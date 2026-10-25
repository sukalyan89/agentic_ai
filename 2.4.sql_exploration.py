import streamlit as st

from helper.create_db import (
    DATABASE_PATH,
    MAX_RESULT_ROWS,
    WORKBOOK_PATH,
    create_database,
    get_database_tables,
    get_table_columns,
    run_read_query,
)


st.set_page_config(
    page_title="SQL Exploration",
    page_icon="🗃️",
    layout="wide",
)

st.title("🗃️ SQL Exploration")
st.caption("Import the sample Excel workbook and explore it with read-only SQL.")

try:
    if not DATABASE_PATH.is_file():
        create_database()
    tables = get_database_tables()
except Exception as error:
    st.error(f"Could not prepare the SQLite database: {error}")
    st.stop()

with st.sidebar:
    st.header("SQLite database")
    st.caption(f"Workbook: {WORKBOOK_PATH}")
    st.caption(f"Database: {DATABASE_PATH}")

    if st.button("Rebuild database from Excel", use_container_width=True):
        try:
            imported_tables = create_database(overwrite=True)
            st.success(
                "Imported "
                + ", ".join(
                    f"{name} ({count:,} rows)"
                    for name, count in imported_tables.items()
                )
            )
            st.rerun()
        except Exception as error:
            st.error(f"Database import failed: {error}")

    st.subheader("Tables")
    for table_name, row_count in tables.items():
        st.markdown(f"**`{table_name}`** · {row_count:,} rows")
        with st.expander(f"Columns in {table_name}"):
            for column_name, column_type in get_table_columns(table_name):
                st.code(f"{column_name} ({column_type})")

    st.info(
        "Only SELECT and WITH queries are accepted. Results are limited "
        f"to {MAX_RESULT_ROWS:,} rows."
    )

if "sql_query" not in st.session_state:
    first_table = next(iter(tables), "sheet1")
    st.session_state.sql_query = f"SELECT * FROM {first_table} LIMIT 10;"

with st.form("sql_query_form"):
    query = st.text_area(
        "SQL query",
        key="sql_query",
        height=180,
        help="Run one read-only SELECT or WITH query against the database.",
    )
    submitted = st.form_submit_button("Run query", type="primary")

if submitted:
    try:
        result, truncated = run_read_query(query)
        st.session_state.query_result = result
        st.session_state.query_error = None
        st.session_state.query_truncated = truncated
    except Exception as error:
        st.session_state.query_result = None
        st.session_state.query_error = str(error)

if st.session_state.get("query_error"):
    st.error(f"Query failed: {st.session_state.query_error}")
elif st.session_state.get("query_result") is not None:
    result = st.session_state.query_result
    st.subheader("Query result")
    st.caption(f"{len(result):,} row(s) · {len(result.columns):,} column(s)")
    st.dataframe(result, use_container_width=True, hide_index=True)
    if st.session_state.get("query_truncated"):
        st.warning(
            f"Only the first {MAX_RESULT_ROWS:,} rows are displayed. "
            "Add a LIMIT clause to narrow the result."
        )
elif tables:
    st.markdown(
        "Enter a query above and select **Run query**. For example:"
    )
    st.code(f"SELECT * FROM {next(iter(tables))} LIMIT 10;", language="sql")
