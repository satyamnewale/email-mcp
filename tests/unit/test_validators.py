
import pytest
from pydantic import ValidationError

from validator.pydantic_class import (
    SearchEmailsRequest,
    GetEmailDetailsInput,
    GetEmailConversationInput,
    GetAttachmentInput,
)


def test_search_request_valid():
    result = SearchEmailsRequest.model_validate({
        "sender": "test@example.com",
        "subject": "Project",
        "max_results": 10,
    })

    assert result.sender == "test@example.com"
    assert result.max_results == 10


@pytest.mark.parametrize("max_results", [0, 51, -1])
def test_search_rejects_invalid_max_results(max_results):
    with pytest.raises(ValidationError):
        SearchEmailsRequest.model_validate({
            "max_results": max_results,
        })


def test_email_details_valid():
    result = GetEmailDetailsInput.model_validate({
        "message_id": "message_123",
    })

    assert result.message_id == "message_123"


def test_email_details_rejects_empty_id():
    with pytest.raises(ValidationError):
        GetEmailDetailsInput.model_validate({
            "message_id": "",
        })


def test_conversation_valid():
    result = GetEmailConversationInput.model_validate({
        "thread_id": "thread_123",
    })

    assert result.thread_id == "thread_123"


def test_attachment_valid():
    result = GetAttachmentInput.model_validate({
        "message_id": "message_123",
        "attachment_id": "attachment_123",
    })

    assert result.message_id == "message_123"
    assert result.attachment_id == "attachment_123"
