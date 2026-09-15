import os

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is not set in the .env file")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_SERVICE_ROLE_KEY is not set in the .env file")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY
)


async def log_chat(
    user_name: str | None,
    session_id: str | None,
    conversation_id: str,
    user_msg: str,
    agent: str | None,
    agent_id: str | None,
    env_id: str | None,
    tool_request: str | None,
    tool_response: str | None,
    tool_id: str | None,
    assistant_msg: str
):
    log_data = {
        "user_name": user_name,
        "session_id": session_id,
        "conversation_id": conversation_id,
        "user_msg": user_msg,
        "agent": agent,
        "agent_id": agent_id,
        "env_id": env_id,
        "tool_request": tool_request,
        "tool_response": tool_response,
        "tool_id": tool_id,
        "assistant_msg": assistant_msg
    }

    result = (
        supabase
        .table("finance_ai_logs")
        .insert(log_data)
        .execute()
    )

    return result