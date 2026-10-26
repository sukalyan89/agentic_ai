import os
import time
from typing import Any, Callable, Optional

from crewai import Agent, Crew, LLM, Process, Task
from dotenv import load_dotenv

from agents.sql_agent import get_database_schema
from tools.policy_search_tool import PolicySearchTool
from tools.sql_tool import SqlQueryTool


load_dotenv()

StageEventCallback = Callable[[str, dict[str, Any]], None]
SqlToolCall = dict[str, Any]
TokenUsage = dict[str, int]


def _usage_metrics(crew: Crew) -> TokenUsage:
    usage = crew.usage_metrics
    return {
        "input": getattr(usage, "prompt_tokens", 0) or 0,
        "output": getattr(usage, "completion_tokens", 0) or 0,
        "total": getattr(usage, "total_tokens", 0) or 0,
    }


def _run_task(
    agent: Agent,
    task: Task,
    inputs: dict[str, str],
) -> tuple[str, TokenUsage]:
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
        memory=False,
    )
    result = crew.kickoff(inputs=inputs)
    return str(result.raw), _usage_metrics(crew)


def run_agent(
    user_message: str,
    on_stage_event: Optional[StageEventCallback] = None,
) -> tuple[str, TokenUsage, float, list[SqlToolCall], list[dict[str, str]]]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from .env")

    start = time.perf_counter()
    stage_updates: list[dict[str, str]] = []
    sql_calls: list[SqlToolCall] = []
    token_usage: TokenUsage = {"input": 0, "output": 0, "total": 0}

    def emit_stage(stage: str, message: str) -> None:
        update = {"stage": stage, "message": message}
        stage_updates.append(update)
        if on_stage_event:
            on_stage_event(stage, update)

    llm = LLM(
        model="openai/openai/gpt-oss-20b",
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
        temperature=0.2,
    )
    router = Agent(
        role="Customer Request Router",
        goal=(
            "Identify whether a customer message needs company policy support, "
            "sales or order data, or a general response."
        ),
        backstory=(
            "You route each request to the right specialist. Choose POLICY for "
            "policy, complaint, return, refund, or grievance guidance; choose "
            "SALES for a specific order lookup or questions requiring sales "
            "records; otherwise choose GENERAL. When the user asks how a policy "
            "applies to an order, choose POLICY."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,
    )
    router_task = Task(
        description=(
            "Classify the user request into exactly one category: POLICY, "
            "SALES, or GENERAL. Return only the category word, with no "
            "explanation or other text.\n\nUser request:\n{question}"
        ),
        expected_output="Exactly POLICY, SALES, or GENERAL.",
        agent=router,
    )

    emit_stage("router_started", "Router is identifying the request type.")
    route_output, route_usage = _run_task(router, router_task, {"question": user_message})
    token_usage = {
        key: token_usage[key] + route_usage[key] for key in token_usage
    }
    route = route_output.strip().splitlines()[0].strip("`*:# .").upper()
    if route not in {"POLICY", "SALES", "GENERAL"}:
        raise ValueError(
            f"Router returned unsupported category {route_output!r}; "
            "expected POLICY, SALES, or GENERAL."
        )
    route_messages = {
        "POLICY": "Router selected Customer Care for policy or grievance guidance.",
        "SALES": "Router selected the Sales Data specialist for an order or sales lookup.",
        "GENERAL": "Router found no policy or sales lookup is needed.",
    }
    emit_stage("router_completed", route_messages[route])

    if route == "POLICY":
        emit_stage(
            "specialist_started",
            "Customer Care is checking the ingested company policies in Chroma.",
        )
        def on_policy_event(event: str, payload: dict[str, Any]) -> None:
            message = payload["message"]
            policies = payload.get("policies", [])
            if policies:
                policy_ids = ", ".join(
                    policy["policy_id"] for policy in policies
                )
                message = f"{message} Policies: {policy_ids}."
            emit_stage(event, message)

        policy_tool = PolicySearchTool(event_callback=on_policy_event)
        customer_care = Agent(
            role="Customer Care Policy Specialist",
            goal=(
                "Answer policy, complaint, and grievance questions using the "
                "retrieved company policy records."
            ),
            backstory=(
                "You are a careful customer care specialist. You never invent "
                "policy rules, clearly identify the applicable policy, and "
                "flag when the retrieved evidence does not settle a question."
            ),
            llm=llm,
            tools=[policy_tool],
            verbose=True,
            allow_delegation=False,
            max_iter=3,
        )
        specialist_task = Task(
            description=(
                "Use the policy search tool to find records relevant to the "
                "customer's issue. Base your assessment only on those records. "
                "Summarize the applicable policy IDs and conditions, explain "
                "what they mean for the customer, and call out missing details "
                "or escalation steps. Do not make a final customer-facing "
                "response yet.\n\nCustomer request:\n{question}"
            ),
            expected_output=(
                "An evidence-based internal summary of applicable policy "
                "records, conditions, and any unresolved details."
            ),
            agent=customer_care,
        )
        specialist_output, specialist_usage = _run_task(
            customer_care,
            specialist_task,
            {"question": user_message},
        )
    elif route == "SALES":
        emit_stage(
            "specialist_started",
            "Sales Data Specialist is reviewing the database schema and querying SQLite.",
        )
        schema = get_database_schema()

        def on_sql_event(
            event: str,
            query: str,
            result: Optional[dict[str, Any]],
            error: Optional[str],
        ) -> None:
            if event == "completed":
                sql_calls.append({"query": query, "result": result or {}})
                emit_stage(
                    "sql_completed",
                    f"Read-only SQL query returned {len((result or {}).get('rows', []))} row(s).",
                )
            elif event == "started":
                emit_stage("sql_started", f"Running read-only SQL:\n{query}")
            elif event == "error":
                emit_stage("sql_error", f"SQL query failed: {error}")

        sql_tool = SqlQueryTool(event_callback=on_sql_event)
        sales_specialist = Agent(
            role="Sales Data Specialist",
            goal=(
                "Answer order and sales questions accurately using read-only "
                "queries against the provided SQLite schema."
            ),
            backstory=(
                "You are a careful sales analyst. You inspect the schema, "
                "query only when needed, and base every data-specific claim "
                "on returned rows."
            ),
            llm=llm,
            tools=[sql_tool],
            verbose=True,
            allow_delegation=False,
            max_iter=3,
        )
        specialist_task = Task(
            description=(
                "Investigate the customer request using the database schema "
                "below. Use the read-only SQL tool for order or sales facts, "
                "and inspect the results before drawing conclusions. Do not "
                "invent missing values. Summarize the findings and any data "
                "limitations; do not write the final customer-facing answer yet.\n\n"
                "Database schema:\n{schema}\n\nCustomer request:\n{question}"
            ),
            expected_output=(
                "A concise summary of the SQL-backed findings and limitations."
            ),
            agent=sales_specialist,
        )
        specialist_output, specialist_usage = _run_task(
            sales_specialist,
            specialist_task,
            {"question": user_message, "schema": schema},
        )
    else:
        specialist_output = (
            "No policy or sales specialist was required. Answer the general "
            "request without claiming access to policy or sales records."
        )
        specialist_usage = {"input": 0, "output": 0, "total": 0}

    token_usage = {
        key: token_usage[key] + specialist_usage[key] for key in token_usage
    }
    specialist_summary = " ".join(specialist_output.split())
    if len(specialist_summary) > 500:
        specialist_summary = specialist_summary[:497] + "..."
    emit_stage(
        "specialist_completed",
        (
            f"Specialist evidence summary: {specialist_summary}"
            if route != "GENERAL"
            else "No specialist lookup was needed."
        ),
    )

    emit_stage("final_started", "Response Agent is preparing the customer-facing answer.")
    response_agent = Agent(
        role="Customer Response Writer",
        goal=(
            "Turn the specialist's evidence into a clear, empathetic, accurate "
            "answer tailored to the customer's question."
        ),
        backstory=(
            "You are a concise customer communications specialist. You never "
            "add unsupported policy or sales facts, and you state uncertainty "
            "plainly."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,
    )
    response_task = Task(
        description=(
            "Write the final response to the customer's request. Answer "
            "directly using the specialist findings below. Do not add policy "
            "or sales facts that are absent from those findings. If details "
            "are missing, say what is needed to proceed. Use a helpful, "
            "customer-friendly tone.\n\nRequest category: {category}\n"
            "Customer request:\n{question}\n\nSpecialist findings:\n{findings}"
        ),
        expected_output="A helpful, accurate customer-facing response.",
        agent=response_agent,
    )
    answer, response_usage = _run_task(
        response_agent,
        response_task,
        {
            "category": route,
            "question": user_message,
            "findings": specialist_output,
        },
    )
    token_usage = {
        key: token_usage[key] + response_usage[key] for key in token_usage
    }
    emit_stage("final_completed", "Final customer response is ready.")
    return (
        answer,
        token_usage,
        time.perf_counter() - start,
        sql_calls,
        stage_updates,
    )
