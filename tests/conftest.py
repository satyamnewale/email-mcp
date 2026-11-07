import pytest


@pytest.fixture
def gmail_service_mock(mocker):
    """Mock Gmail API service."""
    return mocker.MagicMock(name="gmail_service")


@pytest.fixture
def mock_server_service(mocker, gmail_service_mock):
    """Prevent real Gmail authentication."""
    return mocker.patch(
        "server.get_service",
        return_value=gmail_service_mock,
    )


@pytest.fixture
def sample_message():
    """Sample Gmail API response."""

    return {
        "id": "msg-1",
        "threadId": "thread-1",
        "snippet": "Hello",
        "internalDate": "1762300800000",
        "labelIds": ["INBOX"],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {
                    "name": "From",
                    "value": "alice@example.com",
                },
                {
                    "name": "To",
                    "value": "bob@example.com",
                },
                {
                    "name": "Subject",
                    "value": "Update",
                },
            ],
            "body": {
                "data": "SGVsbG8=",
            },
        },
    }
