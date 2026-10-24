
# app.py

import streamlit as st
from agents.simple_agent import run_agent

st.set_page_config(
    page_title="CrewAI Demo",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 CrewAI Chatbot")
st.caption("Powered by CrewAI + Groq")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "token_usage" not in st.session_state:
    st.session_state.token_usage = {
        "input": 0,
        "output": 0,
        "total": 0
    }

if "last_latency" not in st.session_state:
    st.session_state.last_latency = 0.0


# Sidebar
with st.sidebar:

    st.header("Agent Information")
    st.write("**Framework:** CrewAI")
    st.write("**LLM:** Groq Llama 3.3 70B")
    st.write("**Agent:** Senior Data Analyst")

    st.divider()

    st.header("📊 Token Usage")

    usage = st.session_state.token_usage

    st.metric("Input Tokens", f"{usage['input']:,}")
    st.metric("Output Tokens", f"{usage['output']:,}")
    st.metric("Total Tokens", f"{usage['total']:,}")

    st.divider()

    st.header("⏱ Performance")
    st.metric(
        "Last Execution",
        f"{st.session_state.last_latency:.2f} sec"
    )

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.token_usage = {
            "input": 0,
            "output": 0,
            "total": 0
        }
        st.session_state.last_latency = 0.0
        st.rerun()


# Display previous messages
for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# User input
prompt = st.chat_input("Ask the agent something...")

if prompt:

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        with st.spinner("Agent is working..."):

            try:
                answer, usage, duration = run_agent(prompt)

                st.markdown(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

                # Update token usage
                for key in ["input", "output", "total"]:
                    st.session_state.token_usage[key] += (
                        usage[key]
                    )

                st.session_state.last_latency = duration

            except Exception as e:
                st.error(f"Agent execution failed: {e}")

    st.rerun()
