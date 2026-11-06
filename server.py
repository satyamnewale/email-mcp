"""
Gmail Read-Only MCP Server

Public MCP tools:
1. search_emails
2. get_email_details
3. get_email_conversation
4. get_attachment

All Gmail operations use the readonly OAuth scope.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any
from datetime import date

from fastmcp import FastMCP
from googleapiclient.errors import HttpError

from services.auth import get_gmail_service
from services import gmail_service as gmail_api
from services import search as search_service
from services import email_parser
from services import attachment_service

from validator.pydantic_class import (
    SearchEmailsRequest,
    GetEmailDetailsInput,
    GetEmailConversationInput,
    GetAttachmentInput,
)

# error handling
import logging
import json
from google.auth.exceptions import RefreshError, TransportError

# --------------------------------------------------
# LOGGING CONFIGURATION
# --------------------------------------------------

logger = logging.getLogger("gmail_mcp")

logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

logger.propagate = False

# --------------------------------------------------
# 1. CREATE MCP SERVER
# --------------------------------------------------

mcp = FastMCP("Gmail Read-Only MCP")

# --------------------------------------------------
# 2. REUSE AUTHENTICATED GMAIL SERVICE
# --------------------------------------------------


@lru_cache(maxsize=1)
def get_service():
    """
    Create the Gmail API service on first use.
    Reuse it for subsequent tool calls.
    """
    return get_gmail_service()


# --------------------------------------------------
# 3. COMMON VALIDATION / ERROR HELPERS
# --------------------------------------------------


def _validate_id(value: str, field_name: str) -> str:
    """Validate a Gmail message, thread, or attachment ID."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty.")

    return value.strip()


def _validate_max_results(max_results: int) -> int:
    """Limit the number of search results returned."""
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise ValueError("max_results must be an integer.")

    if not 1 <= max_results <= 50:
        raise ValueError("max_results must be between 1 and 50.")

    return max_results


def _classify_http_error(exc: HttpError) -> dict:
    """
    Classify Google Gmail API errors using HTTP status
    and Google's structured error reason.
    """

    status = getattr(exc.resp, "status", None)
    reason = None

    try:
        payload = json.loads(exc.content.decode("utf-8"))

        errors = payload.get("error", {}).get("errors", [])

        if errors:
            reason = errors[0].get("reason")

    except (ValueError, AttributeError, TypeError):
        pass

    # HTTP 400: Invalid API request.
    if status == 400:
        return {
            "code": "GMAIL_BAD_REQUEST",
            "message": "Gmail rejected the search request.",
            "retryable": False,
        }

    # HTTP 401: Authentication failure.
    if status == 401:
        return {
            "code": "AUTHENTICATION_ERROR",
            "message": (
                "Gmail authentication failed. "
                "Reauthentication may be required."
            ),
            "retryable": False,
        }

    # HTTP 403: Permission or quota failure.
    if status == 403:

        quota_reasons = {
            "rateLimitExceeded",
            "userRateLimitExceeded",
            "quotaExceeded",
        }

        if reason in quota_reasons:
            return {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": (
                    "Gmail API quota exceeded. "
                    "Retry after an appropriate delay."
                ),
                "retryable": True,
            }

        return {
            "code": "PERMISSION_DENIED",
            "message": (
                "Gmail access denied. "
                "Check OAuth permissions and API access."
            ),
            "retryable": False,
        }

    # HTTP 404: Resource not found.
    if status == 404:
        return {
            "code": "RESOURCE_NOT_FOUND",
            "message": (
                "The requested Gmail resource was not found."
            ),
            "retryable": False,
        }

    # HTTP 429: Rate limit.
    if status == 429:
        return {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Gmail API request limit exceeded.",
            "retryable": True,
        }

    # HTTP 5xx: Temporary server-side failure.
    if status is not None and status >= 500:
        return {
            "code": "GMAIL_API_ERROR",
            "message": (
                "Gmail service is temporarily unavailable."
            ),
            "retryable": True,
        }

    return {
        "code": "GMAIL_API_ERROR",
        "message": "Gmail API request failed.",
        "retryable": False,
    }



