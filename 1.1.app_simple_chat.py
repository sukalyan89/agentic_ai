import os
from dotenv import load_dotenv
import streamlit as st
from groq import Groq


# Load environment variables
load_dotenv()

# Initialize Groq client
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)



# token usage tracking
if "token_usage" not in st.session_state:
    st.session_state.token_usage = {
        "input": 0,
        "output": 0,
        "total": 0
    }

# adding groq api to make the chatbot response using llm 
def get_bot_response(user_message: str) -> str:
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": user_message
            }
        ]
    )

    return response.choices[0].message.content , response.usage



st.set_page_config(
    page_title="AI Chatbot Starter",
    page_icon="💬",
    layout="centered",
)

st.title("💬 AI Chatbot")
st.caption("A simple Streamlit chat interface — ready to connect to an AI model later.")

# Keep the conversation in session state while this browser session is active.
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! 👋 I'm your chatbot. What can I help you with?",
        }
    ]

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
                response,usage = get_bot_response(prompt)
                st.markdown(response)

                # Update cumulative token usage
                st.session_state.token_usage["input"] += usage.prompt_tokens
                st.session_state.token_usage["output"] += usage.completion_tokens
                st.session_state.token_usage["total"] += usage.total_tokens

                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )

            except Exception as e:
                st.error(f"Something went wrong: {e}")

with st.sidebar:
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
        st.rerun()
