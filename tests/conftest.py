
import base64
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def sample_headers():
    return [
        {"name": "From", "value": "sender@example.com"},
        {"name": "To", "value": "receiver@example.com"},
        {"name": "Subject", "value": "Project Update"},
        {"name": "Date", "value": "Sat, 07 Nov 2026 10:00:00 +0000"},
        {"name": "Message-ID", "value": "<test@example.com>"},
    ]


@pytest.fixture
def sample_message(sample_headers):
    body = base64.urlsafe_b64encode(
        b"Hello, this is a test email."
    ).decode("utf-8").rstrip("=")

    return {
        "id": "message_123",
        "threadId": "thread_123",
        "internalDate": "1794045600000",
        "snippet": "Hello, this is a test email.",
        "labelIds": ["INBOX", "UNREAD"],
        "sizeEstimate": 1024,
        "payload": {
            "mimeType": "text/plain",
            "headers": sample_headers,
            "body": {
                "data": body,
                "size": 29,
            },
            "parts": [],
        },
    }


@pytest.fixture
def sample_thread(sample_message):
    second_message = {
        **sample_message,
        "id": "message_456",
        "internalDate": "1794049200000",
        "snippet": "Second message",
    }

    return {
        "id": "thread_123",
        "messages": [sample_message, second_message],
    }


@pytest.fixture
def sample_attachment():
    return {
        "filename": "report.txt",
        "mime_type": "text/plain",
        "size_bytes": 12,
        "attachment_id": "attachment_123",
        "part_id": "1",
    }


@pytest.fixture
def mock_gmail_service():
    return MagicMock()
