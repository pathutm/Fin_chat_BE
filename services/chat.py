from core.config import ANTHROPIC_ENVIRONMENT_ID
import os
import re
import json
from datetime import datetime, timedelta, timezone

import asyncio

import anthropic

from agents.client import async_client

from agents.setup import (
    coordination_agent,
    finance_agent,
    AGENTS_BY_NAME,
    MODEL
)

from services.memory import (
    last_finance_dataset,
    persist_session,
    load_session,
    get_bounded_conversation_context,
    is_visualization_followup,
    remember_turn
)

from services.db import fetch_finance_data

from services.logging import (
    log_chat,
    create_process_log
)

from agents.coordination_rules import (
    coordination_rule,
    convert_tool_result_currency,
    is_monetary_column
)

from services.validation import (
    validate_sql_query,
    validate_tool_data,
    validate_and_sanitize_response
)

from guardrails.actions import is_standalone_greeting

from core.telemetry import (
    tracer,
    input_token_counter,
    output_token_counter
)


MODEL_USED = MODEL
COORDINATOR_NAME = "Coordination Agent"
FINANCE_NAME = "Finance Agent"

# T12: The coordinator answers with exactly this word when a sub-agent's report
# already answers the question, so the answer is generated once, not twice.
RELAY_MARKER = "RELAY"

# A4: Maximum stream reconnect attempts
MAX_STREAM_RETRIES = 3

# T9: Maximum database tool calls per question
MAX_DB_CALLS = 3

# T11: Platform-enforced spend cap per Managed Agents session, in US cents
# (minor units, integer string). Default $1.00.
SESSION_BUDGET_CENTS = os.getenv("SESSION_BUDGET_CENTS", "100")

class SessionUnavailable(Exception):
    """The persisted session can no longer accept a new user message."""


# T7: Start a fresh session (seeded with the last 3 messages) when the
# conversation was idle longer than this. 0 disables the rollover.
SESSION_IDLE_ROLLOVER_MINUTES = float(os.getenv("SESSION_IDLE_ROLLOVER_MINUTES", "5"))

# Background usage-logging tasks still running (kept so they aren't garbage-collected)
_background_tasks: set[asyncio.Task] = set()

BUDGET_REACHED_MESSAGE = (
    "This question reached the spending limit before it finished. "
    "Please ask a more specific question."
)


