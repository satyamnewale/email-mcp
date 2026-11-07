import pytest

from services import gmail_service


@pytest.mark.integration
def test_list_messages_calls_correct_endpoint(gmail_service_mock):
    gmail_service_mock.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": [{"id": "msg-1"}],
        "nextPageToken": "next",
        "resultSizeEstimate": 2,
    }
    result = gmail_service.list_messages(
        gmail_service_mock, query="from:alice", max_results=5
    )
    assert result["next_page_token"] == "next"
    gmail_service_mock.users.return_value.messages.return_value.list.assert_called_once_with(
        userId="me", maxResults=5, q="from:alice"
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "fn,endpoint,kwargs",
    [
        (gmail_service.get_message, "messages", {"message_id": "msg-1"}),
        (gmail_service.get_thread, "threads", {"thread_id": "thread-1"}),
    ],
)
def test_get_methods_execute(gmail_service_mock, fn, endpoint, kwargs):
    result = fn(gmail_service_mock, **kwargs)
    assert result is not None
    assert getattr(
        gmail_service_mock.users.return_value, endpoint
    ).return_value.get.called


@pytest.mark.integration
def test_search_service_passes_pagination(gmail_service_mock):
    from services import search

    gmail_service_mock.users.return_value.messages.return_value.list.return_value.execute.return_value = {}
    result = search.search_emails(
        gmail_service_mock, sender="alice", page_token="page-2", max_results=5
    )
    assert result["messages"] == []
    gmail_service_mock.users.return_value.messages.return_value.list.assert_called_once_with(
        userId="me", maxResults=5, q="from:alice", pageToken="page-2"
    )
