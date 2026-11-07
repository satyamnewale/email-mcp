
import pytest

from services import gmail_service
from services import search


@pytest.mark.integration
def test_list_messages_calls_correct_endpoint(gmail_service_mock):
    execute = (
        gmail_service_mock.users.return_value
        .messages.return_value
        .list.return_value
        .execute
    )

    execute.return_value = {
        "messages": [{"id": "msg-1"}],
        "nextPageToken": "next",
        "resultSizeEstimate": 2,
    }

    result = gmail_service.list_messages(
        gmail_service_mock,
        query="from:alice",
        max_results=5,
    )

    assert result["messages"] == [{"id": "msg-1"}]
    assert result["next_page_token"] == "next"

    gmail_service_mock.users.return_value.messages.return_value.list.assert_called_once_with(
        userId="me",
        maxResults=5,
        q="from:alice",
    )


@pytest.mark.integration
def test_get_message_calls_correct_endpoint(gmail_service_mock):
    gmail_service.get_message(
        gmail_service_mock,
        "msg-1",
        format="full",
    )

    gmail_service_mock.users.return_value.messages.return_value.get.assert_called_once_with(
        userId="me",
        id="msg-1",
        format="full",
    )


@pytest.mark.integration
def test_get_thread_calls_correct_endpoint(gmail_service_mock):
    gmail_service.get_thread(
        gmail_service_mock,
        "thread-1",
        format="full",
    )

    gmail_service_mock.users.return_value.threads.return_value.get.assert_called_once_with(
        userId="me",
        id="thread-1",
        format="full",
    )


@pytest.mark.integration
def test_get_attachment_calls_correct_endpoint(gmail_service_mock):
    gmail_service.get_attachment_data(
        gmail_service_mock,
        "msg-1",
        "att-1",
    )

    gmail_service_mock.users.return_value.messages.return_value.attachments.return_value.get.assert_called_once_with(
        userId="me",
        messageId="msg-1",
        id="att-1",
    )


@pytest.mark.integration
def test_search_service_passes_pagination(gmail_service_mock, mocker):
    mocker.patch.object(
        search,
        "get_user_timezone",
        return_value="UTC",
    )

    search.search_emails(
        gmail_service_mock,
        sender="alice",
        page_token="page-2",
        max_results=5,
    )

    gmail_service_mock.users.return_value.messages.return_value.list.assert_called_once_with(
        userId="me",
        maxResults=5,
        q="from:alice",
        pageToken="page-2",
    )
