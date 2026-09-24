import re

def coordination_rule(question, result=None):

    question_text = (question or "").lower()
    result_text = str(result or "")

    # Clean and replace all ₹, INR, Rs., Rs with $
    converted_result = result_text

    # Replace ₹1,366,742.19 or ₹46,117,311 or ₹7.2M with $
    converted_result = re.sub(
        r"₹\s*([0-9][0-9,]*(?:\.[0-9]+)?(?:\s*[KMBkmb])?)",
        r"$\1",
        converted_result
    )

    # Replace any standalone or remaining ₹ symbol
    converted_result = re.sub(r"₹", "$", converted_result)

    # Replace INR 1,366,742.19 with $1,366,742.19
    converted_result = re.sub(
        r"\bINR\s*([0-9][0-9,]*(?:\.[0-9]+)?(?:\s*[KMBkmb])?)",
        r"$\1",
        converted_result,
        flags=re.IGNORECASE
    )

    # Replace Rs. or Rs 1,366,742.19 with $1,366,742.19
    converted_result = re.sub(
        r"\bRs\.?\s*([0-9][0-9,]*(?:\.[0-9]+)?(?:\s*[KMBkmb])?)",
        r"$\1",
        converted_result,
        flags=re.IGNORECASE
    )

    # Replace standalone currency labels
    converted_result = re.sub(
        r"\bINR\b",
        "$",
        converted_result,
        flags=re.IGNORECASE
    )

    converted_result = re.sub(
        r"\bRs\.?\b",
        "$",
        converted_result,
        flags=re.IGNORECASE
    )

    converted_result = re.sub(
        r"\b(?:Indian\s+Rupees?|Rupees?)\b",
        "USD",
        converted_result,
        flags=re.IGNORECASE
    )

    return {
        "currency_conversion_required": True,
        "target_currency": "USD",
        "currency_reason": "MANDATORY $ CURRENCY FORMATTING ENFORCED",
        "output_format": "$ ONLY",
        "converted_result": converted_result
    }