async def handle_chat_logic(
    question: str,
    conversation_id: str,
    user_name: str | None = None,
    user_id: str | None = None
):

    # ---------------------------------------------------------
    # T6: STANDALONE GREETINGS (0 LLM Calls)
    # ---------------------------------------------------------
    if is_standalone_greeting(question):
        greeting_response = "Hello! How can I assist you with your finance-related questions today?"
        remember_turn(conversation_id, question, greeting_response)
        await log_chat(
            user_name=user_name,
            user_id=user_id,
            session_id=None,
            conversation_id=conversation_id,
            user_msg=question,
            agent="Greeting Handler",
            agent_id=None,
            env_id=ANTHROPIC_ENVIRONMENT_ID,
            tool_request=None,
            tool_response=None,
            tool_id=None,
            assistant_msg=greeting_response
        )
        return greeting_response, "Greeting Handler"

    # ---------------------------------------------------------
    # T10: REUSE DATASET FOR VISUALIZATION (0 LLM Calls)
    # ---------------------------------------------------------
    # Also restores a cached dataset persisted before a server restart
    persisted_session = await load_session(conversation_id)

    if is_visualization_followup(question, conversation_id):
        cached_data = last_finance_dataset[conversation_id]
        tool_result = cached_data.get("tool_result", "")
        viz_response = (
            "Here is the chart visualization for the previously retrieved financial dataset:\n\n"
            f"{_dataset_as_markdown_table(tool_result)}\n\n"
            "The visualization displays the verified dataset from your query."
        )
        remember_turn(conversation_id, question, viz_response)
        await log_chat(
            user_name=user_name,
            user_id=user_id,
            session_id=None,
            conversation_id=conversation_id,
            user_msg=question,
            agent="Visualization Handler",
            agent_id=None,
            env_id=ANTHROPIC_ENVIRONMENT_ID,
            tool_request=None,
            tool_response=tool_result,
            tool_id=None,
            assistant_msg=viz_response
        )
        return viz_response, "Visualization Handler"

    if not coordination_agent.id:
        return (
            "The finance assistant is not configured yet. Please contact the administrator.",
            COORDINATOR_NAME
        )

    print(f"\n{COORDINATOR_NAME} session")
    print("User:", question)
    print("Conversation ID:", conversation_id)

    # ---------------------------------------------------------
    # A5 & T7: One Managed Agents session per conversation.
    # A reused session already holds the conversation (with platform prompt
    # caching and compaction), so only the new question is sent.
    # ---------------------------------------------------------
    session_id = persisted_session.get("session_id") if persisted_session else None

    if session_id and _cache_expired(persisted_session):
        # The platform's prompt cache lasts ~5 minutes. Resuming a long session
        # after that re-writes its whole history to cache; a fresh session seeded
        # with the recent context (T7) only writes the system prompt.
        print(f"[T7] Session {session_id} idle past the cache window; starting a fresh one")
        session_id = None

    turn = None
    if session_id:
        print("Session reused:", session_id)
        try:
            turn = await _run_agent_turn(
                session_id, question, question, conversation_id, user_name, user_id
            )
        except SessionUnavailable as e:
            print(f"[A5] Session {session_id} can't take new messages ({e}); starting a new one")
            session_id = None

    if not session_id:
        session_id = await _create_session(conversation_id)
        recent_ctx = get_bounded_conversation_context(conversation_id, max_messages=3)
        agent_question = f"{recent_ctx}\nCurrent User Question:\n{question}" if recent_ctx else question
        turn = await _run_agent_turn(
            session_id, agent_question, question, conversation_id, user_name, user_id
        )

    final_response = turn["final_response"]
    coordinator_text = final_response.strip()
    if coordinator_text.strip(".").upper() == RELAY_MARKER:
        relay_outcome = "RELAY used"
    elif not coordinator_text and turn["last_report"]:
        relay_outcome = "No coordinator text, report shown"
    elif turn["last_report"]:
        relay_outcome = "Coordinator rewrote report"
    else:
        relay_outcome = "Coordinator answered directly"

    if relay_outcome in ("RELAY used", "No coordinator text, report shown"):
        # T12: the coordinator relayed a sub-agent's report as the answer
        final_response = turn["last_report"]
    final_response = final_response or "Sorry, I could not generate a response."
    if turn["participating_agents"]:
        print("Agents participated:", ", ".join(turn["participating_agents"]))
    print("Final answer:", relay_outcome)

    # T12: One row per question showing how the final answer was produced, to
    # measure how often the relay saves the coordinator's rewrite:
    #   select "Output", count(*) from finance_ai_process_logs
    #   where "Child_Agent" = 'Final Answer' group by "Output";
    await create_process_log(
        user_name=user_name,
        user_id=user_id,
        session_id=session_id,
        conversation_id=conversation_id,
        agent_id=coordination_agent.id,
        agent_name=COORDINATOR_NAME,
        env_id=ANTHROPIC_ENVIRONMENT_ID,
        tool_id=None,
        tool_req=None,
        tool_response=None,
        parent_agent=COORDINATOR_NAME,
        child_agent="Final Answer",
        input_data=question,
        output_data=relay_outcome,
        context_window=None,
        input_tokens=None,
        output_tokens=None,
        model_used=MODEL_USED
    )

    # S4 & Issue 28: Conditional deterministic currency conversion and response sanitization
    coordination_process = coordination_rule(question, result=final_response)
    final_response = coordination_process.get("converted_result", final_response)
    final_response = validate_and_sanitize_response(final_response)

    remember_turn(conversation_id, question, final_response)

    # A5: Update persisted session with latest dataset. If the session paused at
    # its budget, the next message's send is rejected and a fresh session starts.
    last_ds = last_finance_dataset.get(conversation_id, {}).get("tool_result")
    await persist_session(conversation_id, session_id, last_dataset=last_ds)

    await log_chat(
        user_name=user_name,
        user_id=user_id,
        session_id=session_id,
        conversation_id=conversation_id,
        user_msg=question,
        agent=COORDINATOR_NAME,
        agent_id=coordination_agent.id,
        env_id=ANTHROPIC_ENVIRONMENT_ID,
        tool_request=turn["tool_request"],
        tool_response=turn["tool_response"],
        tool_id=turn["tool_id"],
        assistant_msg=final_response
    )

    return (
        final_response,
        COORDINATOR_NAME
    )


