from core.config import ANTHROPIC_ENVIRONMENT_ID
from agents.client import client

from agents.setup import (
    coordination_agent,
    finance_agent,
    general_agent,
    SECURITY_PROMPT,
    GENERAL_AGENT_PROMPT,
    FINANCE_AGENT_PROMPT,
    COORDINATION_AGENT_PROMPT
)

from services.memory import (
    get_conversation_context,
    conversation_history
)

from services.db import (
    fetch_finance_data,
    extract_tool_result
)

from services.logging import (
    log_chat,
    create_process_log
)


MODEL_USED = "claude-haiku-4-5-20251001"


async def handle_chat_logic(
    question: str,
    conversation_id: str,
    user_name: str | None = None,
    user_id: str | None = None
):

    previous_context = get_conversation_context(
        conversation_id
    )

    if previous_context:

        agent_question = (
            previous_context
            + f"\n\nCurrent user question:\n{question}"
        )

    else:

        agent_question = question

    context_window = f"""
SECURITY PROMPT:
{SECURITY_PROMPT}

COORDINATION AGENT:
{COORDINATION_AGENT_PROMPT}

FINANCE AGENT:
{FINANCE_AGENT_PROMPT}

GENERAL AGENT:
{GENERAL_AGENT_PROMPT}

PREVIOUS CONVERSATION:
{previous_context if previous_context else "No previous conversation"}

CURRENT USER QUESTION:
{question}

CURRENT AGENT INPUT:
{agent_question}
"""

    print("\nUser:", question)
    print("Conversation ID:", conversation_id)
    print("Starting Coordination Agent...")

    session = client.beta.sessions.create(
        agent=coordination_agent.id,
        environment_id=ANTHROPIC_ENVIRONMENT_ID
    )

    print(
        "Session created:",
        session.id
    )

    await create_process_log(
        user_name=user_name,
        user_id=user_id,
        session_id=session.id,
        conversation_id=conversation_id,
        agent_id=coordination_agent.id,
        agent_name="Coordination Agent",
        env_id=ANTHROPIC_ENVIRONMENT_ID,
        tool_id=None,
        tool_req=None,
        tool_response=None,
        process_initiation="User",
        process_destination="Coordination Agent",
        input_data=question,
        output_data="Coordination Agent started",
        context_window=context_window,
        token_consumed=None,
        model_used=MODEL_USED
    )

    final_response = ""

    generated_agent = "Coordination Agent"
    generated_agent_id = coordination_agent.id

    participating_agents = []

    tool_request = None
    tool_response = None
    tool_id = None

    # Latest token usage for the current process
    current_token_consumed = None

    with client.beta.sessions.events.stream(
        session.id
    ) as stream:

        client.beta.sessions.events.send(
            session.id,
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

        await create_process_log(
            user_name=user_name,
            user_id=user_id,
            session_id=session.id,
            conversation_id=conversation_id,
            agent_id=coordination_agent.id,
            agent_name="Coordination Agent",
            env_id=ANTHROPIC_ENVIRONMENT_ID,
            tool_id=None,
            tool_req=None,
            tool_response=None,
            process_initiation="User",
            process_destination="Coordination Agent",
            input_data=agent_question,
            output_data="User message sent to Coordination Agent",
            token_consumed=None,
            model_used=MODEL_USED
        )

        for event in stream:

            # ==================================================
            # TOKEN USAGE
            # ==================================================

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

                    current_token_consumed = (
                        input_tokens
                        + output_tokens
                        + cache_read_tokens
                        + cache_creation_tokens
                    )

                    print(
                        "\nToken Usage:"
                    )

                    print(
                        "Input Tokens:",
                        input_tokens
                    )

                    print(
                        "Output Tokens:",
                        output_tokens
                    )

                    print(
                        "Cache Read Tokens:",
                        cache_read_tokens
                    )

                    print(
                        "Cache Creation Tokens:",
                        cache_creation_tokens
                    )

                    print(
                        "Total Tokens:",
                        current_token_consumed
                    )

                    print(
                        "Model:",
                        MODEL_USED
                    )

                    await create_process_log(
                        user_name=user_name,
                        user_id=user_id,
                        session_id=session.id,
                        conversation_id=conversation_id,
                        agent_id=generated_agent_id,
                        agent_name=generated_agent,
                        env_id=ANTHROPIC_ENVIRONMENT_ID,
                        tool_id=tool_id,
                        tool_req=tool_request,
                        tool_response=tool_response,
                        process_initiation="Model",
                        process_destination=generated_agent,
                        input_data=question,
                        output_data="Model request completed",
                        token_consumed=current_token_consumed,
                        model_used=MODEL_USED
                    )

            # ==================================================
            # AGENT THREAD CREATED
            # ==================================================

            elif event.type == "session.thread_created":

                agent_name = getattr(
                    event,
                    "agent_name",
                    None
                )

                if agent_name in [
                    "Finance Agent",
                    "General Agent"
                ]:

                    if agent_name not in participating_agents:

                        participating_agents.append(
                            agent_name
                        )

                    print(
                        "Coordination Agent →",
                        agent_name
                    )

                    agent_object = (
                        finance_agent
                        if agent_name == "Finance Agent"
                        else general_agent
                    )

                    await create_process_log(
                        user_name=user_name,
                        user_id=user_id,
                        session_id=session.id,
                        conversation_id=conversation_id,
                        agent_id=agent_object.id,
                        agent_name=agent_name,
                        env_id=ANTHROPIC_ENVIRONMENT_ID,
                        tool_id=None,
                        tool_req=None,
                        tool_response=None,
                        process_initiation="Coordination Agent",
                        process_destination=agent_name,
                        input_data=question,
                        output_data="Request routed to agent",
                        token_consumed=None,
                        model_used=MODEL_USED
                    )

            # ==================================================
            # FINANCE AGENT CUSTOM TOOL
            # ==================================================

            elif event.type == "agent.custom_tool_use":

                query = event.input.get(
                    "query",
                    ""
                )

                tool_request = query
                tool_id = event.id

                print(
                    "\nFinance Agent → get_finance_data"
                )

                print(
                    "SQL Query:"
                )

                print(query)

                await create_process_log(
                    user_name=user_name,
                    user_id=user_id,
                    session_id=session.id,
                    conversation_id=conversation_id,
                    agent_id=finance_agent.id,
                    agent_name="Finance Agent",
                    env_id=ANTHROPIC_ENVIRONMENT_ID,
                    tool_id=tool_id,
                    tool_req=query,
                    tool_response=None,
                    process_initiation="Finance Agent",
                    process_destination="get_finance_data",
                    input_data=query,
                    output_data="Tool request generated",
                    token_consumed=None,
                    model_used=MODEL_USED
                )

                try:

                    result = await fetch_finance_data(
                        query
                    )

                    tool_result = extract_tool_result(
                        result
                    )

                    tool_response = tool_result

                    print(
                        "Database result received:"
                    )

                    print(tool_result)

                    await create_process_log(
                        user_name=user_name,
                        user_id=user_id,
                        session_id=session.id,
                        conversation_id=conversation_id,
                        agent_id=finance_agent.id,
                        agent_name="Finance Agent",
                        env_id=ANTHROPIC_ENVIRONMENT_ID,
                        tool_id=tool_id,
                        tool_req=query,
                        tool_response=tool_result,
                        process_initiation="get_finance_data",
                        process_destination="Finance Agent",
                        input_data=query,
                        output_data=tool_result,
                        token_consumed=None,
                        model_used=MODEL_USED
                    )

                    client.beta.sessions.events.send(
                        session.id,
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

                    print(
                        "Database error:",
                        str(e)
                    )

                    tool_response = (
                        f"Database error: {str(e)}"
                    )

                    await create_process_log(
                        user_name=user_name,
                        user_id=user_id,
                        session_id=session.id,
                        conversation_id=conversation_id,
                        agent_id=finance_agent.id,
                        agent_name="Finance Agent",
                        env_id=ANTHROPIC_ENVIRONMENT_ID,
                        tool_id=tool_id,
                        tool_req=query,
                        tool_response=tool_response,
                        process_initiation="get_finance_data",
                        process_destination="Finance Agent",
                        input_data=query,
                        output_data=tool_response,
                        token_consumed=None,
                        model_used=MODEL_USED
                    )

                    client.beta.sessions.events.send(
                        session.id,
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

            # ==================================================
            # SUB-AGENT RESPONSE
            # ==================================================

            elif event.type == "agent.thread_message_received":

                agent_name = getattr(
                    event,
                    "from_agent_name",
                    None
                )

                if agent_name in [
                    "Finance Agent",
                    "General Agent"
                ]:

                    if agent_name not in participating_agents:

                        participating_agents.append(
                            agent_name
                        )

                    print(
                        "Response received from:",
                        agent_name
                    )

                    agent_object = (
                        finance_agent
                        if agent_name == "Finance Agent"
                        else general_agent
                    )

                    await create_process_log(
                        user_name=user_name,
                        user_id=user_id,
                        session_id=session.id,
                        conversation_id=conversation_id,
                        agent_id=agent_object.id,
                        agent_name=agent_name,
                        env_id=ANTHROPIC_ENVIRONMENT_ID,
                        tool_id=tool_id,
                        tool_req=tool_request,
                        tool_response=tool_response,
                        process_initiation=agent_name,
                        process_destination="Coordination Agent",
                        input_data=question,
                        output_data=f"{agent_name} response received",
                        token_consumed=current_token_consumed,
                        model_used=MODEL_USED
                    )

            # ==================================================
            # AGENT MESSAGE
            # ==================================================

            elif event.type == "agent.message":

                text_parts = []

                for block in event.content:

                    if getattr(
                        block,
                        "type",
                        None
                    ) == "text":

                        text_parts.append(
                            block.text
                        )

                if text_parts:

                    response_text = "".join(
                        text_parts
                    )

                    final_response = response_text

                    print(
                        "\nAgent response:"
                    )

                    print(response_text)

                    await create_process_log(
                        user_name=user_name,
                        user_id=user_id,
                        session_id=session.id,
                        conversation_id=conversation_id,
                        agent_id=generated_agent_id,
                        agent_name=generated_agent,
                        env_id=ANTHROPIC_ENVIRONMENT_ID,
                        tool_id=tool_id,
                        tool_req=tool_request,
                        tool_response=tool_response,
                        process_initiation="Agent",
                        process_destination="Coordination Agent",
                        input_data=question,
                        output_data=response_text,
                        token_consumed=current_token_consumed,
                        model_used=MODEL_USED
                    )

            # ==================================================
            # SESSION COMPLETED
            # ==================================================

            elif event.type == "session.status_idle":

                stop_reason = getattr(
                    event,
                    "stop_reason",
                    None
                )

                if stop_reason:

                    reason_type = getattr(
                        stop_reason,
                        "type",
                        None
                    )

                    if reason_type == "end_turn":

                        print(
                            "\nRequest completed"
                        )

                        await create_process_log(
                            user_name=user_name,
                            user_id=user_id,
                            session_id=session.id,
                            conversation_id=conversation_id,
                            agent_id=coordination_agent.id,
                            agent_name="Coordination Agent",
                            env_id=ANTHROPIC_ENVIRONMENT_ID,
                            tool_id=tool_id,
                            tool_req=tool_request,
                            tool_response=tool_response,
                            process_initiation="Coordination Agent",
                            process_destination="User",
                            input_data=question,
                            output_data="Request completed",
                            token_consumed=current_token_consumed,
                            model_used=MODEL_USED
                        )

                        break

    # ==================================================
    # FALLBACK RESPONSE
    # ==================================================

    if not final_response:

        final_response = (
            "Sorry, I could not generate a response."
        )

        await create_process_log(
            user_name=user_name,
            user_id=user_id,
            session_id=session.id,
            conversation_id=conversation_id,
            agent_id=coordination_agent.id,
            agent_name="Coordination Agent",
            env_id=ANTHROPIC_ENVIRONMENT_ID,
            tool_id=tool_id,
            tool_req=tool_request,
            tool_response=tool_response,
            process_initiation="Coordination Agent",
            process_destination="User",
            input_data=question,
            output_data=final_response,
            token_consumed=current_token_consumed,
            model_used=MODEL_USED
        )

    if participating_agents:

        print(
            "Agents participated:",
            ", ".join(participating_agents)
        )

    print(
        "Final response generated by:",
        generated_agent
    )

    await create_process_log(
        user_name=user_name,
        user_id=user_id,
        session_id=session.id,
        conversation_id=conversation_id,
        agent_id=generated_agent_id,
        agent_name=generated_agent,
        env_id=ANTHROPIC_ENVIRONMENT_ID,
        tool_id=tool_id,
        tool_req=tool_request,
        tool_response=tool_response,
        process_initiation="Coordination Agent",
        process_destination="User",
        input_data=question,
        output_data=final_response,
        token_consumed=current_token_consumed,
        model_used=MODEL_USED
    )

    # ==================================================
    # SAVE CONVERSATION HISTORY
    # ==================================================

    conversation_history.setdefault(
        conversation_id,
        []
    ).append(
        {
            "role": "user",
            "content": question
        }
    )

    conversation_history[
        conversation_id
    ].append(
        {
            "role": "assistant",
            "content": final_response
        }
    )

    print(
        "Conversation history updated:",
        conversation_id
    )

    # ==================================================
    # LOG COMPLETE CHAT
    # ==================================================

    await log_chat(
        user_name=user_name,
        user_id=user_id,
        session_id=session.id,
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

    print(
        "Chat logged to Supabase"
    )

    return final_response, generated_agent