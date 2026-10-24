import streamlit as st

from agents.semantic_agent import get_memory_count, get_memory_store_path, run_agent


st.set_page_config(
    page_title="CrewAI Semantic Memory",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 CrewAI Chatbot")
st.caption("Powered by CrewAI + Groq, with optional semantic memory")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "token_usage" not in st.session_state:
    st.session_state.token_usage = {"input": 0, "output": 0, "total": 0}

if "last_latency" not in st.session_state:
    st.session_state.last_latency = 0.0

with st.sidebar:
    st.header("Agent Information")
    st.write("**Framework:** CrewAI")
    st.write("**LLM:** Groq")
    st.write("**Agent:** Senior Data Analyst")

    st.divider()

    st.header("Semantic memory")
    use_semantic_memory = st.toggle(
        "Retrieve context for each question",
        value=True,
        help="Search the knowledge base created by 1.4.Semantic_Memory.py and provide matching chunks to the agent.",
    )
    result_count = st.slider(
        "Context chunks to retrieve",
        min_value=1,
        max_value=10,
        value=5,
        disabled=not use_semantic_memory,
    )
    stored_chunks = get_memory_count()
    st.metric("Stored chunks", stored_chunks)
    st.caption(f"Storage: {get_memory_store_path()}")
    if stored_chunks == 0:
        st.info("No memories stored yet. Add documents in 1.4.Semantic_Memory.py.")

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
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask the agent something...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agent is working..."):
            try:
                answer, usage, duration, memories = run_agent(
                    prompt,
                    use_semantic_memory=use_semantic_memory,
                    result_count=result_count,
                )

                st.markdown(answer)
                if use_semantic_memory:
                    with st.expander("Retrieved semantic context"):
                        if memories:
                            for memory in memories:
                                st.markdown(
                                    f"**{memory.source} · chunk {memory.chunk_index} · "
                                    f"similarity {memory.similarity:.3f}**"
                                )
                                st.write(memory.text)
                        else:
                            st.caption("No matching memories were found.")

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )
                for key in ("input", "output", "total"):
                    st.session_state.token_usage[key] += usage[key]
                st.session_state.last_latency = duration
            except Exception as error:
                st.error(f"Agent execution failed: {error}")

    st.rerun()
