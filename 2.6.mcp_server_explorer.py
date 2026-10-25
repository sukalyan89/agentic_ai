import streamlit as st

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
    # Show and store the user's message.
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Placeholder backend: replace this function with an LLM/API call later.
    def get_bot_response(user_message: str) -> str:
        return f"Hello world! 👋 You said: **{user_message}**"

    response = get_bot_response(prompt)

    # Show and store the assistant's response.
    st.session_state.messages.append(
        {"role": "assistant", "content": response}
    )
    with st.chat_message("assistant"):
        st.markdown(response)

with st.sidebar:
    st.header("About")
    st.write(
        "This is a frontend starter built with Streamlit. "
        "The backend currently returns a simple Hello World response."
    )
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
