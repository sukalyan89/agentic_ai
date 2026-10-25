import json
from typing import Any, Callable, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from helper.create_db import DATABASE_PATH, MAX_RESULT_ROWS, run_read_query


SQL_TOOL_MAX_ROWS = 100
SqlToolEventCallback = Callable[[str, str, Optional[dict[str, Any]], Optional[str]], None]


class SqlQueryInput(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description=(
            "A single read-only SQLite SELECT query that answers the user's "
            "question using the sheet1 table."
        ),
    )


class SqlQueryTool(BaseTool):
    name: str = "query_sales_database"
    description: str = (
        "Execute one read-only SQLite SELECT query against the sheet1 table. "
        "Use the provided schema to write valid SQL. Queries are limited to "
        f"{SQL_TOOL_MAX_ROWS} result rows."
    )
    args_schema: Type[BaseModel] = SqlQueryInput
    _event_callback: Optional[SqlToolEventCallback] = PrivateAttr(default=None)

    def __init__(
        self,
        event_callback: Optional[SqlToolEventCallback] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._event_callback = event_callback

    def _notify(
        self,
        event: str,
        query: str,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        if self._event_callback:
            self._event_callback(event, query, result, error)

    def _run(self, query: str) -> str:
        self._notify("started", query)
        try:
            dataframe, truncated = run_read_query(
                query,
                database_path=DATABASE_PATH,
                max_rows=min(SQL_TOOL_MAX_ROWS, MAX_RESULT_ROWS),
            )
            result = {
                "columns": [str(column) for column in dataframe.columns],
                "rows": dataframe.astype(object)
                .where(dataframe.notna(), None)
                .to_dict(orient="records"),
                "truncated": truncated,
            }
            self._notify("completed", query, result)
            return json.dumps(result, default=str, ensure_ascii=False)
        except Exception as error:
            self._notify("error", query, error=str(error))
            raise