def _error_result(
    exc: Exception,
    tool_name: str
) -> dict[str, Any]:
    """
    Classify an exception, log diagnostic information,
    and return a safe structured error to the MCP caller.
    """

    # 1. Input validation errors.
    if isinstance(exc, ValueError):
        error = {
            "code": "VALIDATION_ERROR",
            "message": str(exc),
            "retryable": False,
        }

        logger.warning(
            "Tool=%s | Error=%s | Message=%s",
            tool_name,
            error["code"],
            error["message"],
        )

    # 2. Gmail API errors.
    elif isinstance(exc, HttpError):
        error = _classify_http_error(exc)

        logger.error(
            "Tool=%s | Error=%s | HTTP_STATUS=%s",
            tool_name,
            error["code"],
            getattr(exc.resp, "status", None),
            exc_info=True,
        )

    # 3. OAuth refresh failures.
    elif isinstance(exc, RefreshError):
        error = {
            "code": "AUTHENTICATION_ERROR",
            "message": (
                "Gmail authentication could not be refreshed. "
                "Reauthentication may be required."
            ),
            "retryable": False,
        }

        logger.error(
            "Tool=%s | Error=%s",
            tool_name,
            error["code"],
            exc_info=True,
        )

    # 4. Missing configuration.
    elif isinstance(exc, FileNotFoundError):
        error = {
            "code": "CONFIGURATION_ERROR",
            "message": (
                "Gmail OAuth configuration is missing. "
                "Check the server configuration."
            ),
            "retryable": False,
        }

        logger.error(
            "Tool=%s | Error=%s",
            tool_name,
            error["code"],
            exc_info=True,
        )

    # 5. Network and timeout failures.
    elif isinstance(exc, (TransportError, TimeoutError)):
        error = {
            "code": "NETWORK_ERROR",
            "message": (
                "Unable to communicate with Gmail. "
                "Check the network connection and retry."
            ),
            "retryable": True,
        }

        logger.error(
            "Tool=%s | Error=%s",
            tool_name,
            error["code"],
            exc_info=True,
        )

    # 6. Unexpected errors.
    else:
        error = {
            "code": "INTERNAL_ERROR",
            "message": (
                "An unexpected error occurred while "
                "processing the Gmail request."
            ),
            "retryable": False,
        }

        logger.exception(
            "Tool=%s | Unexpected internal error",
            tool_name,
        )

    # Common response format.
    return {
        "ok": False,
        "error": error,
    }


def _validate_date(value: str | None, field_name: str):
    """Validate an optional ISO date in YYYY-MM-DD format."""
    if value is None:
        return None

    try:
        date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} must use YYYY-MM-DD format."
        ) from exc

    # Require the exact format, not another accepted ISO representation.
    if len(value) != 10:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.")

    return value


# def _validate_time(value: str | None, field_name: str):
#     """Validate an optional 24-hour time in HH:MM format."""
#     if value is None:
#         return None

#     try:
#         time.fromisoformat(value)
#     except (TypeError, ValueError) as exc:
#         raise ValueError(
#             f"{field_name} must use HH:MM format."
#         ) from exc

#     if len(value) != 5:
#         raise ValueError(f"{field_name} must use HH:MM format.")

#     return value

# --------------------------------------------------
# 4. TOOL: SEARCH EMAILS
# --------------------------------------------------


