import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import re
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

# Add CORS middleware to allow the frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GUARDRAIL_MODEL = "nvidia/nemotron-3.5-content-safety"

# In-memory storage for pending safe finance confirmations (conversation_id -> safe_finance_query)
# NEVER stores raw PII! Stores ONLY the isolated safe finance question.
pending_confirmations: dict[str, str] = {}

AFFIRMATIVE_RESPONSES = {"yes", "yep", "yeah", "yes please", "continue", "proceed", "sure", "ok", "please proceed", "go ahead"}
NEGATIVE_RESPONSES = {"no", "nope", "don't", "cancel", "stop", "nevermind", "no thanks"}


@app.get("/")
def home():
    return {
        "message": "Finance AI Chatbot is running"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    user_msg_clean = request.message.strip().lower()

    # -----------------------------------------------------------------------
    # Step 0: Check for Pending Confirmation Flow (Case 3 & Case 7 follow-up)
    # -----------------------------------------------------------------------
    if request.conversation_id in pending_confirmations:
        if any(user_msg_clean == aff or user_msg_clean.startswith(aff + " ") for aff in AFFIRMATIVE_RESPONSES):
            # Process ONLY the sanitized safe finance question - NEVER the original PII message
            safe_query = pending_confirmations.pop(request.conversation_id)
            print(f"\n[Confirmation Flow] User confirmed. Processing safe query: {safe_query}")

            raw_response, generated_agent = await handle_chat_logic(
                safe_query,
                request.conversation_id,
                user_name=request.user_name,
                user_id=request.user_id
            )

            final_safe_response = await check_output_guardrail(raw_response)

            return ChatResponse(
                response=final_safe_response,
                agent=generated_agent,
                deleted=False,
                requires_confirmation=False
            )

        elif any(user_msg_clean == neg or user_msg_clean.startswith(neg + " ") for neg in NEGATIVE_RESPONSES):
            pending_confirmations.pop(request.conversation_id, None)
            return ChatResponse(
                response="No problem. If you need any other finance-related assistance, please let me know.",
                agent="Input Guardrail",
                deleted=False,
                requires_confirmation=False
            )
        else:
            # User sent a new instruction instead of answering confirmation; clear pending
            pending_confirmations.pop(request.conversation_id, None)

    # -----------------------------------------------------------------------
    # Step 1: Input Guardrail Check
    # -----------------------------------------------------------------------
    guardrail_res = await check_input_guardrail(request.message)

    # Privacy: Avoid logging raw sensitive message if deleted/PII
    safe_log_input = "[SENSITIVE CONTENT REMOVED]" if guardrail_res.is_deleted else request.message

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
        input_data=safe_log_input,
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

    if not guardrail_res.is_allowed:
        # If this request requires confirmation, store ONLY the isolated safe finance query in memory
        if guardrail_res.requires_confirmation and guardrail_res.safe_finance_query:
            pending_confirmations[request.conversation_id] = guardrail_res.safe_finance_query

        return ChatResponse(
            response=guardrail_res.response_text,
            agent="Input Guardrail",
            deleted=guardrail_res.is_deleted,
            requires_confirmation=guardrail_res.requires_confirmation,
            safe_finance_query=guardrail_res.safe_finance_query
        )

    # -----------------------------------------------------------------------
    # Step 2: Forward to Coordination Agent (Safe Content Only)
    # -----------------------------------------------------------------------
    print("\nCoordination Agent")
    print("User message passed to Coordination Agent")

    # If mixed query (Case 4), forward ONLY the isolated finance query, never the non-finance part
    query_to_send = guardrail_res.safe_finance_query if guardrail_res.safe_finance_query else request.message

    raw_response, generated_agent = await handle_chat_logic(
        query_to_send,
        request.conversation_id,
        user_name=request.user_name,
        user_id=request.user_id
    )

    # -----------------------------------------------------------------------
    # Step 3: Output Guardrail (Sanitize & format)
    # -----------------------------------------------------------------------
    final_safe_response = await check_output_guardrail(raw_response)

    # Sync memory if sanitized so future conversation turns do not leak secrets
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

    # -----------------------------------------------------------------------
    # Step 4: Return safe response to Frontend
    # -----------------------------------------------------------------------
    return ChatResponse(
        response=final_safe_response,
        agent=generated_agent,
        deleted=False,
        requires_confirmation=False
    )