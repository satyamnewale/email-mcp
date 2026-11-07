import pytest
from pydantic import ValidationError

from validator.pydantic_class import (
    GetAttachmentInput,
    GetEmailConversationInput,
    GetEmailDetailsInput,
    SearchEmailsRequest,
)


@pytest.mark.unit
def test_search_defaults_allow_recent_emails():
    params = SearchEmailsRequest()
    assert params.max_results == 10
    assert params.sender is None


@pytest.mark.unit
@pytest.mark.parametrize("count", [0, -1, 51, 100, True])
def test_search_rejects_invalid_count(count):
    with pytest.raises(ValidationError):
        SearchEmailsRequest(max_results=count)


@pytest.mark.unit
def test_search_validates_date_order():
    with pytest.raises(ValidationError):
        SearchEmailsRequest(start_date="2026-11-10", end_date="2026-11-01")


@pytest.mark.unit
def test_search_requires_complete_time_range():
    with pytest.raises(ValidationError):
        SearchEmailsRequest(time_date="2026-11-05", start_time="10:00")


@pytest.mark.unit
def test_search_allows_overnight_range():
    params = SearchEmailsRequest(
        time_date="2026-11-05", start_time="22:00", end_time="02:00"
    )
    assert params.end_time.hour == 2


@pytest.mark.unit
@pytest.mark.parametrize(
    "model,field",
    [
        (GetEmailDetailsInput, "message_id"),
        (GetEmailConversationInput, "thread_id"),
        (GetAttachmentInput, "attachment_id"),
    ],
)
def test_ids_reject_whitespace(model, field):
    data = (
        {"message_id": "msg-1", "attachment_id": "att-1"}
        if model is GetAttachmentInput
        else {}
    )
    data[field] = "  "
    with pytest.raises(ValidationError):
        model(**data)


@pytest.mark.unit
def test_extra_fields_rejected():
    with pytest.raises(ValidationError):
        GetEmailDetailsInput(message_id="msg-1", unexpected=True)
