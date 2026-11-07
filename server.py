"""
Gmail Read-Only MCP Server

Public MCP tools:
1. search_emails
2. get_email_details
3. get_email_conversation
4. get_attachment

All Gmail operations use the readonly OAuth scope.
"""

import json

# error handling
import logging
from functools import lru_cache
from typing import Any

from fastmcp import FastMCP
from google.auth.exceptions import RefreshError, TransportError
from googleapiclient.errors import HttpError

from services import attachment_service, email_parser
from services import gmail_service as gmail_api
from services import search as search_service
from services.auth import get_gmail_service
from validator.pydantic_class import (
    GetAttachmentInput,
    GetEmailConversationInput,
    GetEmailDetailsInput,
    SearchEmailsRequest,
)

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
        raise TypeError("max_results must be an integer.")

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
                "Gmail authentication failed. Reauthentication may be required."
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
                    "Gmail API quota exceeded. Retry after an appropriate delay."
                ),
                "retryable": True,
            }

        return {
            "code": "PERMISSION_DENIED",
            "message": ("Gmail access denied. Check OAuth permissions and API access."),
            "retryable": False,
        }

    # HTTP 404: Resource not found.
    if status == 404:
        return {
            "code": "RESOURCE_NOT_FOUND",
            "message": ("The requested Gmail resource was not found."),
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
            "message": ("Gmail service is temporarily unavailable."),
            "retryable": True,
        }

    return {
        "code": "GMAIL_API_ERROR",
        "message": "Gmail API request failed.",
        "retryable": False,
    }


