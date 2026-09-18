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
from agents.coordination_rules import coordination_rule

MODEL_USED = "claude-haiku-4-5-20251001"

async def handle_chat_logic(
    question: str,
    conversation_id: str,
    user_name: str | None = None,
    user_id: str | None = None
):
    previous_context = get_conversation_context(conversation_id)

    if previous_context:
        agent_question = (
            previous_context
            + f"\n\nCurrent user question:\n{question}"
        )
    else:
        agent_question = question

    coordination_process = coordination_rule(question)

    print("\nCoordination Rule")
    print("Question:", question)
    print("Money Related:", coordination_process["currency_conversion_required"])
    print("Target Currency:", coordination_process["target_currency"])
    print("Currency Reason:", coordination_process["currency_reason"])

    context_window = f"""
SECURITY PROMPT:
{SECURITY_PROMPT}

COORDINATION AGENT:
{COORDINATION_AGENT_PROMPT}

FINANCE AGENT:
{FINANCE_AGENT_PROMPT}

GENERAL AGENT:
{GENERAL_AGENT_PROMPT}

COORDINATION RULES:

Currency Conversion:
{coordination_process["currency_reason"]}

Target Currency:
{coordination_process["target_currency"]}

Output Formatting:
{coordination_process["output_format"]}

STRICT CURRENCY REQUIREMENT:

If currency_conversion_required is True:

- Every monetary value in the final response MUST be displayed in USD.
- All INR monetary values MUST be converted to USD.
- Use the "$" symbol for every USD monetary value.
- Do NOT display the "₹" symbol in the final response.
- Do NOT display "INR" in the final response.
- Do NOT simply replace "₹" or "INR" with "$".
- The monetary value must represent the converted USD amount.
- Every monetary value in the response must follow the USD requirement.
- Always format USD monetary values with exactly two decimal places.
- Do not leave any monetary value in INR when USD conversion is required.
- Do not provide mixed INR and USD monetary values.
- Apply this requirement to invoice amounts, purchase order amounts, prices, costs, revenue, expenses, profit, tax, freight, discounts, payments, and all other monetary values.

If currency_conversion_required is False:

- Preserve the original database currency.
- Do not perform unnecessary currency conversion.

FINAL RESPONSE REQUIREMENT:

Before returning the final response, verify that every monetary value follows the currency conversion requirement.

Final Response:
{coordination_process["response_rule"]}

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

    print("Session created:", session.id)

    final_response = ""
    generated_agent = "Coordination Agent"
    generated_agent_id = coordination_agent.id
    participating_agents = []
    tool_request = None
    tool_response = None
    tool_id = None

    pending_model_usage = {}

    thread_agents = {
        session.id: (
            "Coordination Agent",
            coordination_agent.id
        )
    }

    with client.beta.sessions.events.stream(session.id) as stream:

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

        for event in stream:

            event_type = event.type

            if event_type == "span.model_request_end":

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

                    thread_id = getattr(
                        event,
                        "session_thread_id",
                        None
                    )

                    if not thread_id:
                        thread_id = session.id

                    pending_model_usage[thread_id] = {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens
                    }

                    print("\nModel Token Usage")
                    print("Thread:", thread_id)
                    print("Input Tokens:", input_tokens)
                    print("Output Tokens:", output_tokens)
                    print("Model:", MODEL_USED)

            elif event_type == "session.thread_created":

                agent_name = getattr(
                    event,
                    "agent_name",
                    None
                )

                thread_id = getattr(
                    event,
                    "session_thread_id",
                    None
                )

                if agent_name in [
                    "Finance Agent",
                    "General Agent"
                ]:

                    if agent_name not in participating_agents:
                        participating_agents.append(agent_name)

                    agent_object = (
                        finance_agent
                        if agent_name == "Finance Agent"
                        else general_agent
                    )

                    if thread_id:
                        thread_agents[thread_id] = (
                            agent_name,
                            agent_object.id
                        )

                    generated_agent = agent_name
                    generated_agent_id = agent_object.id

                    print(
                        "Coordination Agent →",
                        agent_name
                    )

            elif event_type == "agent.custom_tool_use":

                query = event.input.get(
                    "query",
                    ""
                )

                tool_request = query
                tool_id = event.id

                generated_agent = "Finance Agent"
                generated_agent_id = finance_agent.id

                print("\nFinance Agent → get_finance_data")
                print("SQL Query:")
                print(query)

                try:

                    result = await fetch_finance_data(query)

                    tool_result = extract_tool_result(result)

                    tool_response = tool_result

                    print("Database result received:")
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
                        parent_agent="Finance Agent",
                        child_agent="get_finance_data",
                        input_data=query,
                        output_data=tool_result,
                        context_window=None,
                        input_tokens=None,
                        output_tokens=None,
                        model_used=None
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

                    print("Database error:", str(e))

                    tool_response = f"Database error: {str(e)}"

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
                        parent_agent="Finance Agent",
                        child_agent="get_finance_data",
                        input_data=query,
                        output_data=tool_response,
                        context_window=None,
                        input_tokens=None,
                        output_tokens=None,
                        model_used=None
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

            elif event_type == "agent.thread_message_received":

                agent_name = getattr(
                    event,
                    "from_agent_name",
                    None
                )

                thread_id = getattr(
                    event,
                    "session_thread_id",
                    None
                )

                if agent_name in [
                    "Finance Agent",
                    "General Agent"
                ]:

                    if agent_name not in participating_agents:
                        participating_agents.append(agent_name)

                    agent_object = (
                        finance_agent
                        if agent_name == "Finance Agent"
                        else general_agent
                    )

                    generated_agent = agent_name
                    generated_agent_id = agent_object.id

                    usage = pending_model_usage.get(
                        thread_id,
                        {}
                    )

                    input_tokens = usage.get(
                        "input_tokens"
                    )

                    output_tokens = usage.get(
                        "output_tokens"
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
                        parent_agent="Coordination Agent",
                        child_agent=agent_name,
                        input_data=question,
                        output_data=f"{agent_name} response received",
                        context_window=context_window,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        model_used=MODEL_USED
                    )

            elif event_type == "agent.message":

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

                    response_text = "".join(text_parts)

                    final_response = response_text

                    print("\nAgent response:")
                    print(response_text)

                    usage = pending_model_usage.get(
                        session.id,
                        {}
                    )

                    input_tokens = usage.get(
                        "input_tokens"
                    )

                    output_tokens = usage.get(
                        "output_tokens"
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
                        parent_agent="User",
                        child_agent="Coordination Agent",
                        input_data=agent_question,
                        output_data=response_text,
                        context_window=context_window,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        model_used=MODEL_USED
                    )

            elif event_type == "session.status_idle":

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
                        print("\nRequest completed")
                        break

    if not final_response:
        final_response = (
            "Sorry, I could not generate a response."
        )

    conversation_history.setdefault(
        conversation_id,
        []
    ).append(
        {
            "role": "user",
            "content": question
        }
    )

    conversation_history[conversation_id].append(
        {
            "role": "assistant",
            "content": final_response
        }
    )

    print(
        "Conversation history updated:",
        conversation_id
    )

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

    print("Chat logged to Supabase")

    return final_response, generated_agent