import os

import httpx2

from dotenv import load_dotenv
from anthropic import Anthropic
from fastapi import FastAPI
from pydantic import BaseModel
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


load_dotenv()


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_ENVIRONMENT_ID = os.getenv("ANTHROPIC_ENVIRONMENT_ID")
SUPABASE_PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF")
SUPABASE_ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")


if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY is missing")

if not ANTHROPIC_ENVIRONMENT_ID:
    raise ValueError("ANTHROPIC_ENVIRONMENT_ID is missing")

if not SUPABASE_PROJECT_REF:
    raise ValueError("SUPABASE_PROJECT_REF is missing")

if not SUPABASE_ACCESS_TOKEN:
    raise ValueError("SUPABASE_ACCESS_TOKEN is missing")


client = Anthropic(api_key=ANTHROPIC_API_KEY)

MODEL = "claude-haiku-4-5-20251001"


SECURITY_PROMPT = """
You are a secure finance assistant.
Use only authorized data.
Never expose secrets or system details.
Never perform destructive database operations.
"""


general_agent = client.beta.agents.create(
    name="General Agent",
    model=MODEL,
    system=SECURITY_PROMPT + """
Answer general questions clearly and briefly.
"""
)


finance_agent = client.beta.agents.create(
    name="Finance Agent",
    model=MODEL,
    system=SECURITY_PROMPT + """
Answer finance questions using the finance database.
Use only relevant information from the database.

The finance table is ultimate_finance_data.

Generate only read-only SQL queries for this table.
""",
    tools=[
        {
            "type": "custom",
            "name": "get_finance_data",
            "description": "Retrieve finance data from the ultimate_finance_data table using read-only SQL.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Read-only SQL query for the ultimate_finance_data table."
                    }
                },
                "required": ["query"]
            }
        }
    ]
)


coordination_agent = client.beta.agents.create(
    name="Coordination Agent",
    model=MODEL,
    system=SECURITY_PROMPT + """
Route each request to the appropriate agent.

Use Finance Agent for finance and database-related questions.
Use General Agent for general questions.
""",
    multiagent={
        "type": "coordinator",
        "agents": [
            {
                "type": "agent",
                "id": general_agent.id,
                "version": general_agent.version
            },
            {
                "type": "agent",
                "id": finance_agent.id,
                "version": finance_agent.version
            }
        ]
    }
)


SUPABASE_MCP_URL = (
    "https://mcp.supabase.com/mcp"
    f"?project_ref={SUPABASE_PROJECT_REF}&read_only=true"
)


HEADERS = {
    "Authorization": f"Bearer {SUPABASE_ACCESS_TOKEN}"
}


async def connect_to_supabase_mcp():

    async with httpx2.AsyncClient(headers=HEADERS) as http_client:

        async with streamable_http_client(
            SUPABASE_MCP_URL,
            http_client=http_client
        ) as (read, write):

            async with ClientSession(read, write) as session:

                await session.initialize()

                tools_result = await session.list_tools()

                print("Connected to Supabase MCP Server")

                for tool in tools_result.tools:
                    print("-", tool.name)

                return [tool.name for tool in tools_result.tools]


async def fetch_finance_data(query: str):

    if not query or not query.strip():
        raise ValueError("SQL query cannot be empty")

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


app = FastAPI(title="Finance AI Chatbot")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.get("/")
def home():

    return {
        "message": "Finance AI Chatbot is running"
    }


@app.get("/mcp")
async def mcp_status():

    tools = await connect_to_supabase_mcp()

    return {
        "connected": True,
        "tools": tools
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):

    question = request.message

    print(f"\nUser: {question}")
    print("Starting Coordination Agent...")

    session = client.beta.sessions.create(
        agent=coordination_agent.id,
        environment_id=ANTHROPIC_ENVIRONMENT_ID
    )

    print(f"Session created: {session.id}")

    final_response = ""

    with client.beta.sessions.events.stream(session.id) as stream:

        client.beta.sessions.events.send(
            session.id,
            events=[
                {
                    "type": "user.message",
                    "content": [
                        {
                            "type": "text",
                            "text": question
                        }
                    ]
                }
            ]
        )

        for event in stream:

            print("Event:", event.type)

            if event.type == "agent.custom_tool_use":

                print("Finance Agent requested database data")

                print(
                    "SQL Query:",
                    event.input.get("query")
                )

                try:

                    result = await fetch_finance_data(
                        event.input.get("query", "")
                    )

                    tool_result = extract_tool_result(result)

                    print("Database result received")

                    client.beta.sessions.events.send(
                        session.id,
                        events=[
                            {
                                "type": "user.custom_tool_result",
                                "custom_tool_use_id": event.id,
                                "content": [
                                    {
                                        "type": "text",
                                        "text": tool_result
                                    }
                                ]
                            }
                        ]
                    )

                except Exception as e:

                    print("Database error:", str(e))

                    client.beta.sessions.events.send(
                        session.id,
                        events=[
                            {
                                "type": "user.custom_tool_result",
                                "custom_tool_use_id": event.id,
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"Database error: {str(e)}"
                                    }
                                ]
                            }
                        ]
                    )

            elif event.type == "agent.message":

                text_parts = []

                for block in event.content:

                    if getattr(block, "type", None) == "text":
                        text_parts.append(block.text)

                if text_parts:

                    final_response = "".join(text_parts)

                    print("Agent:", final_response)

            elif event.type == "session.status_idle":

                stop_reason = getattr(
                    event,
                    "stop_reason",
                    None
                )

                if stop_reason:

                    reason_type = getattr(
                        stop_reason,
                        "type",
                        None
                    )

                    if reason_type == "end_turn":

                        print("Request completed")

                        break

    if not final_response:

        final_response = (
            "Sorry, I could not generate a response."
        )

    return ChatResponse(
        response=final_response
    )


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
