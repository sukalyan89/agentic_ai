# Streamlit AI Chatbot Starter

A minimal browser-based chat UI with a placeholder Hello World backend.

## 1. Requirements
- Python 3.9+
- pip

## 2. Install dependencies

Open a terminal in this folder and run:

```bash
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows Command Prompt**
```bat
.venv\Scripts\activate.bat
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Then install Streamlit:

```bash
pip install -r requirements.txt
```

## 3. Run the app

```bash
streamlit run app.py
```

Streamlit will open the app in your browser. If it doesn't, visit the local URL shown in the terminal (usually `http://localhost:8501`).

## Where to connect an AI model later

In `app.py`, replace the `get_bot_response(user_message)` function with a call to your chosen model or API. Keep API keys in environment variables or Streamlit secrets rather than hard-coding them in the source.

## Current features
- Chat-style message bubbles
- Input box at the bottom
- Conversation stored in Streamlit session state
- Sidebar with a Clear chat button
- Placeholder backend response
