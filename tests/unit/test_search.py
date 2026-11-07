from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from services import search


@pytest.mark.unit
def test_query_builder_combines_filters():
    query = search.build_search_query(
        sender="alice@example.com",
        subject="Report",
        has_attachment=True,
        is_unread=False,
    )
    assert "from:alice@example.com" in query
    assert "subject:Report" in query
    assert "has:attachment" in query
    assert "is:read" in query


@pytest.mark.unit
def test_false_attachment_filter():
    assert search.build_search_query(has_attachment=False) == "-has:attachment"


@pytest.mark.unit
def test_date_query_uses_local_midnight(mocker):
    mocker.patch.object(search, "get_user_timezone", return_value=ZoneInfo("UTC"))
    result = search.build_date_query("2026-11-01", "2026-11-01")
    start = int(datetime(2026, 11, 1, tzinfo=ZoneInfo("UTC")).timestamp())
    end = int(datetime(2026, 11, 2, tzinfo=ZoneInfo("UTC")).timestamp())
    assert result == f"after:{start - 1} before:{end}"


@pytest.mark.unit
def test_overnight_time_query(mocker):
    mocker.patch.object(search, "get_user_timezone", return_value=ZoneInfo("UTC"))
    result = search.build_time_query("2026-11-01", "22:00", "02:00")
    start = int(datetime(2026, 11, 1, 22, tzinfo=ZoneInfo("UTC")).timestamp())
    end = int(datetime(2026, 11, 2, 2, tzinfo=ZoneInfo("UTC")).timestamp())
    assert result == f"after:{start - 1} before:{end}"
