from typing import Any, Callable, Optional

from agents.multi_agent_orchestrator import run_agent as run_multi_agent
from helper.langfuse_tracing import initialize_langfuse


StageEventCallback = Callable[[str, dict[str, Any]], None]


def run_agent(
    user_message: str,
    on_stage_event: Optional[StageEventCallback] = None,
) -> tuple[str, dict[str, int], float, list[dict[str, Any]], list[dict[str, str]]]:
    langfuse = initialize_langfuse()
    try:
        with langfuse.start_as_current_observation(
            as_type="span",
            name="multi-agent-customer-care",
            input={"question": user_message},
            metadata={"application": "4.1.app_crew_langfuse"},
        ) as request_trace:
            def report_stage(stage: str, update: dict[str, Any]) -> None:
                if on_stage_event:
                    on_stage_event(stage, update)
                langfuse.flush()

            result = run_multi_agent(
                user_message,
                on_stage_event=report_stage,
            )
            answer, _, _, _, stage_updates = result
            route = next(
                (
                    update["message"]
                    for update in stage_updates
                    if update["stage"] == "router_completed"
                ),
                "No route was reported.",
            )
            request_trace.update(
                output={"answer": answer},
                metadata={
                    "application": "4.1.app_crew_langfuse",
                    "route": route,
                },
            )
    finally:
        langfuse.flush()

    return result