def _error_result(exc: Exception, tool_name: str) -> dict[str, Any]:
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
            exc_info=(type(exc), exc, exc.__traceback__),
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
            exc_info=(type(exc), exc, exc.__traceback__),
        )

    # 4. Missing configuration.
    elif isinstance(exc, FileNotFoundError):
        error = {
            "code": "CONFIGURATION_ERROR",
            "message": (
                "Gmail OAuth configuration is missing. Check the server configuration."
            ),
            "retryable": False,
        }

        logger.error(
            "Tool=%s | Error=%s",
            tool_name,
            error["code"],
            exc_info=(type(exc), exc, exc.__traceback__),
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
            exc_info=(type(exc), exc, exc.__traceback__),
        )

    # 6. Unexpected errors.
    else:
        error = {
            "code": "INTERNAL_ERROR",
            "message": (
                "An unexpected error occurred while processing the Gmail request."
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


# def _validate_date(value: str | None, field_name: str):
#     """Validate an optional ISO date in YYYY-MM-DD format."""
#     if value is None:
#         return None

#     try:
#         date.fromisoformat(value)
#     except (TypeError, ValueError) as exc:
#         raise ValueError(
#             f"{field_name} must use YYYY-MM-DD format."
#         ) from exc

#     # Require the exact format, not another accepted ISO representation.
#     if len(value) != 10:
#         raise ValueError(f"{field_name} must use YYYY-MM-DD format.")

#     return value


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
    # params : SearchEmailsRequest
    sender: str | None = None,
    recipient: str | None = None,
    subject: str | None = None,
    keyword: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    time_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    has_attachment: bool | None = None,
    is_unread: bool | None = None,
    max_results: int = 10,
    page_token: str | None = None,
) -> dict[str, Any]:
    """
    Search and list Gmail emails using optional filters.

    WHEN TO USE:
    - Find, list, or filter emails by sender, recipient, subject, keyword,
      date, time, attachment presence, or read status.
    - Retrieve recent emails or continue a previous search.

    SEARCH BEHAVIOR:
    - Combine supplied filters.
    - If no filters are provided, return the 10 most recent emails.
    - Use max_results for the requested result count (maximum 50).
    - Use page_token only to continue a previous search.
    - Do not assume unspecified filters or invent criteria.

    DATE AND TIME:
    - Use YYYY-MM-DD dates and HH:MM 24-hour times.
    - Resolve relative dates using reliable current-date information.
    - For time searches, provide time_date, start_time, and end_time together.
    - Ask for a date if the user provides only a time range.
    - Use the MCP server's configured timezone.
    - Time ranges crossing midnight are supported.

    LIMITATIONS:
    - Returns email metadata, not complete bodies.
    - Use get_email_details for one email, get_email_conversation for a thread,
      and get_attachment to download an attachment.
    - Cannot send, modify, or delete emails.

    OUTPUT:
    Return matching email metadata, result count, estimated matching count,
    search query, server timezone, and next_page_token.
    """
    try:
        params = SearchEmailsRequest.model_validate(
            {
                "sender": sender,
                "recipient": recipient,
                "subject": subject,
                "keyword": keyword,
                "start_date": start_date,
                "end_date": end_date,
                "time_date": time_date,
                "start_time": start_time,
                "end_time": end_time,
                "has_attachment": has_attachment,
                "is_unread": is_unread,
                "max_results": max_results,
                "page_token": page_token,
            }
        )

        #  params values
        sender = params.sender
        recipient = params.recipient
        subject = params.subject
        keyword = params.keyword

        start_date = params.start_date.isoformat() if params.start_date else None

        end_date = params.end_date.isoformat() if params.end_date else None

        time_date = params.time_date.isoformat() if params.time_date else None

        start_time = params.start_time.strftime("%H:%M") if params.start_time else None

        end_time = params.end_time.strftime("%H:%M") if params.end_time else None

        has_attachment = params.has_attachment
        is_unread = params.is_unread
        max_results = params.max_results
        page_token = params.page_token

        #  validation
        max_results = _validate_max_results(max_results)

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
        return _error_result(exc, tool_name="search_emails")


# --------------------------------------------------
# 5. TOOL: GET ONE EMAIL'S DETAILS
# --------------------------------------------------


@mcp.tool()
def get_email_details(
    # params : GetEmailDetailsInput
    message_id: str,
) -> dict[str, Any]:
    """
    Retrieve the complete contents and metadata of a specific Gmail email.

    WHEN TO USE:
    - Read an email or inspect its sender, recipients, subject, body, or attachments.
    - Use a message_id obtained from search_emails or another email tool.

    INPUT:
    - message_id must be a valid Gmail message ID.
    - Never invent or guess IDs.

    BEHAVIOR:
    - Retrieve only the specified email.
    - Return parsed body, available metadata, and attachment metadata.
    - Preserve the original email's content and meaning.

    LIMITATIONS:
    - Retrieves one email only; does not search or retrieve entire conversations.
    - Use search_emails for searching, get_email_conversation for threads,
      and get_attachment for downloading attachments.

    OUTPUT:
    Return available sender, recipient, subject, timestamp, body, labels,
    and attachment metadata. This operation is read-only.
    """
    try:
        # parameters
        params = GetEmailDetailsInput.model_validate(
            {
                "message_id": message_id,
            }
        )

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
        return _error_result(exc, tool_name="get_email_details")


# --------------------------------------------------
# 6. TOOL: GET AN EMAIL CONVERSATION
# --------------------------------------------------


@mcp.tool()
def get_email_conversation(
    # params : GetEmailConversationInput
    thread_id: str,
) -> dict[str, Any]:
    """
    Retrieve all available messages in a specific Gmail conversation.

    WHEN TO USE:
    - Read an entire email thread or review its conversation history.
    - Use a thread_id obtained from search_emails or get_email_details.

    INPUT:
    - thread_id must be a valid Gmail thread ID.
    - Do not substitute message_id or invent IDs.

    BEHAVIOR:
    - Retrieve only the specified conversation.
    - Preserve message order and individual message boundaries.
    - Return each message's parsed body, metadata, and attachment metadata.

    LIMITATIONS:
    - Does not search for conversations or download attachments.
    - Use search_emails for searching and get_attachment for downloads.

    OUTPUT:
    Return thread information and individual messages with available sender,
    recipients, subject, timestamp, body, and attachment metadata.
    This operation is read-only.
    """
    try:
        # parameters

        params = GetEmailConversationInput.model_validate({"thread_id": thread_id})

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
        return _error_result(exc, tool_name="get_email_conversation")


# --------------------------------------------------
# 7. TOOL: GET / DOWNLOAD AN ATTACHMENT
# --------------------------------------------------


@mcp.tool()
def get_attachment(
    # params: GetAttachmentInput,
    message_id: str,
    attachment_id: str,
) -> dict[str, Any]:
    """
    Download a specific attachment from a Gmail email.

    WHEN TO USE:
    - Download an attachment from a specific email.
    - Save a PDF, image, document, or other supported attachment.
    - Use message_id and attachment_id obtained from email metadata.

    INPUT:
    - message_id: Gmail message ID containing the attachment.
    - attachment_id: Attachment ID obtained from get_email_details.
    - Never invent or guess attachment IDs.

    BEHAVIOR:
    - Retrieve the specified email.
    - Verify that the attachment belongs to that email.
    - Obtain attachment metadata directly from Gmail.
    - Download and save the attachment.
    - Avoid overwriting existing files.

    LIMITATIONS:
    - Downloads one attachment per tool call.
    - Does not search emails or retrieve entire conversations.
    - Cannot send, modify, or delete emails.

    OUTPUT:
    Returns the saved filename, file path, MIME type,
    file size, and download status.
    """
    try:
        params = GetAttachmentInput.model_validate(
            {
                "message_id": message_id,
                "attachment_id": attachment_id,
            }
        )

        message_id = params.message_id
        attachment_id = params.attachment_id
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
        available_attachments = email_parser.attachments(raw_message.get("payload", {}))

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
            raise ValueError("The specified attachment does not belong to this email.")

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
