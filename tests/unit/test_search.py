
import pytest

from services.search import (
    build_search_query,
    build_date_query,
    build_time_query,
    search_emails,
)


def test_build_search_query():
    query = build_search_query(
        sender="sender@example.com",
        subject="Project",
        keyword="Python",
        has_attachment=True,
        is_unread=True,
    )

    assert "from:sender@example.com" in query
    assert "subject:Project" in query
    assert "Python" in query
    assert "has:attachment" in query
    assert "is:unread" in query


def test_build_search_query_without_filters():
    assert build_search_query() == ""


@pytest.mark.parametrize(
    ("has_attachment", "expected"),
    [
        (True, "has:attachment"),
        (False, "-has:attachment"),
        (None, ""),
    ],
)
def test_attachment_filter(has_attachment, expected):
    query = build_search_query(
        has_attachment=has_attachment
    )

    assert query == expected


@pytest.mark.parametrize(
    ("is_unread", "expected"),
    [
        (True, "is:unread"),
        (False, "is:read"),
        (None, ""),
    ],
)
def test_unread_filter(is_unread, expected):
    query = build_search_query(is_unread=is_unread)

    assert query == expected


def test_date_query_start_and_end(monkeypatch):
    from datetime import timezone

    monkeypatch.setattr(
        "services.search.get_user_timezone",
        lambda: timezone.utc,
    )

    query = build_date_query(
        start_date="2026-11-01",
        end_date="2026-11-07",
    )

    assert query.startswith("after:")
    assert "before:" in query


def test_time_query():
    from datetime import timezone

    # Keep this test independent of the machine timezone.
    import services.search as search_module

    original = search_module.get_user_timezone
    search_module.get_user_timezone = lambda: timezone.utc

    try:
        query = build_time_query(
            start_date="2026-11-07",
            start_time="09:00",
            end_time="12:00",
        )

        assert "after:" in query
        assert "before:" in query
    finally:
        search_module.get_user_timezone = original


def test_search_emails_calls_gmail_api(mock_gmail_service):
    messages = mock_gmail_service.users.return_value.messages.return_value

    messages.list.return_value.execute.return_value = {
        "messages": [{"id": "message_123"}],
        "nextPageToken": "next_token",
        "resultSizeEstimate": 10,
    }

    from services.search import search_emails

    result = search_emails(
        service=mock_gmail_service,
        sender="sender@example.com",
        max_results=10,
    )

    assert len(result["messages"]) == 1
    assert result["next_page_token"] == "next_token"
    assert result["result_size_estimate"] == 10

    messages.list.assert_called_once()
