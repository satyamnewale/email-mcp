import asyncio

import pytest

import server


@pytest.mark.contract
def test_registered_tool_names():
    tools = asyncio.run(server.mcp.get_tools())

    expected = {
        "search_emails",
        "get_email_details",
        "get_email_conversation",
        "get_attachment",
    }

    assert expected.issubset(set(tools.keys()))


@pytest.mark.contract
def test_registered_tools_have_descriptions():
    tools = asyncio.run(server.mcp.get_tools())

    expected = {
        "search_emails",
        "get_email_details",
        "get_email_conversation",
        "get_attachment",
    }

    for name in expected:
        assert tools[name].description
        assert len(tools[name].description.strip()) >= 40
