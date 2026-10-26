import os
import time
from typing import Any, Callable, Optional

from crewai import Agent, Crew, LLM, Process, Task
from dotenv import load_dotenv

from agents.sql_agent import get_database_schema
from tools.sql_tool import SqlQueryTool


load_dotenv()

SqlToolEventCallback = Callable[
    [str, str, Optional[dict[str, Any]], Optional[str]], None
]
SqlToolCall = dict[str, Any]


def run_agent(
    user_message: str,
    on_tool_event: Optional[SqlToolEventCallback] = None,
) -> tuple[str, dict[str, int], float, list[SqlToolCall]]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from .env")

    schema = get_database_schema()
    tool_calls: list[SqlToolCall] = []
    task_outputs: list[str] = []

    def record_tool_event(
        event: str,
        query: str,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        if event == "completed":
            tool_calls.append({"query": query, "result": result or {}})
        if on_tool_event:
            on_tool_event(event, query, result, error)

    def record_task_output(task_output: Any) -> None:
        output = getattr(task_output, "raw", None)
        if not isinstance(output, str) or not output.strip():
            raise ValueError("The agent returned an empty task output.")

        task_outputs.append(output.strip())
        if len(task_outputs) == 1:
            record_tool_event("plan", "", {"text": task_outputs[0]})

    sql_tool = SqlQueryTool(event_callback=record_tool_event)
    groq_llm = LLM(
        model="openai/openai/gpt-oss-20b",
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
        temperature=0.2,
    )
    planner = Agent(
        role="Business Analysis Planner",
        goal=(
            "Break the user's business ask into a concise, ordered work plan "
            "that can be answered with evidence from the provided dataset."
        ),
        backstory=(
            "You are a pragmatic analyst who makes the work plan explicit "
            "without exposing private chain-of-thought."
        ),
        llm=groq_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,
    )
    analyst = Agent(
        role="Business Data Analyst",
        goal=(
            "Fulfil business asks with accurate, actionable insights grounded "
            "in the sales dataset."
        ),
        backstory=(
            "You are a careful data analyst. You use the provided SQLite schema, "
            "check database results, distinguish evidence from recommendations, "
            "and never invent dataset values."
        ),
        llm=groq_llm,
        tools=[sql_tool],
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
    planning_task = Task(
        description=(
            "Break the user's business ask into 3-5 short, ordered steps. "
            "Make the steps specific to the ask and dataset schema, including "
            "what evidence or comparison is needed. Do not answer the ask or "
            "write hidden reasoning; return only a concise numbered checklist.\n\n"
            "Database schema:\n{schema}\n\n"
            "User question:\n{question}"
        ),
        expected_output="A concise numbered work plan of 3-5 concrete steps.",
        agent=planner,
    )
    analysis_task = Task(
        description=(
            "Fulfil the user's business ask by following the work plan below. "
            "Use the SQL tool to retrieve and calculate the dataset evidence "
            "needed for each data-specific step. Use only read-only SELECT "
            "queries against the sheet1 table. Inspect returned rows, and base "
            "every dataset-specific claim on those results. If a query fails, "
            "revise it using the schema and try again. Do not invent data. "
            "Explain the key insight and why it matters to the business, then "
            "give practical recommendations supported by the evidence. "
            "If the ask is unrelated to the dataset, say so clearly.\n\n"
            "Database schema:\n{schema}\n\n"
            "User business ask:\n{question}"
        ),
        expected_output=(
            "A clear business answer with data-backed findings, their business "
            "implications, and actionable recommendations."
        ),
        agent=analyst,
        context=[planning_task],
    )
    crew = Crew(
        agents=[planner, analyst],
        tasks=[planning_task, analysis_task],
        process=Process.sequential,
        verbose=True,
        memory=False,
        task_callback=record_task_output,
    )

    start = time.perf_counter()
    result = crew.kickoff(inputs={"question": user_message, "schema": schema})
    duration = time.perf_counter() - start
    usage = crew.usage_metrics
    token_usage = {
        "input": getattr(usage, "prompt_tokens", 0) or 0,
        "output": getattr(usage, "completion_tokens", 0) or 0,
        "total": getattr(usage, "total_tokens", 0) or 0,
    }
    if not task_outputs:
        raise RuntimeError("The agent completed without producing a work plan.")

    response = (
        f"### Work plan\n{task_outputs[0]}\n\n"
        f"### Business insights\n{result.raw}"
    )
    return response, token_usage, duration, tool_calls
