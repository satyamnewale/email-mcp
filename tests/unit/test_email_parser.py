import base64

import pytest

from services import email_parser


def encoded(text):
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


@pytest.mark.unit
def test_get_headers_is_case_insensitive():
    headers = email_parser.get_headers(
        {"headers": [{"name": "SUBJECT", "value": "Hi"}]}
    )
    assert headers["subject"] == "Hi"


@pytest.mark.unit
def test_plain_text_takes_priority_over_html():
    payload = {
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": encoded("plain")},
            },
            {
                "mimeType": "text/html",
                "body": {"data": encoded("<b>html</b>")},
            },
        ]
    }
    assert email_parser.extract_email_body(payload) == "plain"


@pytest.mark.unit
def test_html_fallback_removes_tags():
    payload = {
        "mimeType": "text/html",
        "body": {"data": encoded("<b>Hello</b>")},
    }
    assert email_parser.extract_email_body(payload) == "Hello"


@pytest.mark.unit
def test_nested_attachment_metadata():
    payload = {
        "parts": [
            {
                "parts": [
                    {
                        "filename": "report.pdf",
                        "mimeType": "application/pdf",
                        "body": {
                            "attachmentId": "att-1",
                            "size": 3,
                        },
                    }
                ]
            }
        ]
    }

    found = email_parser.attachments(payload)

    assert len(found) == 1
    assert found[0]["attachment_id"] == "att-1"
    assert found[0]["filename"] == "report.pdf"


@pytest.mark.unit
def test_parse_thread(sample_message):
    result = email_parser.parse_thread(
        {
            "id": "thread-1",
            "messages": [sample_message],
        }
    )

    assert result["message_count"] == 1
    assert result["messages"][0]["body"] == "Hello"
