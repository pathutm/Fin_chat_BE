import httpx

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from core.config import (
    SUPABASE_PROJECT_REF,
    SUPABASE_ACCESS_TOKEN
)


SUPABASE_MCP_URL = (
    "https://mcp.supabase.com/mcp"
    f"?project_ref={SUPABASE_PROJECT_REF}&read_only=true"
)


HEADERS = {
    "Authorization": f"Bearer {SUPABASE_ACCESS_TOKEN}"
}


async def fetch_finance_data(query: str):

    if not query or not query.strip():
        raise ValueError(
            "SQL query cannot be empty"
        )

    blocked_commands = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "CREATE"
    ]

    query_upper = query.upper()

    for command in blocked_commands:

        if command in query_upper:
            raise ValueError(
                f"Blocked SQL operation: {command}"
            )

    print("MCP → execute_sql")

    try:

        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=30.0
        ) as http_client:

            async with streamable_http_client(
                SUPABASE_MCP_URL,
                http_client=http_client
            ) as (read, write):

                async with ClientSession(
                    read,
                    write
                ) as session:

                    await session.initialize()

                    result = await session.call_tool(
                        "execute_sql",
                        {
                            "query": query
                        }
                    )

                    return result

    except httpx.HTTPStatusError as e:

        print(
            f"[DB Error] HTTP Status Error: {e}"
        )

        return (
            "Database connectivity error: "
            f"HTTP {e.response.status_code}"
        )

    except (
        httpx.ConnectError,
        httpx.TimeoutException
    ) as e:

        print(
            f"[DB Error] Network/Connection Error: {e}"
        )

        return (
            "Database connectivity error: "
            "Unable to reach database server. "
            "Please try again later."
        )

    except Exception as e:

        err_str = str(e)

        print(
            f"[DB Error] Tool/Execution Error: "
            f"{err_str}"
        )

        if (
            "TaskGroup" in err_str
            or "streamable" in err_str
        ):

            return (
                "Database query execution error: "
                "The SQL query encountered an execution issue. "
                "Please verify table and identifier parameters."
            )

        return (
            "Database query execution error: "
            f"{err_str}"
        )


def extract_tool_result(result):

    if hasattr(result, "isError") and result.isError:

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

            return combined

    return str(result)