import pytest

import server


@pytest.mark.contract
@pytest.mark.parametrize(
    "name,keyword",
    [
        ("search_emails", "search"),
        ("get_email_details", "email"),
        ("get_email_conversation", "conversation"),
        ("get_attachment", "attachment"),
    ],
)
def test_tool_has_relevant_description(name, keyword):
    description = getattr(server, name).__doc__ or ""
    assert len(description.strip()) >= 80
    assert keyword in description.lower()


@pytest.mark.contract
def test_attachment_description_is_not_conversation_description():
    description = server.get_attachment.__doc__.lower()
    assert "download" in description
    assert "attachment_id" in description