def _cache_expired(persisted_session: dict) -> bool:
    """True when the session was last used longer ago than the rollover window."""
    if SESSION_IDLE_ROLLOVER_MINUTES <= 0:
        return False
    last_used = persisted_session.get("updated_at") or persisted_session.get("created_at")
    if not last_used:
        return False
    try:
        last_used_at = datetime.fromisoformat(str(last_used).replace("Z", "+00:00"))
    except ValueError:
        return False
    if last_used_at.tzinfo is None:
        last_used_at = last_used_at.replace(tzinfo=timezone.utc)
    idle = datetime.now(timezone.utc) - last_used_at
    return idle > timedelta(minutes=SESSION_IDLE_ROLLOVER_MINUTES)


async def _create_session(conversation_id: str) -> str:
    """Create a budgeted Managed Agents session for this conversation (T11)."""
    session = await async_client.beta.sessions.create(
        agent=coordination_agent.id,
        environment_id=ANTHROPIC_ENVIRONMENT_ID,
        title=f"Finance chat {conversation_id}",
        budget={
            "type": "limit",
            "max_list_cost": {"amount": SESSION_BUDGET_CENTS, "currency": "USD"},
        },
    )
    print("Session created:", session.id)
    await persist_session(conversation_id, session.id)
    return session.id


