import os
import time
from typing import Any, Callable, Optional

from crewai import Agent, Crew, LLM, Process, Task
from dotenv import load_dotenv

from helper.create_db import (
    DATABASE_PATH,
    create_database,
    get_database_tables,
    get_table_columns,
)
from tools.sql_tool import SqlQueryTool


load_dotenv()

SqlToolEventCallback = Callable[
    [str, str, Optional[dict[str, Any]], Optional[str]], None
]
SqlToolCall = dict[str, Any]


def get_database_schema() -> str:
    if not DATABASE_PATH.is_file():
        create_database()

    tables = get_database_tables()
    if "sheet1" not in tables:
        raise ValueError(
            f"Expected table 'sheet1' in {DATABASE_PATH}; found: "
            f"{', '.join(tables) or 'no tables'}."
        )

    columns = get_table_columns("sheet1")
    column_lines = "\n".join(
        f"- {name} ({column_type or 'TEXT'})" for name, column_type in columns
    )
    return (
        f"Database: SQLite at {DATABASE_PATH}\n"
        f"Table: sheet1 ({tables['sheet1']} rows)\n"
        "Columns:\n"
        f"{column_lines}"
    )


def run_agent(
    user_message: str,
    on_tool_event: Optional[SqlToolEventCallback] = None,
) -> tuple[str, dict[str, int], float, list[SqlToolCall]]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from .env")

    schema = get_database_schema()
    tool_calls: list[SqlToolCall] = []

    def record_tool_event(
        event: str,
        query: str,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        if event == "completed":
            tool_calls.append(
                {"query": query, "result": result or {}}
            )
        if on_tool_event:
            on_tool_event(event, query, result, error)

    sql_tool = SqlQueryTool(event_callback=record_tool_event)
    groq_llm = LLM(
        model="openai/openai/gpt-oss-20b",
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
        temperature=0.2,
    )
    analyst = Agent(
        role="Data Analyst",
        goal=(
            "Answer questions about the sales dataset accurately by generating "
            "and executing SQL when a data lookup or calculation is needed."
        ),
        backstory=(
            "You are a careful data analyst. You use the provided SQLite schema, "
            "check the database results, and never invent dataset values."
        ),
        llm=groq_llm,
        tools=[sql_tool],
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
    analysis_task = Task(
        description=(
            "Answer the user's question. Use the SQL tool for questions that "
            "require facts, filtering, comparisons, or calculations from the "
            "dataset. Use only read-only SELECT queries against the sheet1 "
            "table. The database tool enforces read-only execution. Inspect "
            "the returned rows and base all dataset-specific claims on them. "
            "If the query fails, revise it using the schema and try again. "
            "For questions unrelated to the dataset, answer directly without "
            "calling the tool. Do not invent data.\n\n"
            "Database schema:\n{schema}\n\n"
            "User question:\n{question}"
        ),
        expected_output=(
            "A concise, clear answer. Include the relevant result values and "
            "briefly explain how they answer the question."
        ),
        agent=analyst,
    )
    crew = Crew(
        agents=[analyst],
        tasks=[analysis_task],
        process=Process.sequential,
        verbose=True,
        memory=False,
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
    return str(result.raw), token_usage, duration, tool_calls
