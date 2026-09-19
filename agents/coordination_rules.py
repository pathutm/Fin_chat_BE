def coordination_rule(
    question: str,
    result: str | None = None
) -> dict:
    """
    Coordination Agent Rules

    Rules:
    1. Currency Conversion
    2. Output Formatting
    3. Graph / Chart Handling
    4. Clarification Control
    5. Concise Final Response
    """

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
        output_format = (
            "Present monetary values in USD with two decimal places."
        )
    else:
        currency_conversion_required = False
        target_currency = None
        currency_reason = (
            "No monetary value is involved."
        )
        output_format = (
            "Format the response clearly according to "
            "the information requested."
        )

    graph_keywords = [
        "graph",
        "chart",
        "graphical",
        "visualize",
        "visualization",
        "plot"
    ]

    graph_requested = any(
        keyword in question_lower
        for keyword in graph_keywords
    )

    if graph_requested:
        graph_rule = (
            "The user EXPLICITLY requested a graph or chart. "
            "DO NOT ask if they want a graph. "
            "Return BOTH the textual finance answer AND "
            "format the database numbers in a clean Markdown "
            "table or list so the frontend chart component "
            "can render the graph automatically. "
            "Use REAL database values."
        )
    else:
        graph_rule = (
            "The user did NOT explicitly request a graph. "
            "If a graph could reasonably represent the result, "
            "you may ask ONCE at the end of the response: "
            "'Would you like me to generate a graphical "
            "representation of this result? (Yes/No)'. "
            "If a clarification question is also required, "
            "combine the graph question into the single "
            "clarification question."
        )

    clarification_rule = (
        "STRICT CLARIFICATION CONTROL: Maximum 1 clarification "
        "question normally, maximum 2 in absolute worst case. "
        "NEVER ask 3 or more clarification questions. "
        "DO NOT ask clarification for specific identifiers "
        "(e.g. 'invoice 000025', 'PO-000001', "
        "'PROD-000025', 'working capital'). "
        "Always query the database and check context first. "
        "If multiple pieces of information are genuinely "
        "missing, COMBINE them into ONE single consolidated "
        "question. "
        "If user says 'don't ask any more questions' or "
        "provides an answer, DO NOT ask another question; "
        "proceed with the best available information."
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
            response_rule,

        "graph_requested":
            graph_requested,

        "graph_rule":
            graph_rule,

        "clarification_rule":
            clarification_rule
    }