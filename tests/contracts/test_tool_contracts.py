import pytest
from fastmcp import Client

import server


pytestmark = pytest.mark.contract


@pytest.mark.anyio
async def test_expected_tools_are_registered():
    async with Client(server.mcp) as client:
        tools = await client.list_tools()

    tool_names = {tool.name for tool in tools}

    expected_tools = {
        "search_emails",
        "get_email_details",
        "get_email_conversation",
        "get_attachment",
    }

    assert expected_tools.issubset(tool_names)