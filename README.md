# Agentic AI examples

A collection of small Streamlit applications that demonstrate chat, memory,
CrewAI agents, search, SQL tools, multi-agent workflows, and Langfuse tracing.
Each numbered application is independent: start one app at a time from the
repository root.

## Requirements

- Python 3.11 is recommended.
- A Groq API key is needed for the LLM-powered chat and CrewAI applications.
- An internet connection is needed for API calls and the first download of
  local embedding models.

## Set up on your laptop

Clone the repository and change into its root directory. Create and activate a
virtual environment:

**Windows PowerShell**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```shell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create your local environment file from the template:

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

Edit `.env` and add only the credentials for the apps you want to use. Never
commit `.env`, API keys, access tokens, or private data. `.env` and
`chroma_data/` are ignored by Git. However, `sample_data.db`, `memory.txt`, and
`memory.json` are already tracked in this repository; `.gitignore` does not
prevent changes to files that are already tracked. Review their contents
before publishing, and do not commit app-generated changes that contain
private data.

Run an application from the repository root with Streamlit:

```shell
streamlit run "1.0.app_scaffold.py"
```

Streamlit prints a local URL (usually `http://localhost:8501`) to open in your
browser. Stop the app with `Ctrl+C`. To run another example, stop the current
one and replace the filename in the command.

## Numbered applications

