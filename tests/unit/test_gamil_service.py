
from services import gmail_service
import pytest

pytestmark = pytest.mark.unit

def test_list_messages(mock_gmail_service):
    messages = (
        mock_gmail_service.users.return_value.messages.return_value
    )

    messages.list.return_value.execute.return_value = {
        "messages": [{"id": "123", "threadId": "456"}],
        "nextPageToken": "next",
        "resultSizeEstimate": 1,
    }

    result = gmail_service.list_messages(
        mock_gmail_service,
        query="from:test@example.com",
        max_results=5,
        page_token="previous",
    )

    assert result["messages"][0]["id"] == "123"
    assert result["next_page_token"] == "next"
    assert result["resultSizeEstimate"] == 1

    messages.list.assert_called_once_with(
        userId="me",
        maxResults=5,
        q="from:test@example.com",
        pageToken="previous",
    )


def test_get_message(mock_gmail_service):
    api = (
        mock_gmail_service.users.return_value.messages.return_value
    )

    api.get.return_value.execute.return_value = {
        "id": "123",
        "snippet": "Test",
    }

    result = gmail_service.get_message(
        mock_gmail_service,
        "123",
    )

    assert result["id"] == "123"


def test_get_thread(mock_gmail_service):
    api = (
        mock_gmail_service.users.return_value.threads.return_value
    )

    api.get.return_value.execute.return_value = {
        "id": "thread_123",
        "messages": [],
    }

    result = gmail_service.get_thread(
        mock_gmail_service,
        "thread_123",
    )

    assert result["id"] == "thread_123"
