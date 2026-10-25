# GitHub MCP Explorer

A Streamlit interface for discovering and invoking tools exposed by the
official GitHub MCP server.

## Requirements

- Python 3.10+
- A GitHub personal access token with the permissions required by the tools
  you plan to call

Install the Python dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run the explorer

```powershell
streamlit run 2.6.mcp_server_explorer.py
```

The explorer connects to GitHub's hosted MCP server at
`https://api.githubcopilot.com/mcp/` using Streamable HTTP. No Docker or local
MCP server process is needed.

Set your GitHub personal access token in the project `.env` file:

```dotenv
GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here
```

The token is loaded automatically and sent to the hosted server as a Bearer
token. You can also enter or override it in the sidebar. The server URL can be
changed there as well; `GITHUB_MCP_SERVER_URL` in `.env` can set a different
default. The hosted service and token must be available to your account and
have the permissions required by the tools you call.

Select a discovered tool to inspect its input schema, enter its arguments as a
JSON object, and choose **Call tool**. The result or any connection/tool error
is shown on the page.