@mcp.tool()
def search_emails(
    params : SearchEmailsRequest
    # sender: str | None = None,
    # recipient: str | None = None,
    # subject: str | None = None,
    # keyword: str | None = None,
    # start_date: str | None = None,
    # end_date: str | None = None,
    # time_date: str | None = None,
    # start_time: str | None = None,
    # end_time: str | None = None,
    # has_attachment: bool | None = None,
    # is_unread: bool | None = None,
    # max_results: int = 10,
    # page_token: str | None = None,
) -> dict[str, Any]:
    """
    Search and list emails from the user's Gmail mailbox using
    optional search filters.

    WHEN TO USE:
    - When the user wants to find, search, list, or filter emails.
    - When searching by sender, recipient, subject, or keywords.
    - When searching within a date or time range.
    - When filtering emails by attachment presence or read status.
    - When the user requests their latest or most recent emails.
    - When continuing a previous search using pagination.

    SEARCH BEHAVIOR:
    - Combine supplied search conditions to narrow the results.
    - If no search conditions are provided, return the 10 most
      recent emails by default.
    - If the user requests a specific number of emails, set
      max_results accordingly, within the supported limit.
    - Do not invent missing search criteria.
    - Do not interpret an unspecified filter as False.
    - Use page_token only to continue a previous search.

    DATE AND TIME:
    - Dates must use YYYY-MM-DD format.
    - Times must use HH:MM in 24-hour format.
    - Resolve relative dates such as yesterday, last Monday,
      and last week using reliable current-date information.
    - Never guess the current date or timezone.
    - For time-range searches, provide time_date, start_time,
      and end_time together.
    - If a time range is provided without a calendar date,
      ask the user to specify the date before calling this tool.
    - Interpret time boundaries using the timezone configured
      on the MCP server.
    - A time range crossing midnight is supported.

    FILTER INTERPRETATION:
    - sender: Email address or sender name.
    - recipient: Email address or recipient name.
    - subject: Subject text to search for.
    - keyword: Search terms in the email.
    - has_attachment: True for emails with attachments,
      False for emails without attachments.
    - is_unread: True for unread emails, False for read emails.
    - Omit filters that the user has not specified.

    LIMITATIONS:
    - This tool searches and lists email metadata.
    - It does not return complete email bodies.
    - Use get_email_details to retrieve a complete email.
    - Use get_email_conversation to retrieve a full thread.
    - Use get_attachment to download an attachment.
    - This tool cannot send, modify, or delete emails.

    RETURNS:
    - Matching email metadata, including message_id, thread_id,
      sender, recipient, subject, date, snippet, and labels.
    - Attachment indicator when available.
    - Number of returned emails and estimated matching count.
    - Search query, server timezone, and next_page_token.
    """
    try:
        #  params values
        sender = params.sender
        recipient = params.recipient
        subject = params.subject
        keyword = params.keyword

        start_date = (
            params.start_date.isoformat()
            if params.start_date else None
        )

        end_date = (
            params.end_date.isoformat()
            if params.end_date else None
        )

        time_date = (
            params.time_date.isoformat()
            if params.time_date else None
        )

        start_time = (
            params.start_time.strftime("%H:%M")
            if params.start_time else None
        )

        end_time = (
            params.end_time.strftime("%H:%M")
            if params.end_time else None
        )

        has_attachment = params.has_attachment
        is_unread = params.is_unread
        max_results = params.max_results
        page_token = params.page_token

        #  validation
        max_results = _validate_max_results(max_results)
        start_date = _validate_date(start_date, "start_date")
        end_date = _validate_date(end_date, "end_date")
        time_date = _validate_date(time_date, "time_date")

        page_token = page_token or ""

        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date must not be after end_date.")

        if (start_time is None) != (end_time is None):
            raise ValueError("Provide both start_time and end_time.")

        if (time_date is None) != (start_time is None):
            raise ValueError("Provide time_date, start_time, and end_time together.")

        # if not any([
        #     sender, recipient, subject, keyword,
        #     start_date, end_date, time_date,
        #     has_attachment is not None,
        #     is_unread is not None,
        # ]):
        #     raise ValueError(
        #         "Provide at least one search condition."
        #     )

        date_filters = None
        if start_date or end_date:
            date_filters = {
                "after": start_date,
                "before": end_date,
            }

        time_filters = None
        if time_date:
            time_filters = {
                "date": time_date,
                "start_time": start_time,
                "end_time": end_time,
            }

        service = get_service()

        # search_service builds Gmail query conditions and calls
        # Gmail's messages.list endpoint.
        result = search_service.search_emails(
            service=service,
            sender=sender,
            recipient=recipient,
            subject=subject,
            keyword=keyword,
            date_filters=date_filters,
            time_filters=time_filters,
            attachment_filters={
                "hasAttachment": has_attachment,
                "isUnread": is_unread,
            },
            max_results=max_results,
            page_token=page_token,
        )

        # The search response contains IDs, not complete email bodies.
        parsed_messages = []

        for reference in result.get("messages", []):
            message_id = reference.get("id")

            if not message_id:
                continue

            raw_message = gmail_api.get_message(
                service,
                message_id,
                format="metadata",
            )

            headers = email_parser.get_headers(raw_message.get("payload", {}))

            parsed_messages.append(
                {
                    "message_id": raw_message.get("id"),
                    "thread_id": raw_message.get("threadId"),
                    "from": headers.get("from"),
                    "to": headers.get("to"),
                    "subject": headers.get("subject"),
                    "date": headers.get("date"),
                    "snippet": raw_message.get("snippet", ""),
                    "has_attachments": bool(
                        email_parser.attachments(raw_message.get("payload", {}))
                    ),
                    "labels": raw_message.get("labelIds", []),
                }
            )

        return {
            "ok": True,
            "query": result.get("query", ""),
            "timezone": result.get("timezone"),
            "result_size_estimate": result.get("result_size_estimate", 0),
            "returned_count": len(parsed_messages),
            "next_page_token": result.get("next_page_token"),
            "emails": parsed_messages,
        }

    except Exception as exc:
        return _error_result(
            exc,
            tool_name="search_emails"
        )


