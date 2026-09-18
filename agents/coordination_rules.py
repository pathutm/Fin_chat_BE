def coordination_rule(
    question: str,
    result: str | None = None
) -> dict:
    """
    Coordination Agent Rules

    Rules:
    4. Currency Conversion
    9. Output Formatting
    11. Concise Final Response
    """

    # Convert the user's question to lowercase
    question_lower = question.lower()

    money_keywords = [
        "amount",
        "price",
        "cost",
        "revenue",
        "expense",
        "profit",
        "loss",
        "payment",
        "payable",
        "receivable",
        "budget",
        "salary",
        "invoice amount",
        "purchase order amount",
        "po amount",
        "total amount",
        "tax amount",
        "discount amount",
        "freight amount",
        "inventory value",
        "product cost",
        "variance amount"
    ]

    money_related = any(
        keyword in question_lower
        for keyword in money_keywords
    )

    if money_related:
        currency_conversion_required = True
        target_currency = "USD"
        currency_reason = (
            "Monetary values must be presented in USD."
        )
    else:
        currency_conversion_required = False
        target_currency = None
        currency_reason = (
            "No monetary value is involved."
        )

    if money_related:
        output_format = (
            "Present monetary values in USD with two decimal places."
        )
    else:
        output_format = (
            "Format the response clearly according to "
            "the information requested."
        )

    response_rule = (
        "Return a direct and professional answer that addresses "
        "the user's question without unnecessary details."
    )

    return {
        "currency_conversion_required":
            currency_conversion_required,

        "target_currency":
            target_currency,

        "currency_reason":
            currency_reason,

        "output_format":
            output_format,

        "response_rule":
            response_rule
    }