
from base64 import urlsafe_b64decode
from datetime import datetime, timezone
from html.parser import HTMLParser
from tzlocal import get_localzone


# --------------------------------------------------
# 1. GET EMAIL HEADERS
# --------------------------------------------------

def get_headers(payload):
    """
    Extract important headers from Gmail's message payload.

    Example:
        From: sender@example.com
        Subject: Project Update
    """

    headers = {}

    for header in payload.get("headers", []):
        name = header.get("name", "").lower()
        value = header.get("value", "")

        headers[name] = value

    return {
        "from": headers.get("from"),
        "to": headers.get("to"),
        "cc": headers.get("cc"),
        "bcc": headers.get("bcc"),
        "subject": headers.get("subject"),
        "date": headers.get("date"),
        "reply_to": headers.get("reply-to"),
        "message_id_header": headers.get("message-id"),
    }


# --------------------------------------------------
# 2. DECODE BASE64URL BODY DATA
# --------------------------------------------------

def _decode_part_data(encoded_data):
    """
    Decode Base64URL-encoded text returned by Gmail.
    This is an internal helper, not an MCP tool.
    """

    if not encoded_data:
        return ""

    # Base64 data may omit padding characters.
    missing_padding = len(encoded_data) % 4

    if missing_padding:
        encoded_data += "=" * (4 - missing_padding)

    decoded_bytes = urlsafe_b64decode(encoded_data)

    return decoded_bytes.decode("utf-8", errors="replace")


# --------------------------------------------------
# 3. CONVERT HTML BODY TO READABLE TEXT
# --------------------------------------------------

class _HTMLTextExtractor(HTMLParser):
    """Small helper that removes HTML tags from email content."""

    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data):
        text = data.strip()

        if text:
            self.text_parts.append(text)

    def get_text(self):
        return "\n".join(self.text_parts)


def _html_to_text(html_content):
    """Convert HTML markup into readable text."""

    parser = _HTMLTextExtractor()
    parser.feed(html_content)
    parser.close()

    return parser.get_text()


# --------------------------------------------------
# 4. EXTRACT EMAIL BODY
# --------------------------------------------------

def extract_email_body(payload):
    """
    Extract plain-text email content.

    If plain text is unavailable, use the HTML body
    and convert it to readable text.
    """

    plain_text_parts = []
    html_parts = []

    def walk_parts(part):
        # A MIME message can contain nested MIME parts.
        mime_type = part.get("mimeType", "")
        filename = part.get("filename", "")
        body_data = part.get("body", {})

        # Do not treat file attachments as email body text.
        if filename:
            return

        # Container parts contain other parts.
        children = part.get("parts", [])

        if children:
            for child in children:
                walk_parts(child)

            return

        # Read text from leaf parts.
        encoded_data = body_data.get("data")

        if not encoded_data:
            return

        text = _decode_part_data(encoded_data)

        if mime_type == "text/plain":
            plain_text_parts.append(text)

        elif mime_type == "text/html":
            html_parts.append(text)

    walk_parts(payload)

    # Prefer plain text when available.
    if plain_text_parts:
        return "\n".join(plain_text_parts).strip()

    # Fall back to HTML when there is no plain text.
    if html_parts:
        html_content = "\n".join(html_parts)
        return _html_to_text(html_content).strip()

    return ""


# --------------------------------------------------
# 5. EXTRACT ATTACHMENT METADATA
# --------------------------------------------------

def attachments(payload):
    """
    Find attachment information in all nested MIME parts.

    This function does NOT download attachment contents.
    """

    found_attachments = []

    def walk_parts(part):
        filename = part.get("filename", "")
        body = part.get("body", {})
        mime_type = part.get("mimeType", "application/octet-stream")

        attachment_id = body.get("attachmentId")

        # A filename or attachment ID indicates file-like content.
        if filename or attachment_id:
            found_attachments.append({
                "filename": filename or "unnamed_attachment",
                "mime_type": mime_type,
                "size_bytes": body.get("size", 0),
                "attachment_id": attachment_id,
                "part_id": part.get("partId"),
            })

        # Check nested parts too.
        for child in part.get("parts", []):
            walk_parts(child)

    walk_parts(payload)

    return found_attachments


# --------------------------------------------------
# 6. PARSE ONE COMPLETE EMAIL
# --------------------------------------------------

def parse_message(message):
    """
    Convert a Gmail API message into a readable dictionary.

    Input:
        Complete response from get_message(service, message_id)

    Output:
        Headers, body, timestamp, IDs, labels and attachments.
    """

    payload = message.get("payload", {})

    # Extract header values.
    header_data = get_headers(payload)

    # Gmail's internalDate is a Unix timestamp in milliseconds.
    internal_date = message.get("internalDate")

    if internal_date is not None:
        timestamp = int(internal_date) / 1000

        received_at = datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc,
        ).astimezone(get_localzone()).isoformat()
    else:
        received_at = None

    return {
        "message_id": message.get("id"),
        "thread_id": message.get("threadId"),
        **header_data,
        "received_at": received_at,
        "body": extract_email_body(payload),
        "attachments": attachments(payload),
        "snippet": message.get("snippet", ""),
        "labels": message.get("labelIds", []),
        "size_estimate_bytes": message.get("sizeEstimate"),
    }


# --------------------------------------------------
# 7. PARSE AN ENTIRE EMAIL CONVERSATION
# --------------------------------------------------

def parse_thread(thread):
    """
    Parse every message in a Gmail conversation.

    Input:
        Complete response from get_thread(service, thread_id)

    Output:
        Thread ID and a list of parsed messages.
    """

    parsed_messages = []

    for message in thread.get("messages", []):
        parsed_messages.append(parse_message(message))

    return {
        "thread_id": thread.get("id"),
        "message_count": len(parsed_messages),
        "messages": parsed_messages,
    }