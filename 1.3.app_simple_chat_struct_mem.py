import json
import os
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st
from groq import Groq


# Load environment variables
load_dotenv()

MEMORY_PATH = Path(__file__).with_name("memory.json")


# Initialize Groq client
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


# ---------- Structured memory helpers ----------
def default_memory() -> dict:
    return {
        "profile": {},
        "facts": [],
        "notes": []
    }


def load_memory() -> dict:
    if not MEMORY_PATH.exists():
        MEMORY_PATH.write_text(json.dumps(default_memory(), indent=2), encoding="utf-8")

    try:
        data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = default_memory()
        save_memory(data)

    if not isinstance(data, dict):
        data = default_memory()
        save_memory(data)

    return {
        "profile": data.get("profile", {}),
        "facts": data.get("facts", []),
        "notes": data.get("notes", [])
    }


def save_memory(memory_data: dict) -> None:
    MEMORY_PATH.write_text(json.dumps(memory_data, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_memory(memory_data: dict, new_payload: dict) -> dict:
    if not isinstance(new_payload, dict):
        return memory_data

    memory_update = new_payload.get("memory_update", {})
    if not isinstance(memory_update, dict):
        return memory_data

    merged = memory_data.copy()
    merged["profile"] = {**merged.get("profile", {}), **memory_update.get("profile", {})}

    for key in ["facts", "notes"]:
        current_values = merged.setdefault(key, [])
        if not isinstance(current_values, list):
            current_values = []
        for item in memory_update.get(key, []):
            if item not in current_values:
                current_values.append(item)
        merged[key] = current_values

    return merged


# ---------- Token usage tracking ----------
if "token_usage" not in st.session_state:
    st.session_state.token_usage = {
        "input": 0,
        "output": 0,
        "total": 0
    }


# Return structured JSON from the assistant and store only the relevant part in JSON memory.
def get_bot_response(user_message: str, memory_data: dict):
    memory_context = json.dumps(memory_data, ensure_ascii=False)

    system_prompt = (
        "You are a helpful assistant. "
        "Use the saved memory only as context. "
        "Return ONLY valid JSON with exactly these keys: answer, memory_update. "
        "The answer field should be the plain response to the user. "
        "The memory_update field should contain only relevant facts to remember, using this structure: "
        "{\"profile\": {\"key\": \"value\"}, \"facts\": [{\"topic\": \"name\", \"value\": \"Alice\"}], \"notes\": [\"Likes Python\"]}. "
        "Do not expose the entire memory store in the answer."
        f"\n\nCurrent memory JSON:\n{memory_context}"
    )

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )

    raw_text = response.choices[0].message.content

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        payload = {
            "answer": raw_text,
            "memory_update": {"facts": [], "notes": []}
        }

    return payload, response.usage


st.set_page_config(
    page_title="AI Chatbot Starter",
    page_icon="💬",
    layout="centered",
)

st.title("💬 Structured Memory Chatbot")
st.caption("Memory is saved as JSON and kept out of the visible chat flow.")

# Keep the conversation in session state while this browser session is active.
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I can remember important details in memory.json and keep them separate from the chat display.",
            "memory_update": {"notes": ["Bot initialized"]}
        }
    ]

if "memory_data" not in st.session_state:
    st.session_state.memory_data = load_memory()

# Render the conversation so far.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            st.markdown(message["content"])
            if message.get("memory_update"):
                memory_flag = message["memory_update"]
                if memory_flag and any(memory_flag.values()):
                    st.caption("🧠 Memory updated")

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
                memory_data = load_memory()
                payload, usage = get_bot_response(prompt, memory_data)

                # update cumulative token usage
                st.session_state.token_usage["input"] += usage.prompt_tokens
                st.session_state.token_usage["output"] += usage.completion_tokens
                st.session_state.token_usage["total"] += usage.total_tokens

                answer_text = payload.get("answer", "")
                memory_update = payload.get("memory_update", {})

                st.markdown(answer_text)
                if memory_update:
                    st.caption("🧠 Memory updated")

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer_text,
                        "memory_update": memory_update
                    }
                )

                # save only relevant structured memory
                st.session_state.memory_data = merge_memory(memory_data, payload)
                save_memory(st.session_state.memory_data)

            except Exception as e:
                st.error(f"Something went wrong: {e}")

with st.sidebar:
    st.header("🧠 Memory Store")
    st.json(load_memory())

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
        st.session_state.memory_data = default_memory()
        save_memory(default_memory())
        st.rerun()
