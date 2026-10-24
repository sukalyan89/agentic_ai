from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue

import streamlit as st

from agents.web_search_agent import is_search_configured, run_agent


st.set_page_config(
    page_title="CrewAI Web Search",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 CrewAI Web Search Assistant")
st.caption("Powered by CrewAI + Groq, with Tavily web search when needed")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "token_usage" not in st.session_state:
    st.session_state.token_usage = {"input": 0, "output": 0, "total": 0}

if "last_latency" not in st.session_state:
    st.session_state.last_latency = 0.0

if "last_web_searches" not in st.session_state:
    st.session_state.last_web_searches = []

with st.sidebar:
    st.header("Agent Information")
    st.write("**Framework:** CrewAI")
    st.write("**LLM:** Groq")
    st.write("**Web search:** Tavily")

    st.divider()
    st.header("Web search")
    search_configured = is_search_configured()
    use_web_search = st.toggle(
        "Allow agent to search the web",
        value=search_configured,
        disabled=not search_configured,
        help="The agent searches only when it needs current or externally verifiable information.",
    )
    if not search_configured:
        st.warning("Add TAVILY_API_KEY to your .env file to enable web search.")

    st.subheader("Latest search results")
    if st.session_state.last_web_searches:
        for search_index, search in enumerate(
            st.session_state.last_web_searches, start=1
        ):
            with st.expander(
                f"Search {search_index}: {search['query']}",
                expanded=(search_index == 1),
            ):
                for result in search["results"]:
                    st.markdown(f"**{result['title']}**")
                    st.markdown(f"[Open source]({result['url']})")
                    st.write(result["content"])
                    if result.get("score") is not None:
                        st.caption(f"Relevance: {result['score']:.3f}")
    else:
        st.caption("Search results will appear here when the agent uses Tavily.")

    st.divider()
    st.header("Token Usage")
    usage = st.session_state.token_usage
    st.metric("Input Tokens", f"{usage['input']:,}")
    st.metric("Output Tokens", f"{usage['output']:,}")
    st.metric("Total Tokens", f"{usage['total']:,}")

    st.divider()
    st.header("Performance")
    st.metric("Last Execution", f"{st.session_state.last_latency:.2f} sec")

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.token_usage = {"input": 0, "output": 0, "total": 0}
        st.session_state.last_latency = 0.0
        st.session_state.last_web_searches = []
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask a question...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.last_web_searches = []

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("Agent is working...", expanded=True) as progress:
            tool_events = Queue()

            def on_tool_event(event, query, results, error):
                tool_events.put((event, query, results, error))

            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    agent_future = executor.submit(
                        run_agent,
                        prompt,
                        use_web_search=use_web_search,
                        on_tool_event=on_tool_event,
                    )
                    while not agent_future.done() or not tool_events.empty():
                        try:
                            event, query, results, error = tool_events.get(
                                timeout=0.2 if not agent_future.done() else 0
                            )
                        except Empty:
                            continue

                        if event == "started":
                            progress.write(
                                f"🔎 Tavily search tool is being called: {query}"
                            )
                            progress.update(
                                label="🔎 Searching the web with Tavily...",
                                state="running",
                                expanded=True,
                            )
                        elif event == "completed":
                            progress.write(
                                f"✅ Tavily returned {len(results or [])} "
                                f"results for: {query}"
                            )
                        elif event == "error":
                            progress.error(f"Tavily search failed: {error}"                            )

                    answer, usage, duration, searches = agent_future.result()

                progress.update(
                    label="Agent response ready",
                    state="complete",
                    expanded=bool(searches),
                )
                st.markdown(answer)
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )
                st.session_state.last_web_searches = searches
                for key in ("input", "output", "total"):
                    st.session_state.token_usage[key] += usage[key]
                st.session_state.last_latency = duration
            except Exception as error:
                st.error(f"Agent execution failed: {error}")

    st.rerun()
