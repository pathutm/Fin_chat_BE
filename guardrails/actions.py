from typing import Optional
from nemoguardrails.actions import action


FINANCE_KEYWORDS = {
    "salary",
    "payroll",
    "employee",
    "designation",
    "department",
    "joining date",
    "asset",
    "assets",
    "liability",
    "liabilities",
    "working capital",
    "current ratio",
    "cash",
    "accounts payable",
    "accounts receivable",
    "finance",
    "financial",
    "revenue",
    "expense",
    "profit",
    "loss",
}


@action(name="check_finance_scope")
async def check_finance_scope(
    context: Optional[dict] = None,
    user_input: Optional[str] = None,
    **kwargs,
) -> bool:
    """Return True when the request is related to the Finance chatbot."""
    text = (
        user_input
        or (context.get("user_message") if context else "")
        or (context.get("last_user_message") if context else "")
        or ""
    ).lower()

    return any(keyword in text for keyword in FINANCE_KEYWORDS)