| File | What it demonstrates | How to run | Configuration / preparation |
|---|---|---|---|
| `1.0.app_scaffold.py` | Chat UI starter with a local placeholder response; no AI API call | `streamlit run "1.0.app_scaffold.py"` | None |
| `1.1.app_simple_chat.py` | Groq-backed chat and token usage | `streamlit run "1.1.app_simple_chat.py"` | `GROQ_API_KEY` |
| `1.2.app_simple_chat_mem.py` | Groq chat with conversation memory saved in `memory.txt` | `streamlit run "1.2.app_simple_chat_mem.py"` | `GROQ_API_KEY`; chat content is saved locally |
| `1.3.app_simple_chat_struct_mem.py` | Groq chat with structured JSON memory in `memory.json` | `streamlit run "1.3.app_simple_chat_struct_mem.py"` | `GROQ_API_KEY`; chat-derived memory is saved locally |
| `1.4.Semantic_Memory.py` | Upload text, Markdown, or text-based PDF files, embed them locally, and search ChromaDB | `streamlit run "1.4.Semantic_Memory.py"` | No API key; first run downloads the embedding model. Add documents in the app. |
| `2.1.app_crew_simple.py` | Single CrewAI analyst agent using Groq | `streamlit run "2.1.app_crew_simple.py"` | `GROQ_API_KEY` |
| `2.2.app_crew_with_sem_mem.py` | CrewAI agent with optional retrieval from ChromaDB semantic memory | `streamlit run "2.2.app_crew_with_sem_mem.py"` | `GROQ_API_KEY`; populate the `webinar_semantic_memory` collection using `1.4.Semantic_Memory.py` first |
| `2.3.app_crew_search_tool.py` | CrewAI agent with optional Tavily web search | `streamlit run "2.3.app_crew_search_tool.py"` | `GROQ_API_KEY`; `TAVILY_API_KEY` enables web search |
| `2.4.sql_exploration.py` | Import the sample Excel workbook and explore it with read-only SQL | `streamlit run "2.4.sql_exploration.py"` | No API key; requires `data_assets/sample_data.xlsx` |
| `2.5.app_crew_sql_tool.py` | CrewAI agent that answers sales questions using read-only SQLite queries | `streamlit run "2.5.app_crew_sql_tool.py"` | `GROQ_API_KEY`; requires `data_assets/sample_data.xlsx` |
| `2.6.mcp_server_explorer.py` | Discover and invoke tools from a GitHub-hosted MCP server | `streamlit run "2.6.mcp_server_explorer.py"` | `GITHUB_PERSONAL_ACCESS_TOKEN`; `GITHUB_MCP_SERVER_URL` is optional |
| `3.1.app_simple_task.py` | CrewAI business analyst with task breakdown and SQL access | `streamlit run "3.1.app_simple_task.py"` | `GROQ_API_KEY`; requires `data_assets/sample_data.xlsx` |
| `3.2.app_multi_agent_architecture.py` | Routes customer-care, sales, and general requests to specialized agents | `streamlit run "3.2.app_multi_agent_architecture.py"` | `GROQ_API_KEY`; prepare the sales database and policy collection as described below |
| `4.1.app_crew_langfuse.py` | Multi-agent customer-care app with Langfuse tracing | `streamlit run "4.1.app_crew_langfuse.py"` | `GROQ_API_KEY`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_SECRET_KEY`; also prepare the sales database and policy collection |

### Prepare data for the SQL and multi-agent apps

The SQL apps create `sample_data.db` from the included
`data_assets/sample_data.xlsx` workbook when needed. You can also build or
rebuild it explicitly:

```shell
python helper/create_db.py
```

The apps that use company policy search need the local ChromaDB collection
first. In the repository root, run:

```shell
python helper/policy_ingest.py
```

This ingests the included sample policy JSON into the local `chroma_data`
directory. It may download the embedding model the first time. `2.2` uses a
different collection: fill that collection by running `1.4.Semantic_Memory.py`
and uploading your own documents.

## Environment variables and API keys

You only need to set credentials for the apps you want to run. Follow the
provider's official guide or console to create each key, then paste it after
the `=` in your local `.env` file:

| Variable | Used by | How to get it |
|---|---|---|
| `GROQ_API_KEY` | `1.1`–`1.3`, `2.1`–`2.3`, `2.5`, `3.1`–`3.2`, `4.1` | Sign in to the [Groq Console API Keys page](https://console.groq.com/keys) and create a key. |
| `TAVILY_API_KEY` | `2.3` (optional; required to enable web search) | Create an account and get a key from the [Tavily API platform](https://app.tavily.com). See the [Tavily quickstart](https://docs.tavily.com/documentation/quickstart) for guidance. |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | `2.6` | Follow GitHub's guide to [create a fine-grained personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token). Grant only the repository access and permissions needed for the MCP tools you plan to use. |
| `GITHUB_MCP_SERVER_URL` | `2.6` (optional) | No key required. Defaults to `https://api.githubcopilot.com/mcp/`; leave the template value unless you use another trusted MCP server. |
| `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` | `4.1` | Follow Langfuse's [tracing quickstart](https://langfuse.com/docs/observability/get-started): create/sign in to an account, create a project, then create API credentials in the project settings. Keep the secret key private. |
| `LANGFUSE_BASE_URL` | `4.1` (optional) | No key required. Use the base URL for your Langfuse Cloud region or self-hosted instance. The template defaults to `https://cloud.langfuse.com`; see the [Langfuse quickstart](https://langfuse.com/docs/observability/get-started) for region examples. |

Treat API keys and access tokens like passwords: keep them only in your local
`.env`, never paste them into source code, screenshots, issues, or commits, and
revoke and replace any key that is accidentally exposed.

LLM-powered apps send prompts to Groq. The search app sends search queries to
Tavily when that tool is enabled, and `4.1` sends traces to Langfuse. Do not
enter confidential or personal information unless you have permission to send
it to those services.

For `2.6`, use only an MCP server you trust. Its tools act with the permissions
of the GitHub token you provide; inspect the available tools and their
permissions before invoking them.

## Other Python files

The Python files in `agents/` and `tools/` provide agents and tools imported by
the numbered apps; they are not standalone applications. The helpers
`helper/create_db.py` and `helper/policy_ingest.py` can be run directly using
the commands above. `helper/policy_retrieve.py` is an optional command-line
example that queries the policy collection after it has been ingested:

```shell
python helper/policy_retrieve.py
```

The remaining files in `helper/` are shared implementation modules.

## Local data

The applications may create or update `sample_data.db`, `chroma_data/`,
`memory.txt`, and `memory.json` in the repository. These files are local
application data, not source code. The database and memory files listed above
are tracked in this repository, so review their contents and check `git status`
before committing. `memory.txt` and `memory.json` can contain conversation
details.
