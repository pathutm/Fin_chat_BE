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
        result = (
            supabase
            .table("finance_ai_logs")
            .insert(log_data)
            .execute()
        )
        return result
    except Exception as e:
        if "User_ID" in log_data and "column" in str(e) and "User_ID" in str(e):
            del log_data["User_ID"]
            result = (
                supabase
                .table("finance_ai_logs")
                .insert(log_data)
                .execute()
            )
            return result
        raise e

async def create_process_log(
    user_name: str | None,
    user_id: str | None,
    session_id: str,
    conversation_id: str | None,
    agent_id: str | None,
    agent_name: str | None,
    env_id: str | None,
    tool_id: str | None,
    tool_req: str | None,
    tool_response: str | None,
    parent_agent: str | None,
    child_agent: str | None,
    input_data: str | None,
    output_data: str | None,
    context_window: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    model_used: str | None = None
):
    process_data = {
        "User_Name": user_name,
        "User_ID": user_id,
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
        "Model_Used": model_used,
        "Input_Tokens": input_tokens,
        "Output_Tokens": output_tokens
    }

    response = (
        supabase
        .table("finance_ai_process_logs")
        .insert(process_data)
        .execute()
    )

    return response