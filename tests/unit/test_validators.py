import pytest

from pydantic import ValidationError

pytestmark = pytest.mark.unit

from validator.pydantic_class import (
    SearchEmailsRequest,
    GetEmailDetailsInput,
    GetEmailConversationInput,
    GetAttachmentInput,
)


def test_search_request_valid():

    result = SearchEmailsRequest.model_validate(
        {
            "sender": "test@example.com",
            "subject": "Project update",
            "max_results": 10,
        }
    )

    assert result.sender == "test@example.com"
    assert result.max_results == 10


def test_search_request_accepts_simple_display_name():

    result = SearchEmailsRequest.model_validate(
        {
            "sender": "John Smith",
        }
    )

    assert result.sender == "John Smith"


@pytest.mark.parametrize(
    "sender",
    [
        "trusted@example.com OR to:attacker@example.com",
        "from:attacker@example.com",
        "John: Smith",
    ],
)
def test_search_request_rejects_unsafe_sender(sender):

    with pytest.raises(ValidationError):
        SearchEmailsRequest.model_validate(
            {
                "sender": sender,
            }
        )


@pytest.mark.parametrize(
    "recipient",
    [
        "user@example.com OR from:attacker@example.com",
        "to:attacker@example.com",
    ],
)
def test_search_request_rejects_unsafe_recipient(recipient):

    with pytest.raises(ValidationError):
        SearchEmailsRequest.model_validate(
            {
                "recipient": recipient,
            }
        )


@pytest.mark.parametrize(
    "subject",
    [
        '" OR from:attacker@example.com',
        "Project\nfrom:attacker@example.com",
    ],
)
def test_search_request_rejects_unsafe_subject(subject):

    with pytest.raises(ValidationError):
        SearchEmailsRequest.model_validate(
            {
                "subject": subject,
            }
        )


@pytest.mark.parametrize(
    "keyword",
    [
        '" OR is:unread',
        "keyword\r\nfrom:attacker@example.com",
    ],
)
def test_search_request_rejects_unsafe_keyword(keyword):

    with pytest.raises(ValidationError):
        SearchEmailsRequest.model_validate(
            {
                "keyword": keyword,
            }
        )


@pytest.mark.parametrize(
    "max_results",
    [0, 51, -1],
)
def test_search_rejects_invalid_max_results(max_results):

    with pytest.raises(ValidationError):
        SearchEmailsRequest.model_validate(
            {
                "max_results": max_results,
            }
        )


def test_search_rejects_unknown_fields():

    with pytest.raises(ValidationError):
        SearchEmailsRequest.model_validate(
            {
                "unknown_field": "value",
            }
        )


def test_email_details_valid():

    result = GetEmailDetailsInput.model_validate(
        {
            "message_id": "message_123",
        }
    )

    assert result.message_id == "message_123"


def test_email_details_rejects_empty_id():

    with pytest.raises(ValidationError):
        GetEmailDetailsInput.model_validate(
            {
                "message_id": "",
            }
        )


def test_conversation_valid():

    result = GetEmailConversationInput.model_validate(
        {
            "thread_id": "thread_123",
        }
    )

    assert result.thread_id == "thread_123"
    assert result.max_messages == 20


def test_conversation_accepts_smaller_limit():

    result = GetEmailConversationInput.model_validate(
        {
            "thread_id": "thread_123",
            "max_messages": 5,
        }
    )

    assert result.max_messages == 5


@pytest.mark.parametrize(
    "max_messages",
    [0, 21, -1],
)
def test_conversation_rejects_invalid_limit(max_messages):

    with pytest.raises(ValidationError):
        GetEmailConversationInput.model_validate(
            {
                "thread_id": "thread_123",
                "max_messages": max_messages,
            }
        )


def test_attachment_valid():

    result = GetAttachmentInput.model_validate(
        {
            "message_id": "message_123",
            "attachment_id": "attachment_123",
        }
    )

    assert result.message_id == "message_123"
    assert result.attachment_id == "attachment_123"


def test_attachment_accepts_attachment_id_only():

    result = GetAttachmentInput.model_validate(
        {
            "message_id": "message_123",
            "attachment_id": "attachment_123",
        }
    )

    assert result.attachment_id == "attachment_123"
    assert result.part_id is None


def test_attachment_accepts_part_id_only():

    result = GetAttachmentInput.model_validate(
        {
            "message_id": "message_123",
            "part_id": "1",
        }
    )

    assert result.part_id == "1"
    assert result.attachment_id is None


def test_attachment_rejects_both_identifiers():

    with pytest.raises(ValidationError):

        GetAttachmentInput.model_validate(
            {
                "message_id": "message_123",
                "attachment_id": "attachment_123",
                "part_id": "1",
            }
        )


def test_attachment_rejects_missing_identifiers():

    with pytest.raises(ValidationError):

        GetAttachmentInput.model_validate(
            {
                "message_id": "message_123",
            }
        )

def test_attachment_accepts_long_gmail_attachment_id():

    long_attachment_id = "A" * 500

    result = GetAttachmentInput.model_validate({
        "message_id": "message_123",
        "attachment_id": long_attachment_id,
    })

    assert result.attachment_id == long_attachment_id