async def _run_agent_turn(
    session_id: str,
    agent_question: str,
    question: str,
    conversation_id: str,
    user_name: str | None,
    user_id: str | None
) -> dict:
    """
    Send one user message to the session and drive it until the agent finishes,
    answering get_finance_data calls along the way.
    """
    state = {
        "final_response": "",
        "tool_request": None,
        "tool_response": None,
        "tool_id": None,
        "db_call_count": 0,
        "budget_reached": False,
        "usage": None,
        "last_report": "",
        "participating_agents": [],
    }

    # M1: Cumulative token tracking across all model calls in this turn
    totals = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}

    agent_span = tracer.start_span("chat.coordination_agent")
    agent_span.set_attribute("agent.name", COORDINATOR_NAME)
    agent_span.set_attribute("model.name", MODEL_USED)
    agent_span.set_attribute("conversation.id", conversation_id)

    processed_event_ids: set[str] = set()
    message_sent = False
    done = False
    stream_attempt = 0

    async def handle(event) -> bool:
        """Process one event. Returns True when the turn is finished."""
        event_type = getattr(event, "type", None)

        if event_type == "span.model_request_end":
            model_usage = getattr(event, "model_usage", None)
            if model_usage:
                input_tokens = getattr(model_usage, "input_tokens", 0) or 0
                output_tokens = getattr(model_usage, "output_tokens", 0) or 0
                totals["input"] += input_tokens
                totals["output"] += output_tokens
                totals["cache_read"] += getattr(model_usage, "cache_read_input_tokens", 0) or 0
                totals["cache_creation"] += getattr(model_usage, "cache_creation_input_tokens", 0) or 0

                input_token_counter.add(input_tokens, {"model": MODEL_USED})
                output_token_counter.add(output_tokens, {"model": MODEL_USED})

                agent_span.set_attribute("input.tokens", totals["input"])
                agent_span.set_attribute("output.tokens", totals["output"])
                agent_span.set_attribute("cache.read.tokens", totals["cache_read"])
                agent_span.set_attribute("cache.creation.tokens", totals["cache_creation"])

                print(
                    f"\nToken Usage (Model Request: in={input_tokens}, out={output_tokens}, "
                    f"cache_read={getattr(model_usage, 'cache_read_input_tokens', 0) or 0} | "
                    f"Turn total: in={totals['input']}, out={totals['output']})"
                )

                # M4: Compact process log entry
                await create_process_log(
                    user_name=user_name,
                    user_id=user_id,
                    session_id=session_id,
                    conversation_id=conversation_id,
                    agent_id=coordination_agent.id,
                    agent_name=COORDINATOR_NAME,
                    env_id=ANTHROPIC_ENVIRONMENT_ID,
                    tool_id=state["tool_id"],
                    tool_req=state["tool_request"],
                    tool_response=state["tool_response"],
                    parent_agent="Model",
                    child_agent=COORDINATOR_NAME,
                    input_data=question,
                    output_data="Model request completed",
                    context_window=None,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model_used=MODEL_USED
                )

        # Multiagent: the coordinator delegated to a roster agent (new thread)
        elif event_type == "session.thread_created":
            agent_name = getattr(event, "agent_name", None)
            sub_agent = AGENTS_BY_NAME.get(agent_name)
            if sub_agent and sub_agent is not coordination_agent:
                if agent_name not in state["participating_agents"]:
                    state["participating_agents"].append(agent_name)
                print(f"{COORDINATOR_NAME} → {agent_name}")
                await create_process_log(
                    user_name=user_name,
                    user_id=user_id,
                    session_id=session_id,
                    conversation_id=conversation_id,
                    agent_id=sub_agent.id,
                    agent_name=agent_name,
                    env_id=ANTHROPIC_ENVIRONMENT_ID,
                    tool_id=None,
                    tool_req=None,
                    tool_response=None,
                    parent_agent=COORDINATOR_NAME,
                    child_agent=agent_name,
                    input_data=question,
                    output_data="Request routed to agent",
                    context_window=None,
                    input_tokens=None,
                    output_tokens=None,
                    model_used=MODEL_USED
                )

        # Multiagent: a roster agent reported back to the coordinator
        elif event_type == "agent.thread_message_received":
            agent_name = getattr(event, "from_agent_name", None)
            report = _text_of(getattr(event, "content", None))
            if report:
                state["last_report"] = report
                # Only coordinator text written after the latest report is the
                # answer; earlier text was an interim note ("Let me check...")
                state["final_response"] = ""
                if agent_name and agent_name not in state["participating_agents"]:
                    state["participating_agents"].append(agent_name)
                sub_agent = AGENTS_BY_NAME.get(agent_name)
                await create_process_log(
                    user_name=user_name,
                    user_id=user_id,
                    session_id=session_id,
                    conversation_id=conversation_id,
                    agent_id=sub_agent.id if sub_agent else None,
                    agent_name=agent_name,
                    env_id=ANTHROPIC_ENVIRONMENT_ID,
                    tool_id=None,
                    tool_req=None,
                    tool_response=None,
                    parent_agent=agent_name,
                    child_agent=COORDINATOR_NAME,
                    input_data=question,
                    output_data=report,
                    context_window=None,
                    input_tokens=None,
                    output_tokens=None,
                    model_used=MODEL_USED
                )

        elif event_type == "agent.custom_tool_use":
            await _answer_tool_call(event, state, session_id, question, conversation_id, user_name, user_id)

        elif event_type == "agent.message":
            text_parts = [
                block.text for block in event.content
                if getattr(block, "type", None) == "text"
            ]
            if text_parts:
                response_text = "".join(text_parts)
                state["final_response"] = response_text
                print("\nAgent response:\n", response_text)

                await create_process_log(
                    user_name=user_name,
                    user_id=user_id,
                    session_id=session_id,
                    conversation_id=conversation_id,
                    agent_id=coordination_agent.id,
                    agent_name=COORDINATOR_NAME,
                    env_id=ANTHROPIC_ENVIRONMENT_ID,
                    tool_id=None,
                    tool_req=None,
                    tool_response=None,
                    parent_agent="User",
                    child_agent=COORDINATOR_NAME,
                    input_data=agent_question,
                    output_data=response_text,
                    context_window=None,
                    input_tokens=totals["input"] or None,
                    output_tokens=totals["output"] or None,
                    model_used=MODEL_USED
                )

        elif event_type == "session.usage":
            state["usage"] = event

        # ---------------------------------------------------------
        # A3: Idle-break gate. requires_action means the agent is waiting
        # for our get_finance_data result - keep reading the stream.
        # ---------------------------------------------------------
        elif event_type == "session.status_idle":
            stop_reason = getattr(event, "stop_reason", None)
            reason_type = getattr(stop_reason, "type", None) if stop_reason else None

            if reason_type == "requires_action":
                return False
            if reason_type == "budget_reached":
                print("\n[T11] Session budget reached")
                state["budget_reached"] = True
                if not state["final_response"]:
                    state["final_response"] = BUDGET_REACHED_MESSAGE
            elif reason_type == "retries_exhausted":
                print("\n[A3] Session stopped: retries_exhausted")
                if not state["final_response"]:
                    state["final_response"] = (
                        "A session error occurred while processing your request. "
                        "Please try again."
                    )
            else:
                print(f"\nRequest completed ({reason_type or 'idle'})")
            return True

        elif event_type == "session.status_terminated":
            print("\n[A3] Session terminated")
            if not state["final_response"]:
                state["final_response"] = (
                    "A session error occurred while processing your request. "
                    "Please try again."
                )
            return True

        elif event_type == "session.error":
            # Retryable errors are rescheduled by the platform; terminal ones end
            # in idle(retries_exhausted) or terminated, handled above.
            error_msg = getattr(event, "error", None) or getattr(event, "message", "Unknown session error")
            print(f"\n[A3] Session error: {error_msg}")

        return False

    try:
        while not done and stream_attempt < MAX_STREAM_RETRIES:
            stream_attempt += 1
            try:
                # A2/A4: Stream-first - open the stream, then send the message
                async with async_client.beta.sessions.events.stream(session_id=session_id) as stream:

                    if not message_sent:
                        try:
                            await async_client.beta.sessions.events.send(
                                session_id=session_id,
                                events=[
                                    {
                                        "type": "user.message",
                                        "content": [{"type": "text", "text": agent_question}]
                                    }
                                ]
                            )
                        except (anthropic.BadRequestError, anthropic.NotFoundError) as e:
                            # Session terminated, archived, deleted or paused at its budget
                            raise SessionUnavailable(str(e)) from e
                        message_sent = True

                        await create_process_log(
                            user_name=user_name,
                            user_id=user_id,
                            session_id=session_id,
                            conversation_id=conversation_id,
                            agent_id=coordination_agent.id,
                            agent_name=COORDINATOR_NAME,
                            env_id=ANTHROPIC_ENVIRONMENT_ID,
                            tool_id=None,
                            tool_req=None,
                            tool_response=None,
                            parent_agent="User",
                            child_agent=COORDINATOR_NAME,
                            input_data=agent_question,
                            output_data=f"User message sent to {COORDINATOR_NAME}",
                            context_window=None,
                            input_tokens=None,
                            output_tokens=None,
                            model_used=MODEL_USED
                        )
                    else:
                        # A4: Lossless reconnect - replay what was missed while disconnected
                        for event in await _missed_events(session_id, agent_question, processed_event_ids):
                            processed_event_ids.add(event.id)
                            if await handle(event):
                                done = True
                                break

                    if not done:
                        async for event in stream:
                            event_id = getattr(event, "id", None)
                            if event_id and event_id in processed_event_ids:
                                continue
                            if event_id:
                                processed_event_ids.add(event_id)
                            if await handle(event):
                                done = True
                                break

                    if not done:
                        # Stream closed without a finishing event - reconnect and
                        # replay what was missed
                        print(f"\n[A4] Stream closed early (attempt {stream_attempt}/{MAX_STREAM_RETRIES}); reconnecting")

            except anthropic.APIConnectionError as e:
                # A4: Stream dropped/interrupted (includes timeouts) - reconnect
                print(f"\n[A4] Stream interrupted (attempt {stream_attempt}/{MAX_STREAM_RETRIES}): {e}")
                if not message_sent:
                    raise
                if stream_attempt >= MAX_STREAM_RETRIES and not state["final_response"]:
                    state["final_response"] = (
                        "The connection was interrupted and could not be recovered. "
                        "Please try again."
                    )

        if not done and not state["final_response"]:
            state["final_response"] = (
                "The connection was interrupted and could not be recovered. "
                "Please try again."
            )

        agent_span.set_attribute("status", "success" if done else "interrupted")
    finally:
        agent_span.end()

    # M2: Authoritative session usage (cumulative for the session)
    # M2: Usage lookups are read-only (not billed) and run in the background so
    # the user doesn't wait for them
    task = asyncio.create_task(
        _log_session_usage(state, session_id, question, conversation_id, user_name, user_id)
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return state


async def _answer_tool_call(event, state, session_id, question, conversation_id, user_name, user_id):
    """Run one get_finance_data call and send the result back to the session."""
    query = event.input.get("query", "")

    state["tool_request"] = query
    state["tool_id"] = event.id

    async def send_result(text: str):
        result_event = {
            "type": "user.custom_tool_result",
            "custom_tool_use_id": event.id,
            "content": [{"type": "text", "text": text}]
        }
        # Calls from the Finance Agent's thread are cross-posted to the primary
        # stream; echo the originating thread so the result is routed back to it
        thread_id = getattr(event, "session_thread_id", None)
        if thread_id:
            result_event["session_thread_id"] = thread_id
        await async_client.beta.sessions.events.send(
            session_id=session_id,
            events=[result_event]
        )

    # T9: Enforce runtime database call limit
    state["db_call_count"] += 1
    if state["db_call_count"] > MAX_DB_CALLS:
        print(
            f"\n[T9 Tool Call Limit] Maximum {MAX_DB_CALLS} database calls reached "
            f"(attempt {state['db_call_count']}). Blocking extra query."
        )
        state["tool_response"] = (
            f"Error: Maximum allowed database tool calls ({MAX_DB_CALLS}) reached for this request. "
            "Please provide the best possible final response using the data already retrieved "
            "or indicate what further information is required."
        )
        await send_result(state["tool_response"])
        return

    print(f"\n{FINANCE_NAME} → get_finance_data (call {state['db_call_count']}/{MAX_DB_CALLS})")
    print("SQL Query:", query)

    tool_span = tracer.start_span("chat.finance_tool")
    tool_span.set_attribute("tool.name", "get_finance_data")
    tool_span.set_attribute("agent.name", FINANCE_NAME)
    tool_span.set_attribute("conversation.id", conversation_id)
    tool_span.set_attribute("tool.request", query)

    try:
        # S2: Validate SQL query for blocked operations and fan-out risk
        query_val = validate_sql_query(query)

        if query_val.get("is_blocked") or query_val.get("has_fan_out_risk"):
            validation_warnings = query_val.get("warnings", [])
            warning_text = (
                "SQL VALIDATION ERROR — QUERY NOT EXECUTED.\n\n"
                + "\n".join(validation_warnings)
                + "\n\nPlease rewrite the query safely using CTEs or subqueries "
                "to independently aggregate each dataset before joining."
            )
            print(f"\n[S2] Validation blocked query: {warning_text}")

            state["tool_response"] = warning_text
            tool_span.set_attribute("validation.blocked", True)
            tool_span.set_attribute("validation.warnings", "; ".join(validation_warnings))
            tool_span.set_attribute("tool.status", "validation_blocked")
            await send_result(warning_text)
            return

        # T8 & S1: Bounded JSON rows via the Supabase MCP server (read-only)
        tool_result = await fetch_finance_data(query)

        # S4: Convert database INR monetary values to USD at tool boundary
        tool_result = convert_tool_result_currency(tool_result)

        # S3: Validate tool data and numerical reconciliation
        parsed_rows = _parse_rows(tool_result)
        if parsed_rows is not None:
            data_val = validate_tool_data(query, parsed_rows)
            issues = data_val.get("reconciliation_issues", [])
            if issues:
                tool_result += "\n\n[Data Reconciliation Note: " + "; ".join(issues) + "]"

        # S2: Attach any non-blocking advisory warnings (e.g. Scope notes)
        advisory_notes = [w for w in query_val.get("warnings", []) if not w.startswith("BLOCKED")]
        if advisory_notes:
            tool_result += "\n\n[" + "; ".join(advisory_notes) + "]"

        state["tool_response"] = tool_result

        # T10: Cache dataset for subsequent visualization requests
        if parsed_rows:
            last_finance_dataset[conversation_id] = {
                "tool_result": tool_result,
                "query": query
            }

        print("Database result received:\n", tool_result)

        tool_span.set_attribute("tool.status", "success")
        tool_span.set_attribute("tool.response", tool_result)

        await create_process_log(
            user_name=user_name,
            user_id=user_id,
            session_id=session_id,
            conversation_id=conversation_id,
            agent_id=finance_agent.id,
            agent_name=FINANCE_NAME,
            env_id=ANTHROPIC_ENVIRONMENT_ID,
            tool_id=state["tool_id"],
            tool_req=query,
            tool_response=tool_result,
            parent_agent=FINANCE_NAME,
            child_agent="get_finance_data",
            input_data=query,
            output_data=tool_result,
            context_window=None,
            input_tokens=None,
            output_tokens=None,
            model_used=MODEL_USED
        )

        await send_result(_compact_for_model(tool_result))

    except anthropic.APIError:
        # Sending the result failed - let the stream reconnect logic handle it
        raise

    except Exception as e:
        print("Database error:", str(e))
        state["tool_response"] = f"Database error: {str(e)}"
        tool_span.record_exception(e)
        tool_span.set_attribute("tool.status", "error")

        await create_process_log(
            user_name=user_name,
            user_id=user_id,
            session_id=session_id,
            conversation_id=conversation_id,
            agent_id=finance_agent.id,
            agent_name=FINANCE_NAME,
            env_id=ANTHROPIC_ENVIRONMENT_ID,
            tool_id=state["tool_id"],
            tool_req=query,
            tool_response=state["tool_response"],
            parent_agent=FINANCE_NAME,
            child_agent="get_finance_data",
            input_data=query,
            output_data=state["tool_response"],
            context_window=None,
            input_tokens=None,
            output_tokens=None,
            model_used=MODEL_USED
        )

        await send_result(state["tool_response"])

    finally:
        tool_span.end()


async def _missed_events(session_id: str, agent_question: str, seen: set[str]) -> list:
    """
    A4: After a reconnect, return the events of the current turn that were
    emitted while the stream was down (history after our last user.message).
    """
    history = []
    async for event in async_client.beta.sessions.events.list(session_id=session_id, order="asc"):
        history.append(event)

    start = 0
    for i, event in enumerate(history):
        if getattr(event, "type", None) != "user.message":
            continue
        text = "".join(
            getattr(block, "text", "") for block in (getattr(event, "content", None) or [])
        )
        if text == agent_question:
            start = i + 1

    current_turn = history[start:]

    # A tool call whose result never reached the session (e.g. the send failed
    # when the connection dropped) must be answered again, even if already seen.
    answered = {
        getattr(e, "custom_tool_use_id", None)
        for e in current_turn
        if getattr(e, "type", None) == "user.custom_tool_result"
    }

    return [
        e for e in current_turn
        if getattr(e, "id", None) not in seen
        or (getattr(e, "type", None) == "agent.custom_tool_use" and e.id not in answered)
    ]


async def _log_session_usage(state, session_id, question, conversation_id, user_name, user_id):
    """
    M2: Log the session's authoritative usage (cumulative for the whole session:
    tokens incl. cache, list cost, running time). Per-question cost = the
    difference between consecutive rows for the same session.
    """
    usage = getattr(state.get("usage"), "usage", None) or state.get("usage")
    try:
        retrieved = await async_client.beta.sessions.retrieve(session_id=session_id)
        usage = getattr(retrieved, "usage", None) or usage
    except anthropic.APIError as e:
        print(f"[M2] Session usage retrieval note: {e}")

    if not usage:
        return

    summary = _usage_summary(usage)
    print("Session usage (cumulative):", summary)

    await create_process_log(
        user_name=user_name,
        user_id=user_id,
        session_id=session_id,
        conversation_id=conversation_id,
        agent_id=coordination_agent.id,
        agent_name=COORDINATOR_NAME,
        env_id=ANTHROPIC_ENVIRONMENT_ID,
        tool_id=None,
        tool_req=None,
        tool_response=None,
        parent_agent=COORDINATOR_NAME,
        child_agent="Session Usage",
        input_data=question,
        output_data=json.dumps(summary),
        context_window=None,
        input_tokens=summary["input_tokens"],
        output_tokens=summary["output_tokens"],
        model_used=MODEL_USED
    )

    # M2: Per-agent split - each thread (coordinator, Finance, General) carries
    # its own cumulative usage. Per-thread costs don't sum exactly to the session
    # total (that also includes session running time and is rounded separately).
    try:
        async for thread in async_client.beta.sessions.threads.list(session_id=session_id):
            if not getattr(thread, "usage", None):
                continue
            agent_name = getattr(getattr(thread, "agent", None), "name", None) or "Unknown Agent"
            agent_ref = AGENTS_BY_NAME.get(agent_name)
            thread_summary = _usage_summary(thread.usage)
            thread_summary["thread_id"] = thread.id
            print(f"Agent usage (cumulative) - {agent_name}:", thread_summary)

            await create_process_log(
                user_name=user_name,
                user_id=user_id,
                session_id=session_id,
                conversation_id=conversation_id,
                agent_id=agent_ref.id if agent_ref else None,
                agent_name=agent_name,
                env_id=ANTHROPIC_ENVIRONMENT_ID,
                tool_id=None,
                tool_req=None,
                tool_response=None,
                parent_agent=agent_name,
                child_agent="Agent Usage",
                input_data=question,
                output_data=json.dumps(thread_summary),
                context_window=None,
                input_tokens=thread_summary["input_tokens"],
                output_tokens=thread_summary["output_tokens"],
                model_used=MODEL_USED
            )
    except anthropic.APIError as e:
        print(f"[M2] Thread usage retrieval note: {e}")


def _usage_summary(usage) -> dict:
    """Plain-dict view of a session or thread usage object."""
    list_cost = getattr(usage, "list_cost", None)
    cache_creation = getattr(usage, "cache_creation", None)
    return {
        "list_cost": list_cost.model_dump() if hasattr(list_cost, "model_dump") else list_cost,
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
        "cache_creation": cache_creation.model_dump() if hasattr(cache_creation, "model_dump") else cache_creation,
        "active_seconds": getattr(usage, "active_seconds", None),
    }


def _parse_rows(tool_result: str) -> list | None:
    """Extract the JSON row array from a get_finance_data result."""
    if not tool_result:
        return None
    match = re.search(r"\[.*\]", tool_result, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        # A trailing [Note: ...] can extend the greedy match - retry up to the array end
        end = tool_result.find("]\n\n[")
        if end == -1:
            return None
        try:
            data = json.loads(tool_result[tool_result.find("["): end + 1])
        except ValueError:
            return None
    return data if isinstance(data, list) else None


def _text_of(content) -> str:
    """Join the text blocks of an event's content (str or list of blocks)."""
    if isinstance(content, str):
        return content
    return "".join(
        getattr(block, "text", None) or (block.get("text", "") if isinstance(block, dict) else "")
        for block in (content or [])
    )


def _compact_for_model(tool_result: str) -> str:
    """
    Send the same rows in columnar form - {"columns": [...], "rows": [[...]]} -
    so column names aren't repeated on every row. Tool results stay in the
    session history and are cached/re-read every later turn; this roughly halves
    their size. Notes after the JSON are kept as they are.
    """
    head, sep, notes = tool_result.partition("\n\n")
    try:
        rows = json.loads(head)
    except ValueError:
        return tool_result
    if not rows or not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        return tool_result

    columns = list(rows[0].keys())
    if any(list(r.keys()) != columns for r in rows):
        return tool_result

    compact = json.dumps(
        {"columns": columns, "rows": [[r[c] for c in columns] for r in rows]},
        separators=(",", ":"),
        default=str,
    )
    return compact + sep + notes


def _dataset_as_markdown_table(tool_result: str) -> str:
    """Render a cached get_finance_data result as a Markdown table for the chart view."""
    rows = _parse_rows(tool_result)
    if not rows or not all(isinstance(r, dict) for r in rows):
        return tool_result

    columns = list(rows[0].keys())

    def fmt(column: str, value) -> str:
        if value is None:
            return ""
        if is_monetary_column(column):
            try:
                return f"${float(str(value).replace(',', '')):,.2f}"
            except ValueError:
                pass
        return str(value).replace("|", "/")

    header = "| " + " | ".join(c.replace("_", " ").title() for c in columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| " + " | ".join(fmt(c, row.get(c)) for c in columns) + " |"
        for row in rows
    ]

    table = "\n".join([header, divider, *body])
    note = re.search(r"\[Note: .*?\]", tool_result, re.DOTALL)
    return table + (f"\n\n{note.group(0)}" if note else "")
