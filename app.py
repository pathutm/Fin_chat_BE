from fastapi import FastAPI

from schemas.chat import ChatRequest, ChatResponse
from services.chat import handle_chat_logic
from services.memory import conversation_history
from guardrails.actions import check_input_guardrail, check_output_guardrail

app = FastAPI(title="Finance AI Chatbot")


@app.get("/")
def home():
    return {
        "message": "Finance AI Chatbot is running"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    # -----------------------------------------------------------------------
    # Step 1: Input Guardrail (Evaluated BEFORE Coordination Agent)
    # -----------------------------------------------------------------------
    is_allowed, input_fallback = await check_input_guardrail(request.message)
    if not is_allowed:
        return ChatResponse(
            response=input_fallback,
            agent="Input Guardrail"
        )

    # -----------------------------------------------------------------------
    # Step 2: Existing Coordination Agent Flow
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # Step 3: Output Guardrail (Sanitize/redact sensitive disclosures)
    # -----------------------------------------------------------------------
    final_safe_response = await check_output_guardrail(raw_response)

    # Sync memory if sanitized so future conversation turns do not leak secrets
    if final_safe_response != raw_response and request.conversation_id in conversation_history:
        if conversation_history[request.conversation_id]:
            conversation_history[request.conversation_id][-1]["content"] = final_safe_response

    # -----------------------------------------------------------------------
    # Step 4: Return safe response to Angular
    # -----------------------------------------------------------------------
    return ChatResponse(
        response=final_safe_response,
        agent=generated_agent
    )