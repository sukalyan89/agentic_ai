import json
import os
from json import JSONDecodeError
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from tools.github_mcp_client import run_http_server


load_dotenv(Path(__file__).resolve().parent / ".env")

st.set_page_config(
    page_title="GitHub MCP Explorer",
    page_icon="🔧",
    layout="wide",
)

st.title("GitHub MCP Explorer")
st.caption("Discover GitHub MCP tools and invoke them directly.")

with st.sidebar:
    st.header("Server connection")
    server_url = st.text_input(
        "MCP server URL",
        value=os.getenv(
            "GITHUB_MCP_SERVER_URL",
            "https://api.githubcopilot.com/mcp/",
        ),
    )
    token = st.text_input(
        "GitHub personal access token",
        type="password",
        value=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", ""),
        help=(
            "Loaded from GITHUB_PERSONAL_ACCESS_TOKEN in the project .env "
            "file and sent as a Bearer token."
        )
    )
    connect_clicked = st.button(
        "Connect / refresh tools",
        type="primary",
        use_container_width=True,
    )

    st.caption(
        "Connects to GitHub's hosted MCP server over Streamable HTTP. "
        "Set GITHUB_PERSONAL_ACCESS_TOKEN in .env or enter it above."
    )

if connect_clicked:
    st.session_state.github_mcp_tools = []
    st.session_state.github_mcp_connection = None
    st.session_state.github_mcp_result = None
    try:
        if not token.strip():
            raise ValueError(
                "Set GITHUB_PERSONAL_ACCESS_TOKEN in .env or enter a GitHub "
                "personal access token."
            )

        discovered_tools, _ = run_http_server(server_url.strip(), token.strip())
        st.session_state.github_mcp_tools = discovered_tools
        st.session_state.github_mcp_connection = {
            "url": server_url.strip(),
            "token": token.strip(),
        }
        st.session_state.github_mcp_result = None
        st.success(f"Connected. Found {len(discovered_tools)} tool(s).")
    except (JSONDecodeError, ValueError) as error:
        st.error(f"Invalid connection settings: {error}")
    except Exception as error:
        st.error(f"Could not connect to the GitHub MCP server: {error}")

tools: list[dict[str, Any]] = st.session_state.get("github_mcp_tools", [])
if not tools:
    st.info("Configure the server and select **Connect / refresh tools** to begin.")
    st.stop()

tools_by_name = {tool["name"]: tool for tool in tools}
selected_name = st.selectbox(
    "Select a tool",
    options=list(tools_by_name),
    format_func=lambda name: f"{name} — {tools_by_name[name].get('description', '')}",
)
selected_tool = tools_by_name[selected_name]

st.subheader(selected_name)
if selected_tool.get("description"):
    st.write(selected_tool["description"])

input_schema = selected_tool.get("inputSchema", {"type": "object", "properties": {}})
with st.expander("Input schema", expanded=False):
    st.json(input_schema)

arguments_key = f"github_mcp_arguments_{selected_name}"
if arguments_key not in st.session_state:
    st.session_state[arguments_key] = "{}"

with st.form("github_mcp_tool_call"):
    arguments_text = st.text_area(
        "Tool arguments (JSON object)",
        key=arguments_key,
        height=220,
        help="Enter the arguments required by the input schema above.",
    )
    call_clicked = st.form_submit_button("Call tool", type="primary")

if call_clicked:
    st.session_state.github_mcp_result = None
    try:
        arguments = json.loads(arguments_text)
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a JSON object.")

        connection = st.session_state.github_mcp_connection
        _, result = run_http_server(
            connection["url"],
            connection["token"],
            tool_name=selected_name,
            tool_arguments=arguments,
        )
        st.session_state.github_mcp_result = {
            "tool_name": selected_name,
            "result": result,
        }
    except (JSONDecodeError, ValueError) as error:
        st.error(f"Invalid tool arguments: {error}")
    except Exception as error:
        st.error(f"Tool call failed: {error}")

tool_result = st.session_state.get("github_mcp_result")
if tool_result is not None and tool_result["tool_name"] == selected_name:
    result = tool_result["result"]
    st.subheader("Tool result")
    if result.get("isError"):
        st.error("The MCP server reported that the tool call failed.")
    st.json(result)
