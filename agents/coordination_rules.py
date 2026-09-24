import json
import os
import re

# Fixed exchange rate: ₹95.7 = $1 USD. Conversion formula: USD = INR / 95.7
INR_PER_USD = 95.7
INR_TO_USD_RATE = 1.0 / INR_PER_USD


NON_MONETARY_TERMS = {
    "quantity", "qty", "count", "percent", "pct", "percentage",
    "rate", "date", "month", "year", "day", "number", "status",
    "terms", "name", "type", "category", "uom", "measure",
    "diameter", "length", "pressure", "grade", "lot", "reason",
    "currency", "match", "ratio"
}

MONETARY_TERMS = {
    "price", "cost", "amount", "value", "spend", "revenue",
    "sales", "profit", "loss", "salary", "credit_limit",
    "subtotal", "freight", "discount", "tax", "budget",
    "payable", "receivable", "total", "sum", "avg", "min", "max"
}


def is_monetary_column(col_name: str) -> bool:
    """
    Deterministically determines if a database column or alias represents a monetary value.
    Non-monetary fields (quantities, counts, dates, IDs, percentages, ratios) return False.
    """
    if not col_name or not isinstance(col_name, str):
        return False
    name = col_name.strip().lower()

    # Exact or suffix ID check (e.g. "po_id", "id", "vendor_id")
    if name == "id" or name.endswith("_id") or name.startswith("id_"):
        return False

    # Check for fields that are already in USD
    if name.endswith("_usd") or name.startswith("usd_"):
        return False

    # Check for non-monetary keywords first (e.g. "ordered_quantity", "tax_rate", "variance_percent", "ratio")
    for term in NON_MONETARY_TERMS:
        if term in name:
            return False

    # Check for monetary keywords
    for term in MONETARY_TERMS:
        if term in name:
            return True

    return False


def _convert_row_monetary_values(row: dict, value_map: dict | None = None) -> dict:
    """
    Converts all monetary fields in a database row from INR to USD deterministically.
    Uses exact fixed conversion: USD = INR / 95.7.
    Preserves original non-monetary fields and explicit non-INR currencies.
    If value_map is provided, records raw -> converted mappings for safety.
    """
    if not isinstance(row, dict):
        return row

    row_currency = str(row.get("currency", "")).strip().upper()
    if row_currency and row_currency not in ("INR", "₹"):
        # Explicit non-INR currency provided by the database (Requirement 1)
        return row

    new_row = {}
    for k, v in row.items():
        if is_monetary_column(k) and v is not None:
            try:
                cleaned = str(v).replace(",", "").strip()
                num = float(cleaned)
                usd_val = round(num / INR_PER_USD, 2)
                new_row[k] = f"{usd_val:.2f}"
                if value_map is not None:
                    value_map[f"${num:,.2f}"] = f"${usd_val:,.2f}"
                    value_map[f"${num:,.0f}"] = f"${usd_val:,.2f}"
                    value_map[f"${cleaned}"] = f"${usd_val:,.2f}"
                    value_map[f"₹{num:,.2f}"] = f"${usd_val:,.2f}"
                    value_map[f"₹{num:,.0f}"] = f"${usd_val:,.2f}"
                    value_map[f"₹{cleaned}"] = f"${usd_val:,.2f}"
            except (ValueError, TypeError):
                new_row[k] = v
        else:
            new_row[k] = v

    if "currency" in new_row and str(new_row["currency"]).strip().upper() in ("INR", "₹"):
        new_row["currency"] = "USD"

    return new_row


def convert_tool_result_currency(tool_result_str: str, value_map: dict | None = None) -> str:
    """
    Inspects tool output from execute_sql / get_finance_data.
    Deterministically converts all database INR monetary values to USD using USD = INR / 95.7.
    Preserves non-monetary values (quantities, counts, dates, IDs, etc.).
    """
    if not tool_result_str or not isinstance(tool_result_str, str):
        return tool_result_str

    def _sub_array(match):
        raw_json = match.group(0)
        try:
            data = json.loads(raw_json)
            if isinstance(data, list):
                converted = [_convert_row_monetary_values(r, value_map=value_map) for r in data]
                return json.dumps(converted)
        except Exception:
            pass
        return raw_json

    def _sub_object(match):
        raw_json = match.group(0)
        try:
            data = json.loads(raw_json)
            if isinstance(data, dict):
                converted = _convert_row_monetary_values(data, value_map=value_map)
                return json.dumps(converted)
        except Exception:
            pass
        return raw_json

    def _process_text_content(content: str) -> str:
        # Convert JSON arrays of objects: [{"col": "val", ...}, ...]
        if re.search(r"\[\s*\{.*?\}\s*\]", content, flags=re.DOTALL):
            return re.sub(r"\[\s*\{.*?\}\s*\]", _sub_array, content, flags=re.DOTALL)
        # Convert single JSON objects if no array: {"col": "val", ...}
        elif re.search(r"\{\s*\"[^{}]*\"\s*:.*?\}", content, flags=re.DOTALL):
            return re.sub(r"\{\s*\"[^{}]*\"\s*:.*?\}", _sub_object, content, flags=re.DOTALL)
        return content

    try:
        outer = json.loads(tool_result_str)
        if isinstance(outer, dict) and "result" in outer and isinstance(outer["result"], str):
            outer["result"] = _process_text_content(outer["result"])
            return json.dumps(outer)
    except Exception:
        pass

    return _process_text_content(tool_result_str)


