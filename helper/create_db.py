import re
import sqlite3
import time
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_PATH = PROJECT_ROOT / "data_assets" / "sample_data.xlsx"
DATABASE_PATH = PROJECT_ROOT / "sample_data.db"
MAX_RESULT_ROWS = 5000


def _table_name(sheet_name: str) -> str:
    normalized = re.sub(r"\W+", "_", sheet_name.strip().lower()).strip("_")
    if not normalized:
        raise ValueError(f"Sheet name {sheet_name!r} cannot be used as a table name.")
    if normalized[0].isdigit():
        normalized = f"sheet_{normalized}"
    return normalized


def create_database(
    workbook_path: Path = WORKBOOK_PATH,
    database_path: Path = DATABASE_PATH,
    overwrite: bool = False,
) -> dict[str, int]:
    """Import every workbook sheet into a SQLite table."""
    if not workbook_path.is_file():
        raise FileNotFoundError(f"Excel workbook not found: {workbook_path}")
    if database_path.exists() and not overwrite:
        return get_database_tables(database_path)

    sheets = pd.read_excel(workbook_path, sheet_name=None)
    if not sheets:
        raise ValueError(f"No worksheets found in {workbook_path}")

    tables: dict[str, pd.DataFrame] = {}
    for sheet_name, frame in sheets.items():
        table = _table_name(sheet_name)
        if table in tables:
            raise ValueError(
                f"Multiple worksheet names map to the same SQLite table: {table}"
            )
        tables[table] = frame

    with sqlite3.connect(database_path) as connection:
        old_tables = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        new_table_names = set(tables)
        for (old_name,) in old_tables:
            if old_name not in new_table_names:
                quoted_name = old_name.replace('"', '""')
                connection.execute(f'DROP TABLE "{quoted_name}"')
        for table_name, frame in tables.items():
            frame.to_sql(table_name, connection, if_exists="replace", index=False)

    return {name: len(frame) for name, frame in tables.items()}


def get_database_tables(
    database_path: Path = DATABASE_PATH,
) -> dict[str, int]:
    """Return table names and their row counts from the generated database."""
    if not database_path.is_file():
        return {}

    with sqlite3.connect(database_path) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return {
            table_name: connection.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]
            for (table_name,) in tables
        }


def get_table_columns(
    table_name: str,
    database_path: Path = DATABASE_PATH,
) -> list[tuple[str, str]]:
    if not database_path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {database_path}")
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", table_name):
        raise ValueError("Invalid table name.")

    with sqlite3.connect(database_path) as connection:
        columns = connection.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()
    return [(column[1], column[2] or "TEXT") for column in columns]


def run_read_query(
    query: str,
    database_path: Path = DATABASE_PATH,
    max_rows: int = MAX_RESULT_ROWS,
    timeout_seconds: int = 5,
) -> tuple[pd.DataFrame, bool]:
    """Execute one read-only SELECT/CTE query and cap displayed results."""
    if not database_path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {database_path}")
    if not query.strip():
        raise ValueError("Enter a SQL query to execute.")

    without_comments = re.sub(r"/\*.*?\*/|--[^\r\n]*", "", query, flags=re.S)
    if not re.match(r"\s*(SELECT|WITH)\b", without_comments, flags=re.I):
        raise ValueError("Only read-only SELECT or WITH queries are allowed.")

    deadline = time.monotonic() + timeout_seconds
    database_uri = f"{database_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(database_uri, uri=True) as connection:
        connection.execute("PRAGMA query_only = ON")
        connection.set_progress_handler(
            lambda: int(time.monotonic() >= deadline), 1000
        )
        cursor = connection.execute(query)
        if cursor.description is None:
            raise ValueError("The query did not return a result set.")
        rows = cursor.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows
        if truncated:
            rows = rows[:max_rows]
        result = pd.DataFrame(
            rows,
            columns=[column[0] for column in cursor.description],
        )
    return result, truncated


if __name__ == "__main__":
    imported_tables = create_database(overwrite=True)
    print(f"Created SQLite database: {DATABASE_PATH}")
    for table_name, row_count in imported_tables.items():
        print(f"  {table_name}: {row_count:,} rows")
