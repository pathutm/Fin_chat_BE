import sys
import time

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

from core.telemetry import (
    tracer,
    request_counter,
    request_duration
)


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


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


pending_confirmations: dict[str, str] = {}


AFFIRMATIVE_RESPONSES = {
    "yes",
    "yep",
    "yeah",
    "yes please",
    "sure",
    "okay",
    "ok",
    "proceed",
    "do it",
    "process it",
    "continue",
    "please proceed",
    "go ahead"
}


NEGATIVE_RESPONSES = {
    "no",
    "nope",
    "not now",
    "don't",
    "cancel",
    "stop",
    "nevermind",
    "no thanks"
}


@app.get("/")
def home():
    return {
        "message": "Finance AI Chatbot is running"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):

    start_time = time.perf_counter()

    with tracer.start_as_current_span(
        "chat.request"
    ) as request_span:

        request_span.set_attribute(
            "conversation.id",
            request.conversation_id
        )

        request_span.set_attribute(
            "user.id",
            request.user_id or "anonymous"
        )

        try:

            user_msg_clean = (
                request.message
                .strip()
                .lower()
            )

            # Step 0: Pending confirmation flow

            if request.conversation_id in pending_confirmations:

                if any(
                    user_msg_clean == aff
                    or user_msg_clean.startswith(
                        aff + " "
                    )
                    for aff in AFFIRMATIVE_RESPONSES
                ):

                    safe_query = pending_confirmations.pop(
                        request.conversation_id
                    )

                    print(
                        "\n[Confirmation Flow] "
                        "User confirmed."
                    )

                    print(
                        "Processing safe query:",
                        safe_query
                    )

                    raw_response, generated_agent = (
                        await handle_chat_logic(
                            safe_query,
                            request.conversation_id,
                            user_name=request.user_name,
                            user_id=request.user_id
                        )
                    )

                    final_safe_response = (
                        await check_output_guardrail(
                            raw_response
                        )
                    )

                    return ChatResponse(
                        response=final_safe_response,
                        agent=generated_agent,
                        deleted=False,
                        requires_confirmation=False
                    )

                elif any(
                    user_msg_clean == neg
                    or user_msg_clean.startswith(
                        neg + " "
                    )
                    for neg in NEGATIVE_RESPONSES
                ):

                    pending_confirmations.pop(
                        request.conversation_id,
                        None
                    )

                    return ChatResponse(
                        response=(
                            "Understood. I won't "
                            "process that request.\n\n"
                            "If you need any other "
                            "assistance, please ask a "
                            "finance-related question."
                        ),
                        agent="Input Guardrail",
                        deleted=False,
                        requires_confirmation=False
                    )

                else:

                    pending_confirmations.pop(
                        request.conversation_id,
                        None
                    )

            # Step 1: Input Guardrail

            with tracer.start_as_current_span(
                "chat.input_guardrail"
            ) as guardrail_span:

                guardrail_span.set_attribute(
                    "agent.name",
                    "Input Guardrail"
                )

                guardrail_span.set_attribute(
                    "model.name",
                    GUARDRAIL_MODEL
                )

                guardrail_res = (
                    await check_input_guardrail(
                        request.message
                    )
                )

                guardrail_span.set_attribute(
                    "guardrail.status",
                    (
                        "allowed"
                        if guardrail_res.is_allowed
                        else "blocked"
                    )
                )

            safe_log_input = (
                "[SENSITIVE CONTENT REMOVED]"
                if guardrail_res.is_deleted
                else request.message
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

                if (
                    guardrail_res.requires_confirmation
                    and guardrail_res.safe_finance_query
                ):

                    pending_confirmations[
                        request.conversation_id
                    ] = guardrail_res.safe_finance_query

                return ChatResponse(
                    response=guardrail_res.response_text,
                    agent="Input Guardrail",
                    deleted=guardrail_res.is_deleted,
                    requires_confirmation=(
                        guardrail_res.requires_confirmation
                    ),
                    safe_finance_query=(
                        guardrail_res.safe_finance_query
                    )
                )

            # Step 2: Safe query → Coordination Agent

            query_to_send = (
                guardrail_res.safe_finance_query
                if guardrail_res.safe_finance_query
                else request.message
            )

            print(
                "\nCoordination Agent called"
            )

            print(
                "User message passed to "
                "Coordination Agent:",
                query_to_send
            )

            with tracer.start_as_current_span(
                "chat.coordination_agent"
            ) as coordination_span:

                coordination_span.set_attribute(
                    "agent.name",
                    "Coordination Agent"
                )

                coordination_span.set_attribute(
                    "model.name",
                    "claude-haiku-4-5-20251001"
                )

                raw_response, generated_agent = (
                    await handle_chat_logic(
                        query_to_send,
                        request.conversation_id,
                        user_name=request.user_name,
                        user_id=request.user_id
                    )
                )

                coordination_span.set_attribute(
                    "agent.generated",
                    generated_agent or "unknown"
                )

            # Step 3: Output Guardrail

            print(
                "\nOutput Guardrail called"
            )

            with tracer.start_as_current_span(
                "chat.output_guardrail"
            ) as output_span:

                output_span.set_attribute(
                    "agent.name",
                    "Output Guardrail"
                )

                output_span.set_attribute(
                    "model.name",
                    GUARDRAIL_MODEL
                )

                final_safe_response = (
                    await check_output_guardrail(
                        raw_response
                    )
                )

                output_span.set_attribute(
                    "status",
                    "success"
                )

            if final_safe_response == raw_response:

                print(
                    "Output Guardrail: PASSED"
                )

            else:

                print(
                    "Output Guardrail: "
                    "SANITIZED / BLOCKED "
                    "(Sensitive content redacted)"
                )

            print(
                "Response sent to UI\n"
            )

            # Keep conversation memory synchronized
            # if output guardrail modified the response.

            if (
                final_safe_response != raw_response
                and request.conversation_id
                in conversation_history
            ):

                if conversation_history[
                    request.conversation_id
                ]:

                    conversation_history[
                        request.conversation_id
                    ][-1]["content"] = (
                        final_safe_response
                    )

            # Output Guardrail process log

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

            # Step 4: Return response

            return ChatResponse(
                response=final_safe_response,
                agent=generated_agent,
                deleted=False,
                requires_confirmation=False
            )

        except Exception as e:

            request_span.record_exception(e)

            request_span.set_attribute(
                "status",
                "error"
            )

            raise

        finally:

            duration_ms = (
                time.perf_counter() - start_time
            ) * 1000

            request_span.set_attribute(
                "duration.ms",
                duration_ms
            )

            request_counter.add(1)

            request_duration.record(
                duration_ms
            )