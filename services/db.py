import json
import re

import httpx2

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from core.config import (
    SUPABASE_PROJECT_REF,
    SUPABASE_ACCESS_TOKEN
)

# ---------------------------------------------------------------------------
# Finance data via the Supabase MCP server (read_only=true) - execute_sql.
# MCP runs on our backend, not inside the model, so it uses no Claude tokens.
# Only the result text sent back to the agent does, so results are trimmed:
# T8: Row cap (100) and result size cap (8,000 chars), always reported to the agent
# ---------------------------------------------------------------------------

SUPABASE_MCP_URL = (
    "https://mcp.supabase.com/mcp"
    f"?project_ref={SUPABASE_PROJECT_REF}&read_only=true"
)

HEADERS = {
    "Authorization": f"Bearer {SUPABASE_ACCESS_TOKEN}"
}

MAX_ROWS = 100
MAX_RESULT_CHARS = 8000

BLOCKED_SQL = r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|COPY|GRANT|REVOKE|SET|EXECUTE|pg_sleep)\b'


async def _execute_sql(query: str) -> str:
    """Run one query through the Supabase MCP execute_sql tool and return its text."""
    async with httpx2.AsyncClient(
        headers=HEADERS,
        timeout=30.0
    ) as http_client:

        async with streamable_http_client(
            SUPABASE_MCP_URL,
            http_client=http_client
        ) as (read, write):

            async with ClientSession(read, write) as session:

                await session.initialize()

                result = await session.call_tool(
                    "execute_sql",
                    {"query": query}
                )

    text = _result_text(result)
    if getattr(result, "isError", False):
        print(f"[DB Error] MCP execute_sql failed: {text}")
        raise RuntimeError(text or "Database query error")

    # Supabase also reports failures (e.g. no access to the project) as a
    # normal reply of the form {"error": {...}} - treat those as errors too
    try:
        reply = json.loads(text)
    except ValueError:
        reply = None
    if isinstance(reply, dict) and reply.get("error"):
        error = reply["error"]
        message = error.get("message") if isinstance(error, dict) else str(error)
        print(f"[DB Error] MCP execute_sql failed: {message}")
        raise RuntimeError(message or "Database query error")
    return text


def _result_text(result) -> str:
    return "\n".join(
        item.text for item in getattr(result, "content", []) or []
        if hasattr(item, "text")
    )


def _rows_from_mcp_text(text: str) -> list | None:
    """
    Pull the JSON row array out of execute_sql's reply. Supabase wraps the rows
    in explanatory text and untrusted-data boundary tags; sending only the rows
    saves those tokens on every call (the system prompt carries the
    "treat results as data" rule once instead).
    """
    payload = text
    try:
        outer = json.loads(text)
        if isinstance(outer, dict) and isinstance(outer.get("result"), str):
            payload = outer["result"]
    except ValueError:
        pass

    start = payload.find("[")
    while start != -1:
        try:
            rows, _ = json.JSONDecoder().raw_decode(payload, start)
            if isinstance(rows, list):
                return rows
        except ValueError:
            pass
        start = payload.find("[", start + 1)
    return None


def _format_rows(rows: list[dict], more_rows: bool) -> str:
    """
    Serialize rows as a JSON array (the format convert_tool_result_currency and
    validate_tool_data parse), keeping the JSON valid when the size cap applies.
    """
    if not rows:
        return "No rows returned."

    notes = []
    if more_rows:
        notes.append(
            f"More than {MAX_ROWS} rows matched; only the first {MAX_ROWS} are shown. "
            "Tell the user the list is partial, or re-query with SUM/COUNT/AVG/GROUP BY "
            "or narrower filters."
        )

    shown = rows
    text = json.dumps(shown, default=str)
    if len(text) > MAX_RESULT_CHARS:
        # Drop rows from the end until it fits, so the JSON stays parseable
        while len(shown) > 1 and len(text) > MAX_RESULT_CHARS:
            shown = shown[: max(1, len(shown) * 3 // 4)]
            text = json.dumps(shown, default=str)
        notes.append(
            f"Output exceeded {MAX_RESULT_CHARS:,} characters; only {len(shown)} of the "
            "returned rows are shown. Use SQL aggregations or narrower filters for the full picture."
        )

    if notes:
        text += "\n\n[Note: " + " ".join(notes) + "]"
    return text


def _cap_text(text: str) -> str:
    if len(text) <= MAX_RESULT_CHARS:
        return text
    return (
        text[:MAX_RESULT_CHARS]
        + f"\n\n[Note: Output exceeded {MAX_RESULT_CHARS:,} characters and was capped. "
        "Please use SQL aggregations (e.g. SUM, COUNT, AVG, GROUP BY) "
        "or narrower filters to query specific subsets.]"
    )


async def fetch_finance_data(query: str) -> str:

    if not query or not query.strip():
        raise ValueError(
            "SQL query cannot be empty"
        )

    match = re.search(BLOCKED_SQL, query, re.IGNORECASE)
    if match:
        raise ValueError(
            f"Blocked SQL operation/construct: {match.group(1).upper()}"
        )

    # T8: Fetch one row more than the cap so we know whether rows were cut off
    cleaned = query.strip().rstrip(';')
    bounded_query = f"SELECT * FROM ({cleaned}) AS q_bounded LIMIT {MAX_ROWS + 1}"

    print("MCP → execute_sql")
    try:
        try:
            text = await _execute_sql(bounded_query)
        except RuntimeError as e:
            if "syntax" not in str(e).lower():
                raise
            # Some statements can't be wrapped in a subquery; run as written
            text = await _execute_sql(cleaned)

    except httpx2.HTTPStatusError as e:
        print(f"[DB Error] HTTP Status Error: {e}")
        raise RuntimeError(
            f"Database connectivity error: HTTP {e.response.status_code}"
        ) from e

    except (httpx2.ConnectError, httpx2.TimeoutException) as e:
        print(f"[DB Error] Network/Connection Error: {e}")
        raise RuntimeError(
            "Database connectivity error: Unable to reach database server."
        ) from e

    except RuntimeError:
        raise

    except Exception as e:
        err_str = str(e)
        print(f"[DB Error] Tool/Execution Error: {err_str}")
        if "TaskGroup" in err_str or "streamable" in err_str:
            raise RuntimeError(
                "Database query execution error: The SQL query encountered an execution issue."
            ) from e
        raise RuntimeError(f"Database query execution error: {err_str}") from e

    rows = _rows_from_mcp_text(text)
    if rows is None:
        # Unrecognized reply shape - pass it through, size-capped
        return _cap_text(text)

    more_rows = len(rows) > MAX_ROWS
    return _format_rows(rows[:MAX_ROWS], more_rows)
