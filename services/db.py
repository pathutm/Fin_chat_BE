import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from core.config import SUPABASE_PROJECT_REF, SUPABASE_ACCESS_TOKEN

SUPABASE_MCP_URL = (
    "https://mcp.supabase.com/mcp"
    f"?project_ref={SUPABASE_PROJECT_REF}&read_only=true"
)

HEADERS = {
    "Authorization": f"Bearer {SUPABASE_ACCESS_TOKEN}"
}

async def fetch_finance_data(query: str):
    if not query or not query.strip():
        raise ValueError("SQL query cannot be empty")

    blocked_commands = [
        "INSERT", "UPDATE", "DELETE", "DROP", 
        "ALTER", "TRUNCATE", "CREATE"
    ]

    query_upper = query.upper()
    for command in blocked_commands:
        if command in query_upper:
            raise ValueError(f"Blocked SQL operation: {command}")

    print("MCP → execute_sql")

    async with httpx2.AsyncClient(headers=HEADERS) as http_client:
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
                return result

def extract_tool_result(result):
    if hasattr(result, "content"):
        texts = []
        for item in result.content:
            if hasattr(item, "text"):
                texts.append(item.text)
        if texts:
            return "\n".join(texts)
    return str(result)
