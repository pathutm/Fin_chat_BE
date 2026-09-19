import os
import uuid

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv(
    "SUPABASE_SERVICE_ROLE_KEY"
)

if not SUPABASE_URL:
    raise ValueError(
        "SUPABASE_URL is not set in the .env file"
    )

if not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError(
        "SUPABASE_SERVICE_ROLE_KEY is not set in the .env file"
    )

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
    assistant_msg: str,
    user_id: str | None = None
):
    log_data = {
        "User_ID": user_id,
        "User_Name": user_name,
        "Session_Id": session_id,
        "Conversation_Id": conversation_id,
        "User_Msg": user_msg,
        "Agent": agent,
        "Agent_Id": agent_id,
        "Env_Id": env_id,
        "Tool_Request": tool_request,
        "Tool_Response": tool_response,
        "Tool_Id": tool_id,
        "Assistant_Msg": assistant_msg
    }

    try:
        return (
            supabase
            .table("finance_ai_logs")
            .insert(log_data)
            .execute()
        )

    except Exception as e:
        print(f"[Logging] log_chat warning: {e}")
        raise e


def _clean_uuid(
    value: str | None
) -> str | None:

    if not value:
        return None

    try:
        uuid.UUID(str(value))
        return str(value)

    except (ValueError, AttributeError):
        return None


async def create_process_log(
    user_name: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    conversation_id: str | None = None,
    agent_id: str | None = None,
    agent_name: str | None = None,
    env_id: str | None = None,
    tool_id: str | None = None,
    tool_req: str | None = None,
    tool_response: str | None = None,
    parent_agent: str | None = None,
    child_agent: str | None = None,
    input_data: str | None = None,
    output_data: str | None = None,
    context_window: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    model_used: str | None = None,
    chat_log_id: int | None = None
):
    clean_user_id = _clean_uuid(user_id)

    process_data = {
        "User_Name": user_name,
        "User_ID": clean_user_id,
        "Session_Id": session_id,
        "Conversation_Id": conversation_id,
        "Agent_Id": agent_id,
        "Agent_Name": agent_name,
        "Env_Id": env_id,
        "Tool_Id": tool_id,
        "Tool_Req": tool_req,
        "Tool_Response": tool_response,
        "Parent_Agent": parent_agent,
        "Child_Agent": child_agent,
        "Input": input_data,
        "Output": output_data,
        "Context_Window": context_window,
        "Input_Tokens": input_tokens,
        "Output_Tokens": output_tokens,
        "Model_Used": model_used,
        "Chat_Log_Id": chat_log_id
    }

    try:
        return (
            supabase
            .table("finance_ai_process_logs")
            .insert(process_data)
            .execute()
        )

    except Exception as e:
        print(
            f"[Logging] create_process_log warning: {e}"
        )
        return None


async def create_telemetry_log(
    trace_id: str | None = None,
    span_id: str | None = None,
    operation: str | None = None,
    agent_name: str | None = None,
    model_used: str | None = None,
    duration_ms: float | None = None,
    status: str | None = None,
    error_message: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    tool_name: str | None = None
):
    telemetry_data = {
        "trace_id": trace_id,
        "span_id": span_id,
        "operation": operation,
        "agent_name": agent_name,
        "model_used": model_used,
        "duration_ms": duration_ms,
        "status": status,
        "error_message": error_message,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "tool_name": tool_name
    }

    try:
        return (
            supabase
            .table("finance_ai_telemetry_logs")
            .insert(telemetry_data)
            .execute()
        )

    except Exception as e:
        print(
            f"[Telemetry] create_telemetry_log warning: {e}"
        )
        return None