# --------------------------------------------------
# 5. TOOL: GET ONE EMAIL'S DETAILS
# --------------------------------------------------


@mcp.tool()
def get_email_details( 
        params : GetEmailDetailsInput
        # message_id : str
    ) -> dict[str, Any]:

    """
    PURPOSE:
    Retrieve the detailed contents and metadata of a specific Gmail email.

    WHEN TO USE:
    - When the user wants to read the complete contents of an email.
    - When the user asks for details about a particular email found through search_emails.
    - When the user wants to inspect the sender, recipients, subject, date, body, or attachments of an email.
    - When the user provides a specific Gmail message ID.

    INPUT INSTRUCTIONS:
    - message_id must be a valid Gmail message ID.
    - Obtain message_id from search_emails results or another email-related tool.
    - Do not invent or guess message IDs.

    RETRIEVAL INSTRUCTIONS:
    - Retrieve the specified email using its Gmail message ID.
    - Extract and return the available email metadata and parsed message body.
    - Include attachment metadata when attachments are present.
    - Preserve the original email's meaning and content.
    - Do not retrieve unrelated emails.

    LIMITATIONS:
    - This tool retrieves only one email at a time.
    - It does not search for emails. Use search_emails for that.
    - It does not retrieve an entire email conversation. Use get_email_conversation when the user requests the complete thread.
    - It does not download attachments. Use get_attachment for that.

    OUTPUT:
    Return the email details, including available sender and recipient information,
    subject, timestamp, body, labels, and attachment metadata.

    The operation is read-only and does not modify the email.
    """
    try:

        # parameters
        message_id = params.message_id

        # validation
        message_id = _validate_id(message_id, "message_id")

        service = get_service()

        raw_message = gmail_api.get_message(
            service,
            message_id,
            format="full",
        )

        parsed = email_parser.parse_message(raw_message)

        return {
            "ok": True,
            "email": parsed,
        }

    except Exception as exc:
        return _error_result(
            exc,
            tool_name="get_email_details"
        )

# --------------------------------------------------
# 6. TOOL: GET AN EMAIL CONVERSATION
# --------------------------------------------------


@mcp.tool()
def get_email_conversation(
        params : GetEmailConversationInput
        # thread_id : str
    ) -> dict[str, Any]:
    """
    PURPOSE:
    Retrieve all available messages belonging to a specific Gmail conversation.

    WHEN TO USE:
    - When the user asks to read an entire email conversation or thread.
    - When the user wants to see the complete discussion between participants.
    - When the user wants to review previous replies and responses.
    - When the user asks for the conversation history of a particular email.
    - When the user provides a Gmail thread ID.

    INPUT INSTRUCTIONS:
    - thread_id must be a valid Gmail thread ID.
    - Obtain thread_id from search_emails results or get_email_details output.
    - Do not use a message_id in place of a thread_id.
    - Do not invent or guess thread IDs.

    RETRIEVAL INSTRUCTIONS:
    - Retrieve the specified Gmail conversation using its thread ID.
    - Extract the available messages belonging to that thread.
    - Return each message with its available metadata and parsed body.
    - Preserve the message order and individual message boundaries.
    - Include attachment metadata when available.
    - Do not combine separate messages into one email body.

    LIMITATIONS:
    - This tool retrieves only the specified conversation.
    - It does not search for conversations. Use search_emails for that.
    - It does not download attachments. Use get_attachment for that.
    - It does not retrieve unrelated conversations.

    OUTPUT:
    Return the conversation details, including available thread information
    and individual messages with their sender, recipients, subject, timestamp,
    body, and attachment metadata.

    The operation is read-only and does not modify the conversation.
    """
    try:

        # parameters
        thread_id = params.thread_id

        # validator
        thread_id = _validate_id(thread_id, "thread_id")

        service = get_service()

        raw_thread = gmail_api.get_thread(
            service,
            thread_id,
            format="full",
        )

        parsed_thread = email_parser.parse_thread(raw_thread)

        return {
            "ok": True,
            "conversation": parsed_thread,
        }

    except Exception as exc:
        return _error_result(
            exc,
            tool_name="get_email_conversation"
        )


