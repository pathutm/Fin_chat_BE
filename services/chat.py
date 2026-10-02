from core.config import ANTHROPIC_ENVIRONMENT_ID
import re
import json

from agents.client import async_client

from agents.setup import (
    coordination_agent,
    finance_agent,
    general_agent,
    SESSION_BUDGET_LIMIT_USD,
    estimate_session_cost
)

from services.memory import (
    conversation_history,
    last_finance_dataset,
    persist_session,
    load_session,
    get_bounded_conversation_context
)

from services.db import (
    fetch_finance_data,
    extract_tool_result
)

from services.logging import (
    log_chat,
    create_process_log
)

from agents.coordination_rules import (
    coordination_rule,
    convert_tool_result_currency
)

from services.validation import (
    validate_sql_query,
    validate_tool_data,
    validate_and_sanitize_response
)

from guardrails.actions import (
    detect_finance_intent,
    detect_non_finance,
    is_standalone_greeting,
    is_affirmative_confirmation
)

from core.telemetry import (
    tracer,
    input_token_counter,
    output_token_counter
)


MODEL_USED = "claude-haiku-4-5-20251001"

# A4: Maximum stream reconnect attempts
MAX_STREAM_RETRIES = 3


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
        conversation_history.setdefault(conversation_id, []).append({"role": "user", "content": question})
        conversation_history[conversation_id].append({"role": "assistant", "content": greeting_response})
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
    is_explicit_viz = bool(re.search(r'(?i)\b(visualiz|chart|graph|plot)\b', question))
    is_referential = bool(re.search(r'(?i)\b(this|that|it|these|the\s+data|the\s+result|above|dataset)\b', question))
    is_short_prompt = len(question.strip().split()) <= 4

    is_viz_confirmation = (
        is_affirmative_confirmation(question)
        or (is_explicit_viz and (is_referential or is_short_prompt))
    )
    if is_viz_confirmation and conversation_id in last_finance_dataset:
        cached_data = last_finance_dataset[conversation_id]
        tool_result = cached_data.get("tool_result", "")
        viz_response = (
            "Here is the chart visualization for the previously retrieved financial dataset:\n\n"
            f"{tool_result}\n\n"
            "The visualization displays the verified dataset from your query."
        )
        conversation_history.setdefault(conversation_id, []).append({"role": "user", "content": question})
        conversation_history[conversation_id].append({"role": "assistant", "content": viz_response})
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

    # ---------------------------------------------------------
    # T7: STRICT BOUNDED CONTEXT STRATEGY (MAX 3 PREVIOUS MESSAGES)
    # ---------------------------------------------------------
    recent_ctx = get_bounded_conversation_context(conversation_id, max_messages=3)
    if recent_ctx:
        agent_question = f"{recent_ctx}\nCurrent User Question:\n{question}"
    else:
        agent_question = question

    # Deterministic Agent Selection (Eliminates Coordinator LLM routing call - T5)
    if detect_non_finance(question) and not detect_finance_intent(question):
        target_agent = general_agent
        agent_name = "General Agent"
    else:
        target_agent = finance_agent
        agent_name = "Finance Agent"

    print(f"\nDeterministic routing → {agent_name}")
    print("User:", question)
    print("Conversation ID:", conversation_id)

    # A5 & T7: Persistent session reuse per conversation
    persisted_session = await load_session(conversation_id)
    session_id = persisted_session.get("session_id") if persisted_session else None

    if not session_id:
        # A2 & T11: Create session with budget limit
        session = await async_client.beta.sessions.create(
            agent=target_agent.id,
            environment_id=ANTHROPIC_ENVIRONMENT_ID
        )
        session_id = session.id
        print("Session created:", session_id)
        await persist_session(conversation_id, session_id)
    else:
        print("Session reused:", session_id)

    final_response = ""
    generated_agent = agent_name
    generated_agent_id = target_agent.id

    tool_request = None
    tool_response = None
    tool_id = None
    db_call_count = 0

    # T11 & M1: Cumulative token tracking across all model calls / threads in the session
    cumulative_input_tokens = 0
    cumulative_output_tokens = 0
    cumulative_cache_read_tokens = 0
    cumulative_cache_creation_tokens = 0

    agent_span = tracer.start_span(
        f"chat.{agent_name.lower().replace(' ', '_')}"
    )
    agent_span.set_attribute("agent.name", agent_name)
    agent_span.set_attribute("model.name", MODEL_USED)
    agent_span.set_attribute("conversation.id", conversation_id)

    tool_span = None

    # A4: Stream with reconnect logic and retry bounds
    stream_attempt = 0
    message_sent = False
    processed_event_ids = set()

    while stream_attempt < MAX_STREAM_RETRIES:
        stream_attempt += 1
        try:
            # A2: Use async_client for streaming
            async with async_client.beta.sessions.events.stream(
                session_id
            ) as stream:

                # Send user message only on the first attempt
                if not message_sent:
                    await async_client.beta.sessions.events.send(
                        session_id,
                        events=[
                            {
                                "type": "user.message",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": agent_question
                                    }
                                ]
                            }
                        ]
                    )
                    message_sent = True

                    # M4: Compact process log (no full 12KB context_window dumping)
                    await create_process_log(
                        user_name=user_name,
                        user_id=user_id,
                        session_id=session_id,
                        conversation_id=conversation_id,
                        agent_id=target_agent.id,
                        agent_name=agent_name,
                        env_id=ANTHROPIC_ENVIRONMENT_ID,
                        tool_id=None,
                        tool_req=None,
                        tool_response=None,
                        parent_agent="User",
                        child_agent=agent_name,
                        input_data=agent_question,
                        output_data=f"User message sent to {agent_name}",
                        context_window=None,
                        input_tokens=None,
                        output_tokens=None,
                        model_used=MODEL_USED
                    )

                async for event in stream:

                    # A4: Deduplicate events across reconnects
                    event_id = getattr(event, "id", None)
                    if event_id and event_id in processed_event_ids:
                        continue
                    if event_id:
                        processed_event_ids.add(event_id)

                    if event.type == "span.model_request_end":

                        model_usage = getattr(
                            event,
                            "model_usage",
                            None
                        )

                        if model_usage:

                            input_tokens = getattr(
                                model_usage,
                                "input_tokens",
                                0
                            ) or 0

                            output_tokens = getattr(
                                model_usage,
                                "output_tokens",
                                0
                            ) or 0

                            cache_read_tokens = getattr(
                                model_usage,
                                "cache_read_input_tokens",
                                0
                            ) or 0

                            cache_creation_tokens = getattr(
                                model_usage,
                                "cache_creation_input_tokens",
                                0
                            ) or 0

                            # M1: Accumulate tokens accurately
                            cumulative_input_tokens += input_tokens
                            cumulative_output_tokens += output_tokens
                            cumulative_cache_read_tokens += cache_read_tokens
                            cumulative_cache_creation_tokens += cache_creation_tokens

                            input_token_counter.add(
                                input_tokens,
                                {
                                    "model": MODEL_USED
                                }
                            )

                            output_token_counter.add(
                                output_tokens,
                                {
                                    "model": MODEL_USED
                                }
                            )

                            if agent_span:
                                agent_span.set_attribute(
                                    "input.tokens",
                                    cumulative_input_tokens
                                )
                                agent_span.set_attribute(
                                    "output.tokens",
                                    cumulative_output_tokens
                                )
                                agent_span.set_attribute(
                                    "cache.read.tokens",
                                    cumulative_cache_read_tokens
                                )
                                agent_span.set_attribute(
                                    "cache.creation.tokens",
                                    cumulative_cache_creation_tokens
                                )

                            print(f"\nToken Usage (Model Request: in={input_tokens}, out={output_tokens} | Total: in={cumulative_input_tokens}, out={cumulative_output_tokens})")

                            # M4: Compact process log entry
                            await create_process_log(
                                user_name=user_name,
                                user_id=user_id,
                                session_id=session_id,
                                conversation_id=conversation_id,
                                agent_id=target_agent.id,
                                agent_name=agent_name,
                                env_id=ANTHROPIC_ENVIRONMENT_ID,
                                tool_id=tool_id,
                                tool_req=tool_request,
                                tool_response=tool_response,
                                parent_agent="Model",
                                child_agent=agent_name,
                                input_data=question,
                                output_data="Model request completed",
                                context_window=None,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                model_used=MODEL_USED
                            )

                            # T11: Check session budget limit
                            session_cost = estimate_session_cost(
                                cumulative_input_tokens,
                                cumulative_output_tokens
                            )
                            if session_cost >= SESSION_BUDGET_LIMIT_USD:
                                print(
                                    f"\n[T11] Session budget limit reached: "
                                    f"${session_cost:.4f} >= ${SESSION_BUDGET_LIMIT_USD}"
                                )
                                final_response = (
                                    "This session has reached the maximum allowed cost budget. "
                                    "Please start a new conversation for additional queries."
                                )
                                break

                    elif event.type == "agent.custom_tool_use":

                        query = event.input.get(
                            "query",
                            ""
                        )

                        tool_request = query
                        tool_id = event.id

                        # T9: Enforce runtime database call limit (max 3 calls)
                        db_call_count += 1
                        if db_call_count > 3:
                            print(
                                f"\n[T9 Tool Call Limit] Maximum 3 database calls reached (attempt {db_call_count}). Blocking extra query."
                            )
                            tool_response = (
                                "Error: Maximum allowed database tool calls (3) reached for this request. "
                                "Please provide the best possible final response using the data already retrieved or indicate what further information is required."
                            )
                            await async_client.beta.sessions.events.send(
                                session_id,
                                events=[
                                    {
                                        "type": "user.custom_tool_result",
                                        "custom_tool_use_id": event.id,
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": tool_response
                                            }
                                        ]
                                    }
                                ]
                            )
                            continue

                        print(
                            f"\n{agent_name} → get_finance_data (call {db_call_count}/3)"
                        )
                        print("SQL Query:", query)

                        tool_span = tracer.start_span(
                            "chat.finance_tool"
                        )
                        tool_span.set_attribute("tool.name", "get_finance_data")
                        tool_span.set_attribute("agent.name", agent_name)
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

                                tool_response = warning_text
                                tool_span.set_attribute("validation.blocked", True)
                                tool_span.set_attribute("validation.warnings", "; ".join(validation_warnings))

                                await async_client.beta.sessions.events.send(
                                    session_id,
                                    events=[
                                        {
                                            "type": "user.custom_tool_result",
                                            "custom_tool_use_id": event.id,
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": warning_text
                                                }
                                            ]
                                        }
                                    ]
                                )

                                if tool_span:
                                    tool_span.set_attribute("tool.status", "validation_blocked")
                                    tool_span.end()
                                    tool_span = None
                                continue

                            # T8 & S1: Fetch bounded data via asyncpg pool / read-only execution
                            result = await fetch_finance_data(query)
                            tool_result = extract_tool_result(result)

                            # S4: Convert database INR monetary values to USD at tool boundary
                            tool_result = convert_tool_result_currency(tool_result)

                            # S3: Validate tool data and numerical reconciliation
                            parsed_data = None
                            try:
                                if tool_result.strip().startswith(("{", "[")):
                                    parsed_data = json.loads(tool_result)
                                elif "{" in tool_result or "[" in tool_result:
                                    m = re.search(r'\[.*\]|\{.*\}', tool_result, re.DOTALL)
                                    if m:
                                        parsed_data = json.loads(m.group(0))
                            except Exception:
                                pass

                            if parsed_data is not None:
                                data_val = validate_tool_data(query, parsed_data)
                                if not data_val.get("reconciliation_passed", True):
                                    issues = data_val.get("reconciliation_issues", [])
                                    if issues:
                                        tool_result += "\n\n[Data Reconciliation Note: " + "; ".join(issues) + "]"

                            # S2: Attach any non-blocking advisory warnings (e.g. Scope notes)
                            if query_val.get("warnings"):
                                advisory_notes = [w for w in query_val["warnings"] if not w.startswith("BLOCKED")]
                                if advisory_notes:
                                    tool_result += "\n\n[" + "; ".join(advisory_notes) + "]"

                            tool_response = tool_result

                            # T10: Cache dataset for subsequent visualization requests
                            last_finance_dataset[conversation_id] = {
                                "tool_result": tool_result,
                                "query": query
                            }

                            print("Database result received:\n", tool_result)

                            tool_span.set_attribute("tool.status", "success")
                            tool_span.set_attribute("tool.response", tool_result)

                            # M4: Compact process log
                            await create_process_log(
                                user_name=user_name,
                                user_id=user_id,
                                session_id=session_id,
                                conversation_id=conversation_id,
                                agent_id=target_agent.id,
                                agent_name=agent_name,
                                env_id=ANTHROPIC_ENVIRONMENT_ID,
                                tool_id=tool_id,
                                tool_req=query,
                                tool_response=tool_result,
                                parent_agent=agent_name,
                                child_agent="get_finance_data",
                                input_data=query,
                                output_data=tool_result,
                                context_window=None,
                                input_tokens=None,
                                output_tokens=None,
                                model_used=MODEL_USED
                            )

                            await async_client.beta.sessions.events.send(
                                session_id,
                                events=[
                                    {
                                        "type": "user.custom_tool_result",
                                        "custom_tool_use_id": event.id,
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": tool_result
                                            }
                                        ]
                                    }
                                ]
                            )

                        except Exception as e:
                            print("Database error:", str(e))
                            tool_response = f"Database error: {str(e)}"
                            tool_span.record_exception(e)
                            tool_span.set_attribute("tool.status", "error")

                            await create_process_log(
                                user_name=user_name,
                                user_id=user_id,
                                session_id=session_id,
                                conversation_id=conversation_id,
                                agent_id=target_agent.id,
                                agent_name=agent_name,
                                env_id=ANTHROPIC_ENVIRONMENT_ID,
                                tool_id=tool_id,
                                tool_req=query,
                                tool_response=tool_response,
                                parent_agent=agent_name,
                                child_agent="get_finance_data",
                                input_data=query,
                                output_data=tool_response,
                                context_window=None,
                                input_tokens=None,
                                output_tokens=None,
                                model_used=MODEL_USED
                            )

                            await async_client.beta.sessions.events.send(
                                session_id,
                                events=[
                                    {
                                        "type": "user.custom_tool_result",
                                        "custom_tool_use_id": event.id,
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": tool_response
                                            }
                                        ]
                                    }
                                ]
                            )

                        finally:
                            if tool_span:
                                tool_span.end()
                                tool_span = None

                    elif event.type == "agent.message":
                        text_parts = []
                        for block in event.content:
                            if getattr(block, "type", None) == "text":
                                text_parts.append(block.text)

                        if text_parts:
                            response_text = "".join(text_parts)
                            final_response = response_text
                            print("\nAgent response:\n", response_text)

                            await create_process_log(
                                user_name=user_name,
                                user_id=user_id,
                                session_id=session_id,
                                conversation_id=conversation_id,
                                agent_id=target_agent.id,
                                agent_name=agent_name,
                                env_id=ANTHROPIC_ENVIRONMENT_ID,
                                tool_id=None,
                                tool_req=None,
                                tool_response=None,
                                parent_agent="User",
                                child_agent=agent_name,
                                input_data=agent_question,
                                output_data=response_text,
                                context_window=None,
                                input_tokens=cumulative_input_tokens or None,
                                output_tokens=cumulative_output_tokens or None,
                                model_used=MODEL_USED
                            )

                    # ---------------------------------------------------------
                    # A3: Handle ALL terminal/error stream states
                    # ---------------------------------------------------------
                    elif event.type == "session.status_idle":
                        stop_reason = getattr(event, "stop_reason", None)
                        if stop_reason:
                            reason_type = getattr(stop_reason, "type", None)
                            if reason_type == "end_turn":
                                print("\nRequest completed (end_turn)")
                                break
                            elif reason_type == "max_tokens":
                                print("\n[A3] Session stopped: max_tokens reached")
                                if not final_response:
                                    final_response = (
                                        "The response was truncated because the maximum token limit was reached. "
                                        "Please try a more specific question."
                                    )
                                break
                            elif reason_type == "stop_sequence":
                                print("\n[A3] Session stopped: stop_sequence hit")
                                break
                            else:
                                print(f"\n[A3] Session stopped with reason: {reason_type}")
                                break
                        else:
                            print("\n[A3] Session idle (no stop_reason) — completing")
                            break

                    elif event.type == "session.error":
                        error_msg = getattr(event, "error", None) or getattr(event, "message", "Unknown session error")
                        print(f"\n[A3] Session error: {error_msg}")
                        if not final_response:
                            final_response = (
                                "A session error occurred while processing your request. "
                                "Please try again."
                            )
                        break

                else:
                    break

            break

        except (ConnectionError, TimeoutError, OSError) as e:
            # A4: Stream dropped/interrupted — reconnect
            print(f"\n[A4] Stream interrupted (attempt {stream_attempt}/{MAX_STREAM_RETRIES}): {e}")
            if stream_attempt >= MAX_STREAM_RETRIES:
                print("[A4] Max stream retries exhausted")
                if not final_response:
                    final_response = (
                        "The connection was interrupted and could not be recovered. "
                        "Please try again."
                    )
            # Preserves db_call_count (T9)
            continue

    # M2: Authoritative session usage retrieval
    try:
        retrieved_session = await async_client.beta.sessions.retrieve(session_id)
        if hasattr(retrieved_session, "usage") and retrieved_session.usage:
            u = retrieved_session.usage
            cumulative_input_tokens = getattr(u, "input_tokens", cumulative_input_tokens)
            cumulative_output_tokens = getattr(u, "output_tokens", cumulative_output_tokens)
            cumulative_cache_read_tokens = getattr(u, "cache_read_input_tokens", cumulative_cache_read_tokens)
            cumulative_cache_creation_tokens = getattr(u, "cache_creation_input_tokens", cumulative_cache_creation_tokens)
    except Exception as e:
        print(f"[M2] Session usage retrieval note: {e}")

    if agent_span:
        agent_span.set_attribute("status", "success")
        agent_span.end()

    if not final_response:
        final_response = "Sorry, I could not generate a response."

    # S4 & Issue 28: Conditional deterministic currency conversion and response sanitization
    coordination_process = coordination_rule(question, result=final_response)
    final_response = coordination_process.get("converted_result", final_response)
    final_response = validate_and_sanitize_response(final_response)

    conversation_history.setdefault(conversation_id, []).append({"role": "user", "content": question})
    conversation_history[conversation_id].append({"role": "assistant", "content": final_response})

    # A5: Update persisted session with latest dataset
    last_ds = last_finance_dataset.get(conversation_id, {}).get("tool_result")
    await persist_session(conversation_id, session_id, last_dataset=last_ds)

    await log_chat(
        user_name=user_name,
        user_id=user_id,
        session_id=session_id,
        conversation_id=conversation_id,
        user_msg=question,
        agent=generated_agent,
        agent_id=generated_agent_id,
        env_id=ANTHROPIC_ENVIRONMENT_ID,
        tool_request=tool_request,
        tool_response=tool_response,
        tool_id=tool_id,
        assistant_msg=final_response
    )

    return (
        final_response,
        generated_agent
    )