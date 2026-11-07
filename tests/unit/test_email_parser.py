
import base64
import pytest

pytestmark = pytest.mark.unit
from services.email_parser import (
    get_headers,
    extract_email_body,
    attachments,
    parse_message,
    parse_thread,
)


def encode(text):
    return base64.urlsafe_b64encode(
        text.encode()
    ).decode().rstrip("=")


def test_get_headers(sample_message):
    headers = get_headers(
        sample_message["payload"]
    )

    assert headers["from"] == "sender@example.com"
    assert headers["to"] == "receiver@example.com"
    assert headers["subject"] == "Project Update"


def test_extract_plain_text(sample_message):
    body = extract_email_body(
        sample_message["payload"]
    )

    assert body == "Hello, this is a test email."


def test_extract_html_body():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {
                "mimeType": "text/html",
                "body": {"data": encode(
                    "<html><body><h1>Hello</h1>"
                    "<p>Testing email</p></body></html>"
                )},
            }
        ],
    }

    result = extract_email_body(payload)

    assert "Hello" in result
    assert "Testing email" in result
    assert "<h1>" not in result


def test_plain_text_preferred_over_html():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": encode("Plain content")},
            },
            {
                "mimeType": "text/html",
                "body": {"data": encode("<p>HTML content</p>")},
            },
        ],
    }

    assert extract_email_body(payload) == "Plain content"


def test_extract_empty_body():
    assert extract_email_body({}) == ""


def test_extract_attachment_metadata():
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "filename": "report.pdf",
                "mimeType": "application/pdf",
                "body": {
                    "attachmentId": "att_123",
                    "size": 2048,
                },
            }
        ],
    }

    result = attachments(payload)

    assert len(result) == 1
    assert result[0]["filename"] == "report.pdf"
    assert result[0]["attachment_id"] == "att_123"


def test_parse_message(sample_message):
    result = parse_message(sample_message)

    assert result["message_id"] == "message_123"
    assert result["thread_id"] == "thread_123"
    assert result["subject"] == "Project Update"
    assert result["body"] == "Hello, this is a test email."
    assert result["labels"] == ["INBOX", "UNREAD"]


def test_parse_thread(sample_thread):
    result = parse_thread(sample_thread)

    assert result["thread_id"] == "thread_123"
    assert result["message_count"] == 2
    assert len(result["messages"]) == 2
