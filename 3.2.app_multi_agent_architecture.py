from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue

import pandas as pd
import streamlit as st

from agents.multi_agent_orchestrator import run_agent
from agents.sql_agent import get_database_schema
from helper.create_db import DATABASE_PATH, create_database
from tools.policy_search_tool import POLICY_COLLECTION_NAME, POLICY_STORE_PATH


st.set_page_config(
    page_title="Multi-Agent Customer Care",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 Multi-Agent Customer Care")
st.caption(
    "A request router sends policy and grievance questions to Customer Care, "
    "and order or sales questions to the SQL specialist."
)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "token_usage" not in st.session_state:
    st.session_state.token_usage = {"input": 0, "output": 0, "total": 0}

if "last_latency" not in st.session_state:
    st.session_state.last_latency = 0.0

if "last_sql_calls" not in st.session_state:
    st.session_state.last_sql_calls = []

try:
    schema = get_database_schema()
except Exception as error:
    st.error(f"Could not load the SQL database: {error}")
    if st.button("Create or rebuild database from sample_data.xlsx"):
        try:
            imported = create_database(overwrite=True)
            st.success(f"Imported database tables: {imported}")
            st.rerun()
        except Exception as import_error:
            st.error(f"Database import failed: {import_error}")
    st.stop()

with st.sidebar:
    st.header("Multi-agent workflow")
    st.write("**Agents:** Router → Customer Care / Sales Data → Response Writer")
    st.write("**Policy source:** ChromaDB")
    st.caption(f"Collection: {POLICY_COLLECTION_NAME}")
    st.caption(f"Policy store: {POLICY_STORE_PATH}")
    st.write("**Sales tool:** Read-only SQLite")
    st.caption(f"Database: {DATABASE_PATH}")

    st.divider()
    st.header("Database schema")
    st.code(schema, language="text")

    st.divider()
    st.header("Latest SQL results")
    if st.session_state.last_sql_calls:
        for call_number, call in enumerate(st.session_state.last_sql_calls, start=1):
            with st.expander(f"SQL call {call_number}", expanded=(call_number == 1)):
                st.code(call["query"], language="sql")
                result = call["result"]
                rows = result.get("rows", [])
                st.caption(
                    f"{len(rows):,} row(s), "
                    f"{len(result.get('columns', [])):,} column(s)"
                )
                if rows:
                    st.dataframe(
                        pd.DataFrame(rows),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("The query returned no rows.")
                if result.get("truncated"):
                    st.warning("The tool limited the result to 100 rows.")
    else:
        st.caption("SQL statements and results will appear here after tool use.")
 
    st.divider()
    st.header("Token usage")
    usage = st.session_state.token_usage
    st.metric("Input tokens", f"{usage['input']:,}")
    st.metric("Output tokens", f"{usage['output']:,}")
    st.metric("Total tokens", f"{usage['total']:,}")

    st.divider()
    st.header("Performance")
    st.metric("Last execution", f"{st.session_state.last_latency:.2f} sec")

    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_sql_calls = []
        st.session_state.token_usage = {"input": 0, "output": 0, "total": 0}
        st.session_state.last_latency = 0.0
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        stage_updates = message.get("stage_updates", [])
        if stage_updates:
            with st.expander("Agent activity", expanded=False):
                for update in stage_updates:
                    st.write(update["message"])
        st.markdown(message["content"])

prompt = st.chat_input(
    "Ask about company policy, a complaint, an order, or sales data..."
)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.last_sql_calls = []

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("Agent is working...", expanded=True) as progress:
            tool_events = Queue()

            def on_stage_event(event, update):
                tool_events.put((event, update))

            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    agent_future = executor.submit(
                        run_agent,
                        prompt,
                        on_stage_event=on_stage_event,
                    )
                    while not agent_future.done() or not tool_events.empty():
                        try:
                            event, update = tool_events.get(
                                timeout=0.2 if not agent_future.done() else 0
                            )
                        except Empty:
                            continue

                        if event == "started":
                            progress.write(update["message"])
                        elif event == "sql_started":
                            progress.write(update["message"])
                            progress.code(
                                update["message"].partition("\n")[2],
                                language="sql",
                            )
                        elif event.endswith("_error"):
                            progress.error(update["message"])
                        else:
                            progress.write(update["message"])

                    (
                        answer,
                        usage,
                        duration,
                        sql_calls,
                        stage_updates,
                    ) = agent_future.result()

                progress.update(
                    label="Agent response ready",
                    state="complete",
                    expanded=True,
                )
                st.markdown(answer)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "stage_updates": stage_updates,
                    }
                )
                st.session_state.last_sql_calls = sql_calls
                for key in ("input", "output", "total"):
                    st.session_state.token_usage[key] += usage[key]
                st.session_state.last_latency = duration
            except Exception as error:
                st.error(f"Agent execution failed: {error}")
...........kojiboijihm....
    st.rerun()
