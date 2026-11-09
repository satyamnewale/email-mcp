from datetime import timezone

import pytest

pytestmark = pytest.mark.unit

from services.search import (
    build_search_query,
    build_date_query,
    build_time_query,
    search_emails,
)


def test_build_search_query():

    query = build_search_query(
        sender="sender@example.com",
        subject="Project update",
        keyword="Python",
        has_attachment=True,
        is_unread=True,
    )

    assert "from:sender@example.com" in query
    assert 'subject:"Project update"' in query
    assert '"Python"' in query
    assert "has:attachment" in query
    assert "is:unread" in query


def test_display_name_is_quoted():

    query = build_search_query(
        sender="John Smith",
    )

    assert query == 'from:"John Smith"'


def test_recipient_is_quoted():

    query = build_search_query(
        recipient="Jane Doe",
    )

    assert query == 'to:"Jane Doe"'


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


@pytest.mark.parametrize(
    "malicious_sender",
    [
        "trusted@example.com OR to:attacker@example.com",
        "trusted@example.com is:unread",
        "from:attacker@example.com",
        "John: OR Bob",
    ],
)
def test_sender_search_operator_injection_rejected(malicious_sender):

    with pytest.raises(ValueError):
        build_search_query(sender=malicious_sender)


@pytest.mark.parametrize(
    "malicious_recipient",
    [
        "user@example.com OR from:attacker@example.com",
        "to:attacker@example.com",
    ],
)
def test_recipient_search_operator_injection_rejected(malicious_recipient):

    with pytest.raises(ValueError):
        build_search_query(recipient=malicious_recipient)


@pytest.mark.parametrize(
    "malicious_subject",
    [
        '" OR from:attacker@example.com',
        "Project\nfrom:attacker@example.com",
        'Project" OR is:unread',
    ],
)
def test_subject_search_operator_injection_rejected(malicious_subject):

    with pytest.raises(ValueError):
        build_search_query(subject=malicious_subject)


@pytest.mark.parametrize(
    "malicious_keyword",
    [
        '" OR from:attacker@example.com',
        "is:unread",
        "keyword\r\nfrom:attacker@example.com",
    ],
)
def test_keyword_search_operator_injection_rejected(malicious_keyword):

    with pytest.raises(ValueError):
        build_search_query(keyword=malicious_keyword)


def test_date_query_start_and_end(monkeypatch):

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


def test_time_query(monkeypatch):

    monkeypatch.setattr(
        "services.search.get_user_timezone",
        lambda: timezone.utc,
    )

    query = build_time_query(
        start_date="2026-11-07",
        start_time="09:00",
        end_time="12:00",
    )

    assert "after:" in query
    assert "before:" in query


def test_search_emails_calls_gmail_api(mock_gmail_service):

    messages = (
        mock_gmail_service
        .users.return_value
        .messages.return_value
    )

    messages.list.return_value.execute.return_value = {
        "messages": [{"id": "message_123"}],
        "nextPageToken": "next_token",
        "resultSizeEstimate": 10,
    }

    result = search_emails(
        service=mock_gmail_service,
        sender="sender@example.com",
        max_results=10,
    )

    assert len(result["messages"]) == 1
    assert result["next_page_token"] == "next_token"
    assert result["result_size_estimate"] == 10

    messages.list.assert_called_once()

    actual_params = messages.list.call_args.kwargs

    assert actual_params["q"] == "from:sender@example.com"