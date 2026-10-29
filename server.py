
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
from datetime import date, time

from mcp.server.fastmcp import FastMCP
from googleapiclient.errors import HttpError

from services.auth import get_gmail_service
from services import gmail_service as gmail_api
from services import search as search_service
from services import email_parser
from services import attachment_service


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


def _validate_time(value: str | None, field_name: str):
    """Validate an optional 24-hour time in HH:MM format."""
    if value is None:
        return None

    try:
        time.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} must use HH:MM format."
        ) from exc

    if len(value) != 5:
        raise ValueError(f"{field_name} must use HH:MM format.")

    return value


def _error_result(exc: Exception) -> dict[str, Any]:
    """Return a structured, user-readable error."""
    if isinstance(exc, ValueError):
        message = str(exc)
    elif isinstance(exc, (RuntimeError, HttpError)):
        message = str(exc)
    else:
        # Avoid returning unexpected internal details to the caller.
        message = "The Gmail operation failed. Check server logs."

    return {
        "ok": False,
        "error": {
            "type": type(exc).__name__,
            "message": message,
        },
    }


# --------------------------------------------------
# 4. TOOL: SEARCH EMAILS
# --------------------------------------------------

@mcp.tool()
def search_emails(
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
    Search Gmail by sender, recipient, subject, keyword, date,
    time, attachment presence, or unread status.

    Dates use YYYY-MM-DD. Times use HH:MM in the timezone
    configured on the machine running this server.

    Returns matching emails with parsed headers and snippets/body.
    """
    try:
        max_results = _validate_max_results(max_results)

        start_date = _validate_date(start_date, "start_date")
        end_date = _validate_date(end_date, "end_date")
        time_date = _validate_date(time_date, "time_date")

        start_time = _validate_time(start_time, "start_time")
        end_time = _validate_time(end_time, "end_time")

        page_token = page_token or ""

        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date must not be after end_date.")

        if (start_time is None) != (end_time is None):
            raise ValueError(
                "Provide both start_time and end_time."
            )

        if (time_date is None) != (start_time is None):
            raise ValueError(
                "Provide time_date, start_time, and end_time together."
            )

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

            headers = email_parser.get_headers(
                raw_message.get("payload", {})
            )

            parsed_messages.append({
                "message_id": raw_message.get("id"),
                "thread_id": raw_message.get("threadId"),
                "from": headers.get("from"),
                "to": headers.get("to"),
                "subject": headers.get("subject"),
                "date": headers.get("date"),
                "snippet": raw_message.get("snippet", ""),
                "has_attachments": bool(
                    email_parser.attachments(
                        raw_message.get("payload", {})
                    )
                ),
                "labels": raw_message.get("labelIds", []),
            })

        return {
            "ok": True,
            "query": result.get("query", ""),
            "timezone": result.get("timezone"),
            "result_size_estimate": result.get(
                "result_size_estimate", 0
            ),
            "returned_count": len(parsed_messages),
            "next_page_token": result.get("next_page_token"),
            "emails": parsed_messages,
        }

    except (ValueError, RuntimeError, HttpError) as exc:
        return _error_result(exc)
    except Exception as exc:
        return _error_result(exc)


# --------------------------------------------------
# 5. TOOL: GET ONE EMAIL'S DETAILS
# --------------------------------------------------

@mcp.tool()
def get_email_details(message_id: str) -> dict[str, Any]:
    """
    Retrieve one email by its Gmail message ID.

    Returns sender, recipients, subject, timestamps, body,
    labels, conversation ID, and attachment metadata.
    """
    try:
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

    except (ValueError, RuntimeError, HttpError) as exc:
        return _error_result(exc)
    except Exception as exc:
        return _error_result(exc)


# --------------------------------------------------
# 6. TOOL: GET AN EMAIL CONVERSATION
# --------------------------------------------------

@mcp.tool()
def get_email_conversation(thread_id: str) -> dict[str, Any]:
    """
    Retrieve every message in a Gmail conversation by thread ID.

    Returns the ordered messages, each with parsed headers,
    body text, timestamps, and attachment metadata.
    """
    try:
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

    except (ValueError, RuntimeError, HttpError) as exc:
        return _error_result(exc)
    except Exception as exc:
        return _error_result(exc)


# --------------------------------------------------
# 7. TOOL: GET / DOWNLOAD AN ATTACHMENT
# --------------------------------------------------

@mcp.tool()
def get_attachment(
    message_id: str,
    attachment_id: str,
    filename: str,
    mime_type: str = "application/octet-stream",
    size_bytes: int | None = None,
) -> dict[str, Any]:
    """
    Fetch and save an attachment from a specific Gmail message.

    Required inputs:
    - message_id: Gmail ID of the email containing the file.
    - attachment_id: attachment ID from that email's metadata.
    - filename: filename reported by Gmail.

    The file is saved under the local downloads/ directory.
    The attachment is retrieved read-only from Gmail.
    """
    try:
        message_id = _validate_id(message_id, "message_id")
        attachment_id = _validate_id(attachment_id, "attachment_id")
        filename = _validate_id(filename, "filename")

        if size_bytes is not None:
            if isinstance(size_bytes, bool) or not isinstance(size_bytes, int):
                raise ValueError("size_bytes must be an integer.")
            if size_bytes < 0:
                raise ValueError("size_bytes cannot be negative.")

        if not isinstance(mime_type, str) or not mime_type.strip():
            raise ValueError("mime_type must not be empty.")

        # Prevent callers from supplying a path as the filename.
        if Path(filename).name != filename or "/" in filename or "\\" in filename:
            raise ValueError("filename must be a filename, not a path.")

        service = get_service()

        # Load the specified email and verify its attachments.
        raw_message = gmail_api.get_message(
            service,
            message_id,
            format="full",
        )

        available_attachments = email_parser.attachments(
            raw_message.get("payload", {})
        )

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

        # Use metadata obtained from Gmail, not caller-supplied metadata.
        attachment_metadata = {
            "filename": matched_attachment.get("filename") or filename,
            "mime_type": matched_attachment.get("mime_type")
                or "application/octet-stream",
            "attachment_id": attachment_id,
            "size_bytes": matched_attachment.get("size_bytes"),
        }

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

    except (ValueError, RuntimeError, HttpError) as exc:
        return _error_result(exc)
    except Exception as exc:
        return _error_result(exc)

# --------------------------------------------------
# 8. START MCP SERVER
# --------------------------------------------------

if __name__ == "__main__":
    mcp.run()