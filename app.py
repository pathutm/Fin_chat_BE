from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from schemas.chat import ChatRequest, ChatResponse
from services.chat import handle_chat_logic
from services.memory import conversation_history
from services.logging import create_process_log

from guardrails.actions import (
    check_input_guardrail,
    check_output_guardrail
)

app = FastAPI(title="Finance AI Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GUARDRAIL_MODEL = "nvidia/nemotron-3.5-content-safety"


@app.get("/")
def home():
    return {
        "message": "Finance AI Chatbot is running"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):

    # Step 1: Input Guardrail
    print("\nInput Guardrail called")
    print(f"User message: {request.message}")

    guardrail_res = await check_input_guardrail(
        request.message,
        conversation_id=request.conversation_id
    )

    print(
        "Input Guardrail:",
        "PASSED" if guardrail_res.is_allowed else "BLOCKED"
    )

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
        parent_agent="User",
        child_agent="Input Guardrail",
        input_data=request.message,
        output_data=(
            "Input Guardrail ALLOWED"
            if guardrail_res.is_allowed
            else "Input Guardrail BLOCKED"
        ),
        context_window=None,
        input_tokens=None,
        output_tokens=None,
        model_used=GUARDRAIL_MODEL
    )

    # If input is blocked
    if not guardrail_res.is_allowed:

        return ChatResponse(
            response=guardrail_res.response_text,
            agent="Input Guardrail",
            deleted=guardrail_res.is_deleted,
            requires_confirmation=guardrail_res.requires_confirmation,
            safe_finance_query=guardrail_res.safe_finance_query
        )

    # Use safe query if guardrail modified the input
    query_to_send = (
        guardrail_res.safe_finance_query
        if guardrail_res.safe_finance_query
        else request.message
    )

    # Step 2: Coordination Agent
    print("\nCoordination Agent")
    print(
        f"User message passed to Coordination Agent: "
        f"'{query_to_send}'"
    )

    raw_response, generated_agent = await handle_chat_logic(
        query_to_send,
        request.conversation_id,
        user_name=request.user_name,
        user_id=request.user_id
    )

    # Step 3: Output Guardrail
    print("\nOutput Guardrail called")

    final_safe_response = await check_output_guardrail(
        raw_response
    )

    print(
        "Output Guardrail:",
        "PASSED"
        if final_safe_response == raw_response
        else "SANITIZED"
    )

    # Sync memory if response was sanitized
    if (
        final_safe_response != raw_response
        and request.conversation_id in conversation_history
    ):
        if conversation_history[request.conversation_id]:
            conversation_history[
                request.conversation_id
            ][-1]["content"] = final_safe_response

    # Log Output Guardrail
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
        parent_agent=generated_agent,
        child_agent="Output Guardrail",
        input_data=raw_response,
        output_data=(
            "Output Guardrail ALLOWED"
            if final_safe_response == raw_response
            else "Output Guardrail SANITIZED"
        ),
        context_window=None,
        input_tokens=None,
        output_tokens=None,
        model_used=GUARDRAIL_MODEL
    )

    # Step 4: Return response to Angular
    return ChatResponse(
        response=final_safe_response,
        agent=generated_agent
    )