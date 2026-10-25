import asyncio
from typing import Any, Optional
from urllib.parse import urlparse

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def _run_http_server(
    url: str,
    token: str,
    tool_name: Optional[str],
    tool_arguments: Optional[dict[str, Any]],
) -> tuple[list[dict[str, Any]], Optional[dict[str, Any]]]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with streamablehttp_client(url, headers=headers) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tool_response = await session.list_tools()
            tools = [tool.model_dump(mode="json") for tool in tool_response.tools]
            if tool_name is None:
                return tools, None

            result = await session.call_tool(
                tool_name,
                arguments=tool_arguments or {},
            )
            return tools, result.model_dump(mode="json"            )


def run_http_server(
            url: str,
            token: str,
            tool_name: Optional[str] = None,
            tool_arguments: Optional[dict[str, Any]] = None,
) -> tuple[list[dict[str, Any]], Optional[dict[str, Any]]]:
            parsed_url = urlparse(url)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                raise ValueError("MCP server URL must be a valid HTTP or HTTPS URL.")

            return asyncio.run(
                _run_http_server(
                    url,
                    token,
                    tool_name,
                    tool_arguments,
                )
            )
