
import pytest
from pydantic import ValidationError

from validator.pydantic_class import (
    SearchEmailsRequest,
    GetEmailDetailsInput,
    GetEmailConversationInput,
    GetAttachmentInput,
)


@pytest.mark.unit
def test_search_defaults_allow_recent_emails():
    params = SearchEmailsRequest()

    assert params.max_results == 10
    assert params.sender is None
    assert params.page_token is None


@pytest.mark.unit
@pytest.mark.parametrize("count", [1, 10, 25, 50])
def test_search_accepts_valid_max_results(count):
    params = SearchEmailsRequest(max_results=count)

    assert params.max_results == count


@pytest.mark.unit
@pytest.mark.parametrize("count", [0, -1, 51, 100, True])
def test_search_rejects_invalid_max_results(count):
    with pytest.raises(ValidationError):
        SearchEmailsRequest(max_results=count)


@pytest.mark.unit
def test_search_validates_date_order():
    with pytest.raises(ValidationError):
        SearchEmailsRequest(
            start_date="2026-11-10",
            end_date="2026-11-01",
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        {"start_date": "2026-02-30"},
        {"end_date": "invalid"},
        {"time_date": "2026-13-01"},
    ],
)
def test_search_rejects_invalid_dates(payload):
    with pytest.raises(ValidationError):
        SearchEmailsRequest(**payload)


@pytest.mark.unit
def test_search_requires_complete_time_range():
    with pytest.raises(ValidationError):
        SearchEmailsRequest(
            time_date="2026-11-05",
            start_time="10:00",
        )


@pytest.mark.unit
def test_search_allows_valid_time_range():
    params = SearchEmailsRequest(
        time_date="2026-11-05",
        start_time="10:00",
        end_time="12:00",
    )

    assert params.start_time.hour == 10
    assert params.end_time.hour == 12


@pytest.mark.unit
def test_search_allows_overnight_range():
    params = SearchEmailsRequest(
        time_date="2026-11-05",
        start_time="22:00",
        end_time="02:00",
    )

    assert params.start_time.hour == 22
    assert params.end_time.hour == 2


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        {"start_time": "25:00", "end_time": "26:00"},
        {"start_time": "10:60", "end_time": "11:00"},
        {"start_time": "10:00:00", "end_time": "11:00"},
    ],
)
def test_search_rejects_invalid_times(payload):
    with pytest.raises(ValidationError):
        SearchEmailsRequest(
            time_date="2026-11-05",
            **payload,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "model,field",
    [
        (GetEmailDetailsInput, "message_id"),
        (GetEmailConversationInput, "thread_id"),
    ],
)
def test_ids_reject_whitespace(model, field):
    with pytest.raises(ValidationError):
        model(**{field: "   "})


@pytest.mark.unit
def test_attachment_rejects_whitespace_ids():
    with pytest.raises(ValidationError):
        GetAttachmentInput(
            message_id="msg-1",
            attachment_id="   ",
        )


@pytest.mark.unit
def test_attachment_requires_both_ids():
    with pytest.raises(ValidationError):
        GetAttachmentInput(message_id="msg-1")


@pytest.mark.unit
def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        GetEmailDetailsInput(
            message_id="msg-1",
            unexpected=True,
        )


@pytest.mark.unit
def test_search_string_whitespace_rejected():
    with pytest.raises(ValidationError):
        SearchEmailsRequest(sender="   ")
