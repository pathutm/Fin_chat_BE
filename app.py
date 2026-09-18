from fastapi import FastAPI

from schemas.chat import ChatRequest, ChatResponse
from services.chat import handle_chat_logic
from services.memory import conversation_history
from services.logging import create_process_log
from guardrails.actions import (
    check_input_guardrail,
    check_output_guardrail
)

app = FastAPI(title="Finance AI Chatbot")


@app.get("/")
def home():
    return {
        "message": "Finance AI Chatbot is running"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    is_allowed, input_fallback = await check_input_guardrail(
        request.message
    )

    # Log Input Guardrail process
    await create_process_log(
        user_name=request.user_name,
        user_id=request.user_id,
        session_id="guardrail",
        conversation_id=request.conversation_id,
        agent_id=None,
        agent_name="Input Guardrail",
        env_id=None,
        tool_id=None,
        tool_req=None,
        tool_response=None,
        process_initiation="User",
        process_destination="Input Guardrail",
        input_data=request.message,
        output_data=(
            "Input Guardrail ALLOWED"
            if is_allowed
            else "Input Guardrail BLOCKED"
        ),
        context_window=None,
        token_consumed=None,
        model_used="openai/gpt-oss-20b"
    )

    if not is_allowed:
        return ChatResponse(
            response=input_fallback,
            agent="Input Guardrail"
        )

    print("=" * 50)
    print("[COORDINATION AGENT]")
    print("User message passed to Coordination Agent")
    print("=" * 50)

    raw_response, generated_agent = await handle_chat_logic(
        request.message,
        request.conversation_id,
        user_name=request.user_name,
        user_id=request.user_id
    )

    final_safe_response = await check_output_guardrail(
        raw_response
    )

    # Log Output Guardrail process
    await create_process_log(
        user_name=request.user_name,
        user_id=request.user_id,
        session_id="guardrail",
        conversation_id=request.conversation_id,
        agent_id=None,
        agent_name="Output Guardrail",
        env_id=None,
        tool_id=None,
        tool_req=None,
        tool_response=None,
        process_initiation="Coordination Agent",
        process_destination="Output Guardrail",
        input_data=raw_response,
        output_data=(
            "Output Guardrail ALLOWED"
            if final_safe_response == raw_response
            else "Output Guardrail FORMATTED"
        ),
        context_window=None,
        token_consumed=None,
        model_used="openai/gpt-oss-20b"
    )

    if (
        final_safe_response != raw_response
        and request.conversation_id in conversation_history
    ):
        if conversation_history[request.conversation_id]:
            conversation_history[
                request.conversation_id
            ][-1]["content"] = final_safe_response

    await create_process_log(
        user_name=request.user_name,
        user_id=request.user_id,
        session_id="guardrail",
        conversation_id=request.conversation_id,
        agent_id=None,
        agent_name="Output Guardrail",
        env_id=None,
        tool_id=None,
        tool_req=None,
        tool_response=None,
        process_initiation="Output Guardrail",
        process_destination="User",
        input_data=raw_response,
        output_data=final_safe_response,
        context_window=None,
        token_consumed=None,
        model_used="openai/gpt-oss-20b"
    )

    return ChatResponse(
        response=final_safe_response,
        agent=generated_agent
    )