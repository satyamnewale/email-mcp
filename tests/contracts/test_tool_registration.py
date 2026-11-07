
import asyncio

import pytest

import server


EXPECTED_TOOLS = {
    "search_emails",
    "get_email_details",
    "get_email_conversation",
    "get_attachment",
}


@pytest.mark.contract
def test_registered_tool_names():
    tools = asyncio.run(server.mcp.get_tools())

    assert EXPECTED_TOOLS <= set(tools)


@pytest.mark.contract
def test_registered_tools_have_descriptions():
    tools = asyncio.run(server.mcp.get_tools())

    for name in EXPECTED_TOOLS:
        assert name in tools

        description = tools[name].description

        assert description
        assert len(description.strip()) >= 40
