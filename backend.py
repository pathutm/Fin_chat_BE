import os
import asyncio

from dotenv import load_dotenv
from anthropic import Anthropic
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


load_dotenv()


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SUPABASE_PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF")
SUPABASE_ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")


if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY is missing")

if not SUPABASE_PROJECT_REF:
    raise ValueError("SUPABASE_PROJECT_REF is missing")

if not SUPABASE_ACCESS_TOKEN:
    raise ValueError("SUPABASE_ACCESS_TOKEN is missing")


client = Anthropic(
    api_key=ANTHROPIC_API_KEY
)


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
Answer finance questions using the authorized finance database.

When the user asks for employee, salary, company, asset,
liability, working capital, reporting, or financial ratio
information, use the get_finance_data tool.

Do not refuse authorized database information because it is
financial information.

Use only the data returned by the tool.
""",
    tools=[
        {
            "type": "custom",
            "name": "get_finance_data",
            "description": "Retrieve authorized finance data from Supabase using read-only SQL.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A read-only SQL query."
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
You are the main coordination agent.

Route general questions to General Agent.

Route finance and database questions to Finance Agent.

Return the appropriate agent's final answer to the user.
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

    async with streamablehttp_client(
        SUPABASE_MCP_URL,
        headers=HEADERS,
        terminate_on_close=False
    ) as (read, write, _):

        async with ClientSession(read, write) as session:

            await session.initialize()

            tools_result = await session.list_tools()

            print("Connected to Supabase MCP Server")

            for tool in tools_result.tools:
                print("-", tool.name)

            return [
                tool.name
                for tool in tools_result.tools
            ]


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


    async with streamablehttp_client(
        SUPABASE_MCP_URL,
        headers=HEADERS,
        terminate_on_close=False
    ) as (read, write, _):

        async with ClientSession(read, write) as session:

            await session.initialize()

            result = await session.call_tool(
                "execute_sql",
                {
                    "query": query
                }
            )


            if hasattr(result, "content"):

                texts = []

                for item in result.content:

                    if hasattr(item, "text"):
                        texts.append(item.text)

                if texts:
                    return "\n".join(texts)


            return str(result)


environment = client.beta.environments.create(
    name="finchat-env"
)


async def run_agent(question: str):

    session = client.beta.sessions.create(
        agent=coordination_agent.id,
        environment_id=environment.id
    )


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


    processed_events = set()


    for _ in range(60):

        await asyncio.sleep(1)


        events_page = client.beta.sessions.events.list(
            session.id
        )


        for event in events_page.data:

            if event.id in processed_events:
                continue


            processed_events.add(event.id)


            if event.type == "agent.custom_tool_use":

                if event.name == "get_finance_data":

                    query = event.input.get(
                        "query",
                        ""
                    )


                    try:

                        result = await fetch_finance_data(
                            query
                        )


                        client.beta.sessions.events.send(
                            session.id,
                            events=[
                                {
                                    "type": "user.custom_tool_result",
                                    "custom_tool_use_id": event.id,
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": result
                                        }
                                    ]
                                }
                            ]
                        )


                    except Exception as error:

                        client.beta.sessions.events.send(
                            session.id,
                            events=[
                                {
                                    "type": "user.custom_tool_result",
                                    "custom_tool_use_id": event.id,
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": str(error)
                                        }
                                    ]
                                }
                            ]
                        )


            elif event.type == "agent.message":

                response_text = ""


                for content in event.content:

                    if hasattr(content, "text"):
                        response_text += content.text


                if response_text.strip():
                    return response_text


    return "The agent did not return a response."


app = FastAPI(
    title="Finance AI Chatbot"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.post(
    "/chat",
    response_model=ChatResponse
)
async def chat_endpoint(
    request: ChatRequest
):

    question = request.message.strip()


    if not question:

        return ChatResponse(
            response="Please enter a question."
        )


    result = await run_agent(
        question
    )


    return ChatResponse(
        response=result
    )


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )