conversation_history: dict[str, list[dict]] = {}

def get_conversation_context(conversation_id: str) -> str:
    history = conversation_history.get(conversation_id, [])
    if not history:
        return ""

    history_text = []
    for item in history:
        role = item.get("role", "")
        content = item.get("content", "")
        if role == "user":
            history_text.append(f"User: {content}")
        elif role == "assistant":
            history_text.append(f"Assistant: {content}")

    return (
        "\n\nPrevious conversation:\n"
        + "\n".join(history_text)
        + "\n\nUse this previous conversation to understand references "
        "such as 'he', 'his', 'that company', or 'the same employee'."
    )