def _convert_inr_to_usd(amount_str: str, suffix: str = "", is_negative: bool = False) -> str:
    """
    Deterministically converts an INR monetary amount to formatted USD ($X.XX).
    Uses exact fixed conversion: USD = INR / 95.7.
    Preserves scale suffixes (K/M/B) where appropriate.
    """
    cleaned = amount_str.replace(",", "").strip()
    try:
        val = float(cleaned)
    except (ValueError, TypeError):
        return amount_str

    if is_negative:
        val = -abs(val)

    s = (suffix or "").strip().lower()
    multiplier = 1.0
    if s == "k":
        multiplier = 1_000.0
    elif s in ("m", "million", "millions"):
        multiplier = 1_000_000.0
    elif s in ("b", "billion", "billions"):
        multiplier = 1_000_000_000.0
    elif s in ("lakh", "lakhs", "lac", "lacs"):
        multiplier = 100_000.0
    elif s in ("crore", "crores", "cr"):
        multiplier = 10_000_000.0

    inr_val = val * multiplier
    usd_val = inr_val / INR_PER_USD

    prefix = "-" if usd_val < 0 else ""
    abs_usd = abs(usd_val)

    if s in ("m", "million", "millions") and abs_usd >= 1_000_000:
        return f"{prefix}${abs_usd / 1_000_000:,.2f}M"
    elif s in ("b", "billion", "billions") and abs_usd >= 1_000_000_000:
        return f"{prefix}${abs_usd / 1_000_000_000:,.2f}B"
    elif s in ("b", "billion", "billions") and abs_usd >= 1_000_000:
        return f"{prefix}${abs_usd / 1_000_000:,.2f}M"
    elif s == "k" and abs_usd >= 1_000:
        return f"{prefix}${abs_usd / 1_000:,.2f}K"
    else:
        return f"{prefix}${abs_usd:,.2f}"


def coordination_rule(question, result=None):
    question_text = (question or "").lower()
    result_text = str(result) if result is not None else ""

    converted_result = result_text

    # Prefix pattern: Currency symbol/code before amount (e.g. ₹143, INR 143, Rs. 143, Rupees 143)
    prefix_pattern = re.compile(
        r"(?<!\w)(?P<neg1>-)?\s*(?:₹|INR\b|Rs\.?\b|(?:Indian\s+Rupees?|Rupees?)\b)\s*(?P<neg2>-)?\s*"
        r"(?P<amount>[0-9][0-9,]*(?:\.[0-9]+)?)\s*"
        r"(?P<suffix>[KMBkmb]\b|lakhs?\b|crores?\b|cr\b|lacs?\b|billions?\b|millions?\b)?(?:\s*/-)?",
        flags=re.IGNORECASE,
    )

    def _prefix_sub(match):
        is_neg = bool(match.group("neg1") or match.group("neg2"))
        amount = match.group("amount")
        suffix = match.group("suffix") or ""
        return _convert_inr_to_usd(amount, suffix, is_negative=is_neg)

    converted_result = prefix_pattern.sub(_prefix_sub, converted_result)

    # Postfix pattern: Amount before currency symbol/code (e.g. 143 INR, 143 Rs., 143 rupees)
    postfix_pattern = re.compile(
        r"(?<![\$\w])(?P<neg>-)?\s*(?P<amount>[0-9][0-9,]*(?:\.[0-9]+)?)\s*"
        r"(?P<suffix>[KMBkmb]\b|lakhs?\b|crores?\b|cr\b|lacs?\b|billions?\b|millions?\b)?(?:\s*/-)?\s*"
        r"(?:₹|INR\b|Rs\.?\b|(?:Indian\s+Rupees?|Rupees?)\b)",
        flags=re.IGNORECASE,
    )

    def _postfix_sub(match):
        is_neg = bool(match.group("neg"))
        amount = match.group("amount")
        suffix = match.group("suffix") or ""
        return _convert_inr_to_usd(amount, suffix, is_negative=is_neg)

    converted_result = postfix_pattern.sub(_postfix_sub, converted_result)

    # Clean up standalone non-numeric currency terms (e.g. "(INR)" -> "(USD)", "in Rupees" -> "in USD")
    # Never simply replace them with '$'
    converted_result = re.sub(
        r"\b(?:INR|Rs\.?|Indian\s+Rupees?|Rupees?)\b",
        "USD",
        converted_result,
        flags=re.IGNORECASE,
    )
    converted_result = re.sub(r"₹", "USD", converted_result)

    return {
        "currency_conversion_required": True,
        "target_currency": "USD",
        "currency_reason": "MANDATORY USD CONVERSION: Converted from INR using fixed rate ₹95.7 = $1 USD (USD = INR / 95.7).",
        "output_format": "$ ONLY",
        "converted_result": converted_result,
    }
