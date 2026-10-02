import re
import os
import asyncpg

from core.config import SUPABASE_PROJECT_REF

# ---------------------------------------------------------------------------
# A6: Persistent asyncpg connection pool with lifecycle management
# S1: Read-only enforcement + 10s statement timeout
# ---------------------------------------------------------------------------

# Database URL — constructed from Supabase project ref or explicit env var
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://postgres.{SUPABASE_PROJECT_REF}:"
    f"{os.getenv('SUPABASE_DB_PASSWORD', '')}@"
    f"aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
)

_pool: asyncpg.Pool | None = None
_use_direct_db = bool(os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_PASSWORD"))


async def get_db_pool() -> asyncpg.Pool:
    """Get or create the asyncpg connection pool (A6)."""
    global _pool
    if _pool is not None and not _pool._closed:
        return _pool

    _pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=10.0,  # S1: 10s statement timeout
        server_settings={
            "default_transaction_read_only": "on",  # S1: read-only enforcement
            "statement_timeout": "10000",            # S1: 10s timeout at server level
        }
    )
    print("[A6/S1] asyncpg connection pool created (read-only, 10s timeout)")
    return _pool


async def close_db_pool():
    """Shutdown the connection pool gracefully."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        print("[A6] asyncpg connection pool closed")


async def _fetch_via_pool(query: str) -> str:
    """Execute read-only SQL via asyncpg pool and return formatted results."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        # Execute within a read-only transaction (S1 double enforcement)
        async with conn.transaction(readonly=True):
            rows = await conn.fetch(query)

        if not rows:
            return "No rows returned."

        # Format as readable text (matching MCP output format)
        columns = list(rows[0].keys())
        result_lines = [" | ".join(columns)]
        result_lines.append("-" * len(result_lines[0]))

        for row in rows:
            result_lines.append(
                " | ".join(str(row[col]) for col in columns)
            )

        combined = "\n".join(result_lines)

        # Cap character length to prevent massive token bloat (T8)
        if len(combined) > 8000:
            combined = (
                combined[:8000]
                + "\n\n[Note: Output exceeded 8,000 characters and was capped. "
                "Please use SQL aggregations (e.g. SUM, COUNT, AVG, GROUP BY) "
                "or narrower filters to query specific subsets.]"
            )

        return combined


async def fetch_finance_data(query: str):

    if not query or not query.strip():
        raise ValueError(
            "SQL query cannot be empty"
        )

    blocked_pattern = r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|COPY|GRANT|REVOKE|SET|EXECUTE|pg_sleep)\b'
    match = re.search(blocked_pattern, query, re.IGNORECASE)
    if match:
        raise ValueError(
            f"Blocked SQL operation/construct: {match.group(1).upper()}"
        )

    # Safe bounded query wrapping (T8)
    exec_query = query
    if not re.search(r'\bLIMIT\b', query, re.IGNORECASE):
        cleaned = query.strip().rstrip(';')
        exec_query = f"SELECT * FROM ({cleaned}) AS q_bounded LIMIT 101"

    # A6: Execute directly via persistent asyncpg connection pool (Read-only + 10s statement timeout)
    print("DB → asyncpg pool (direct read-only execution)")
    try:
        result_text = await _fetch_via_pool(exec_query)
        return _wrap_text_result(result_text)
    except asyncpg.PostgresSyntaxError:
        # Fall back to raw query within pool if bounded subquery encountered a dialect limitation
        result_text = await _fetch_via_pool(query)
        return _wrap_text_result(result_text)
    except Exception as e:
        err_str = str(e)
        print(f"[DB Error] asyncpg query error: {err_str}")
        raise RuntimeError(
            f"Database query execution error: {err_str}"
        ) from e


class _TextResult:
    """Wrapper to make asyncpg text results compatible with extract_tool_result."""
    def __init__(self, text):
        self.content = [type('TextItem', (), {'text': text})()]
        self.isError = False


def _wrap_text_result(text: str):
    """Wrap a plain text result into an object compatible with extract_tool_result."""
    return _TextResult(text)


def extract_tool_result(result):

    if hasattr(result, "isError") and result.isError:

        texts = []

        if hasattr(result, "content"):

            for item in result.content:

                if hasattr(item, "text"):

                    texts.append(
                        item.text
                    )

        if texts:

            return "\n".join(texts)

        return (
            "Database query error: "
            f"{str(result)}"
        )

    if hasattr(result, "content"):

        texts = []

        for item in result.content:

            if hasattr(item, "text"):

                texts.append(
                    item.text
                )

        if texts:

            combined = "\n".join(
                texts
            )

            if (
                "TaskGroup" in combined
                or "sub-exception" in combined
            ):

                return (
                    "Database query execution error: "
                    "The SQL query encountered an execution error. "
                    "Please ensure table names and identifier "
                    "formats are valid."
                )

            # Cap character length to prevent massive token bloat (T8)
            if len(combined) > 8000:
                combined = (
                    combined[:8000]
                    + "\n\n[Note: Output exceeded 8,000 characters and was capped. Please use SQL aggregations (e.g. SUM, COUNT, AVG, GROUP BY) or narrower filters to query specific subsets.]"
                )

            return combined

    res_str = str(result)
    if len(res_str) > 8000:
        res_str = (
            res_str[:8000]
            + "\n\n[Note: Output capped at 8,000 characters. Please refine query with aggregation or narrower filters.]"
        )
    return res_str