
import pytest


@pytest.fixture
def gmail_service_mock(mocker):
    """Mock the authenticated Gmail API service."""
    return mocker.MagicMock(name="gmail_service")


@pytest.fixture
def mock_server_service(mocker, gmail_service_mock):
    """Prevent real OAuth authentication during tool tests."""
    return mocker.patch(
        "server.get_service",
        return_value=gmail_service_mock,
    )


@pytest.fixture
def sample_message():
    """Return a fresh Gmail API message response."""

    return {
        "id": "msg-1",
        "threadId": "thread-1",
        "snippet": "Hello",
        "internalDate": "1762300800000",
        "labelIds": ["INBOX"],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "alice@example.com"},
                {"name": "To", "value": "bob@example.com"},
                {"name": "Subject", "value": "Update"},
                {"name": "Date", "value": "Thu, 5 Nov 2026 12:00:00 +0000"},
            ],
            "body": {
                "data": "SGVsbG8=",
            },
        },
    }


@pytest.fixture
def sample_thread(sample_message):
    """Return a Gmail thread containing one message."""

    return {
        "id": "thread-1",
        "messages": [sample_message],
    }
