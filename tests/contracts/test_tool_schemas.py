
import pytest

from validator.pydantic_class import (
    GetAttachmentInput,
    GetEmailConversationInput,
    GetEmailDetailsInput,
    SearchEmailsRequest,
)


@pytest.mark.contract
@pytest.mark.parametrize(
    "model, fields",
    [
        (SearchEmailsRequest, {"sender", "max_results", "page_token"}),
        (GetEmailDetailsInput, {"message_id"}),
        (GetEmailConversationInput, {"thread_id"}),
        (GetAttachmentInput, {"message_id", "attachment_id"}),
    ],
)
def test_schema_has_expected_fields(model, fields):
    schema = model.model_json_schema()

    assert fields <= set(schema["properties"])
    assert schema.get("additionalProperties") is False


@pytest.mark.contract
def test_search_schema_documents_max_results():
    schema = SearchEmailsRequest.model_json_schema()
    field = schema["properties"]["max_results"]

    assert field["minimum"] == 1
    assert field["maximum"] == 50
    assert field["default"] == 10


@pytest.mark.contract
@pytest.mark.parametrize(
    "model, expected_required",
    [
        (GetEmailDetailsInput, {"message_id"}),
        (GetEmailConversationInput, {"thread_id"}),
        (GetAttachmentInput, {"message_id", "attachment_id"}),
    ],
)
def test_required_fields_are_documented(model, expected_required):
    schema = model.model_json_schema()

    assert expected_required <= set(schema.get("required", []))


@pytest.mark.contract
def test_search_schema_has_optional_filters():
    schema = SearchEmailsRequest.model_json_schema()

    optional_fields = {
        "sender",
        "recipient",
        "subject",
        "keyword",
        "start_date",
        "end_date",
        "has_attachment",
        "is_unread",
    }

    assert optional_fields <= set(schema["properties"])

    required = set(schema.get("required", []))
    assert optional_fields.isdisjoint(required)


@pytest.mark.contract
def test_attachment_schema_does_not_accept_caller_metadata():
    schema = GetAttachmentInput.model_json_schema()

    assert "filename" not in schema["properties"]
    assert "mime_type" not in schema["properties"]
    assert "size_bytes" not in schema["properties"]