# --------------------------------------------------
# 7. TOOL: GET / DOWNLOAD AN ATTACHMENT
# --------------------------------------------------


@mcp.tool()
def get_attachment(
    params: GetAttachmentInput,
) -> dict[str, Any]:
    """
    PURPOSE:
    Retrieve and save a specific attachment from a Gmail email.

    WHEN TO USE:
    - When the user explicitly asks to download or save an email attachment.
    - When the user wants to retrieve a particular file attached to an email.
    - When the user identifies an attachment from get_email_details or
      get_email_conversation output.
    - When the user asks to download a specific attachment by its name,
      provided its corresponding attachment metadata has been retrieved.

    INPUT INSTRUCTIONS:
    - message_id must identify the Gmail email containing the attachment.
    - attachment_id must identify the specific attachment within that email.
    - Obtain both identifiers from email details or conversation results.
    - Do not invent or guess attachment IDs.
    - Do not substitute a thread_id for a message_id.

    DOWNLOAD INSTRUCTIONS:
    - Retrieve the specified email from Gmail.
    - Extract its available attachment metadata.
    - Verify that the requested attachment_id belongs to the specified email.
    - Obtain the filename, MIME type, and file size from Gmail metadata.
    - Download the attachment using the Gmail API.
    - Save the downloaded file under the local downloads/ directory.
    - Do not use metadata supplied by the LLM as the authoritative source.

    LIMITATIONS:
    - This tool downloads only one specified attachment per invocation.
    - It does not search for emails or attachments.
    - It does not retrieve attachments from unrelated emails.
    - It does not send, modify, or delete emails.
    - The file is saved in the MCP server's local downloads/ directory.

    OUTPUT:
    Return the download result, including the saved file information
    provided by the attachment service.

    The operation is read-only with respect to Gmail.
    It saves a local copy of the attachment without modifying the original email.
    """
    try:
        # 1. Extract and validate input parameters
        message_id = _validate_id(params.message_id, "message_id")
        attachment_id = _validate_id(params.attachment_id, "attachment_id")

        # 2. Get Gmail service
        service = get_service()

        # 3. Retrieve the specified email
        raw_message = gmail_api.get_message(
            service,
            message_id,
            format="full",
        )

        # 4. Extract attachment metadata
        available_attachments = email_parser.attachments(
            raw_message.get("payload", {})
        )

        # 5. Verify attachment belongs to this email
        matched_attachment = next(
            (
                item
                for item in available_attachments
                if item.get("attachment_id") == attachment_id
            ),
            None,
        )

        if matched_attachment is None:
            raise ValueError(
                "The specified attachment does not belong to this email."
            )

        # 6. Build metadata using Gmail's data
        attachment_metadata = {
            "filename": matched_attachment.get("filename") or "attachment",
            "mime_type": matched_attachment.get("mime_type")
            or "application/octet-stream",
            "attachment_id": attachment_id,
            "size_bytes": matched_attachment.get("size_bytes"),
        }

        # 7. Download attachment
        saved_file = attachment_service.download_attachment(
            service=service,
            message_id=message_id,
            attachment=attachment_metadata,
            output_dir="downloads",
        )

        return {
            "ok": True,
            "attachment": saved_file,
        }

    except Exception as exc:
        return _error_result(
            exc,
            tool_name="get_attachment",
        )


# --------------------------------------------------
# 8. START MCP SERVER
# --------------------------------------------------

if __name__ == "__main__":
    mcp.run()
