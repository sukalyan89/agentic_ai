
# agents.py

import os
import time
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM


load_dotenv()


def run_agent(user_message: str):

    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY is missing from .env")

    # 1. Configure the LLM
    groq_llm = LLM(
        model="openai/openai/gpt-oss-20b",               # 👈 Prefix with 'openai/' instead of 'groq/'
        base_url="https://api.groq.com/openai/v1",       # 👈 Direct to Groq's endpoint
        api_key=os.environ.get("GROQ_API_KEY"),
        temperature=0.5
    )

    # 2. Define the agent
    analyst = Agent(
        role="Senior Data Analyst",

        goal=(
            "Answer analytical and technical questions "
            "clearly, accurately, and concisely."
        ),

        backstory=(
            "You are an experienced data analyst with "
            "expertise in Python, SQL, banking analytics, "
            "and data science. You explain technical "
            "concepts using practical examples."
        ),

        llm=groq_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1
    )

    # 3. Define the task
    analysis_task = Task(
        description=(
            "Answer the following user question:\n"
            "{question}\n\n"
            "Explain your answer clearly. "
            "Do not invent data or claim to have "
            "performed external research."
        ),

        expected_output=(
            "A clear and structured response to the "
            "user's question, with examples where useful."
        ),

        agent=analyst
    )

    # 4. Create the crew
    crew = Crew(
        agents=[analyst],
        tasks=[analysis_task],
        process=Process.sequential,
        verbose=True,
        memory=False
    )

    # 5. Execute
    start = time.perf_counter()

    result = crew.kickoff(
        inputs={"question": user_message}
    )

    duration = time.perf_counter() - start

    # 6. Capture token usage
    usage = crew.usage_metrics

    token_usage = {
        "input": getattr(usage, "prompt_tokens", 0) or 0,
        "output": getattr(usage, "completion_tokens", 0) or 0,
        "total": getattr(usage, "total_tokens", 0) or 0
    }

    return str(result.raw), token_usage, duration
