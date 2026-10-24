import os
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st
from groq import Groq


# Load environment variables
load_dotenv()

MEMORY_PATH = Path(__file__).with_name("memory.txt")


# Initialize Groq client
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


# ---------- Memory helpers ----------
def load_memory() -> str:
    if not MEMORY_PATH.exists():
        MEMORY_PATH.write_text("", encoding="utf-8")
    return MEMORY_PATH.read_text(encoding="utf-8")


def save_memory(content: str) -> None:
    MEMORY_PATH.write_text(content, encoding="utf-8")


def append_to_memory(user_message: str, assistant_message: str) -> str:
    existing = load_memory()
    entry = (
        f"User: {user_message}\n"
        f"Assistant: {assistant_message}\n\n"
    )
    updated = existing + entry
    save_memory(updated)
    return updated


# ---------- Token usage tracking ----------
if "token_usage" not in st.session_state:
    st.session_state.token_usage = {
        "input": 0,
        "output": 0,
        "total": 0
    }


# adding groq api to make the chatbot response using llm
def get_bot_response(user_message: str, memory_text: str) -> str:
    memory_context = (
        "You can refer to the saved memory below when helpful. "
        "If there is no memory, ignore it.\n\n"
        f"Memory:\n{memory_text if memory_text.strip() else 'No saved memory yet.'}"
    )

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": memory_context
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    )

    return response.choices[0].message.content, response.usage


st.set_page_config(
    page_title="AI Chatbot Starter",
    page_icon="💬",
    layout="centered",
)

st.title("💬 AI Chatbot")
st.caption("A simple Streamlit chat interface with persistent memory saved to a local file.")

# Keep the conversation in session state while this browser session is active.
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! 👋 I'm your chatbot. I can remember details from memory.txt and refer to them in replies.",
        }
    ]

if "memory_text" not in st.session_state:
    st.session_state.memory_text = load_memory()

# Render the conversation so far.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input stays at the bottom of the page.
prompt = st.chat_input("Type your message...")

if prompt:
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                memory_text = load_memory()
                response, usage = get_bot_response(prompt, memory_text)
                st.markdown(response)

                # Update cumulative token usage
                st.session_state.token_usage["input"] += usage.prompt_tokens
                st.session_state.token_usage["output"] += usage.completion_tokens
                st.session_state.token_usage["total"] += usage.total_tokens

                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )

                # Save chat interaction into memory file
                st.session_state.memory_text = append_to_memory(prompt, response)

            except Exception as e:
                st.error(f"Something went wrong: {e}")

with st.sidebar:
    st.header("🧠 Memory")
    current_memory = load_memory()

    edited_memory = st.text_area(
        "memory.txt",
        value=current_memory,
        height=220,
        key="memory_editor"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Memory"):
            save_memory(edited_memory)
            st.session_state.memory_text = edited_memory
            st.success("Memory saved.")
    with col2:
        if st.button("🔄 Refresh"):
            st.session_state.memory_text = load_memory()
            st.rerun()

    st.divider()
    st.header("📊 Token Usage")

    usage = st.session_state.token_usage

    st.metric("Input Tokens", f"{usage['input']:,}")
    st.metric("Output Tokens", f"{usage['output']:,}")
    st.metric("Total Tokens", f"{usage['total']:,}")

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.token_usage = {
            "input": 0,
            "output": 0,
            "total": 0
        }
        st.session_state.memory_text = ""
        save_memory("")
        st.rerun()
