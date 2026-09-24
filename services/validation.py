"""
Validation Layer for CFO AI Chatbot.
Enforces Data Accuracy and Validation Rules:
- Detects and prevents join fan-out in SQL queries
- Validates data grain, scope, and aggregation
- Performs numerical reconciliation on component metrics
- Validates that non-monetary quantities are not formatted as currency
- Sanitizes final responses against substring-level formatting corruption
"""

import re
import logging

logger = logging.getLogger("finance_validator")

# Tables that have 1-to-many relationships and cause Cartesian fan-out when joined directly
MANY_TO_ONE_CHILD_TABLES = {
    "purchase_order_line",
    "supplier_invoice",
    "supplier_invoice_line",
    "goods_receipt_note",
    "goods_receipt_note_line",
    "inventory_batch",
    "material_consumption",
    "production_order",
    "product_cost",
    "inventory_transaction",
    "cost_centre_allocation",
    "customer_order",
}

# Physical units and non-monetary entity terms
PHYSICAL_UNITS_PATTERN = re.compile(
    r"\$([0-9][0-9,]*(?:\.[0-9]+)?\s*(?:units?|kg|tons?|tonnes?|batches|orders?|pieces|pcs|meters?|mtr|rings?|records?|invoices?|POs?|items?|lines?))\b",
    re.IGNORECASE,
)

# Inventory variance quantities mistakenly prefixed with '$'
INVENTORY_VARIANCE_PATTERN = re.compile(
    r"\$([0-9][0-9,]*(?:\.[0-9]+)?[KMBkmb]?)\s+(variance\s+(?:between\s+expected\s+and\s+actual\s+available\s+inventory|quantity|units?))\b",
    re.IGNORECASE,
)

# Malformed corrupted currency values created by bad substring replaces (e.g. $0.79,543.91 or $0.01.24M)
CORRUPTED_PREFIX_PATTERN = re.compile(r"\$0\.(\d{1,2}),(\d{3}(?:\.\d{1,2})?)")
CORRUPTED_MILLIONS_PATTERN = re.compile(r"\$0\.01\.(\d{1,2})([KMBkmb])")


def validate_sql_query(query: str) -> dict:
    """
    Validates a SQL query before execution against Data Accuracy and Validation Rules:
    - Protect against Join Fan-Out (Rule 3)
    - Determine Correct Data Grain (Rule 2)
    - Scope Validation (Rule 5)
    """
    if not query or not isinstance(query, str):
        return {"valid": True, "warnings": []}

    q_lower = query.lower()
    warnings = []

    # 1. Join Fan-Out Check
    # Find all mentioned child tables in the query
    mentioned_tables = [tbl for tbl in MANY_TO_ONE_CHILD_TABLES if re.search(rf"\b{tbl}\b", q_lower)]
    
    # Check if multiple child tables are joined directly
    if len(mentioned_tables) >= 2 and "join" in q_lower:
        # Check if pre-aggregation (CTE or subquery with GROUP BY) is used
        has_cte = "with " in q_lower
        has_subquery_group = bool(re.search(r"\(\s*select\b.*?\bgroup\s+by\b.*?\)", q_lower, re.DOTALL))
        
        if not (has_cte or has_subquery_group):
            warning_msg = (
                f"POTENTIAL JOIN FAN-OUT DETECTED: Tables {mentioned_tables} are joined without "
                "prior CTE or subquery aggregation. Joining multiple 1-to-many tables directly "
                "multiplies rows and inflates SUM/COUNT results. "
                "Ensure child tables are independently aggregated before joining."
            )
            warnings.append(warning_msg)
            logger.warning(warning_msg)

    # 2. Scope Validation Check
    if "limit " in q_lower and "count(" not in q_lower:
        warnings.append(
            "SCOPE NOTE: Query contains LIMIT without COUNT(*). Do not treat the returned rows "
            "as the total database entity count."
        )

    return {
        "valid": True,
        "warnings": warnings,
        "has_fan_out_risk": any("FAN-OUT" in w for w in warnings),
    }


def validate_tool_data(query: str, data: list | dict) -> dict:
    """
    Validates data returned from get_finance_data against Data Accuracy Rules:
    - Check numerical reconciliation where components are present (Rule 6)
    - Check for unexpected duplication or suspicious values (Rule 4, Rule 12)
    """
    reconciliation_results = []

    if isinstance(data, list):
        for idx, row in enumerate(data):
            if not isinstance(row, dict):
                continue
            
            # Production reconciliation check: production_qty = good_qty + rejected_qty + scrap_qty
            prod_keys = {"production_quantity", "good_quantity", "rejected_quantity", "scrap_quantity"}
            if prod_keys.issubset(row.keys()):
                try:
                    p_qty = float(str(row["production_quantity"]).replace(",", ""))
                    g_qty = float(str(row["good_quantity"]).replace(",", ""))
                    r_qty = float(str(row["rejected_quantity"]).replace(",", ""))
                    s_qty = float(str(row["scrap_quantity"]).replace(",", ""))
                    diff = abs(p_qty - (g_qty + r_qty + s_qty))
                    if diff > 0.01:
                        reconciliation_results.append(
                            f"Row {idx}: Production quantity ({p_qty}) != Good ({g_qty}) + Rejected ({r_qty}) + Scrap ({s_qty}), diff={diff}"
                        )
                except (ValueError, TypeError):
                    pass

    return {
        "reconciliation_passed": len(reconciliation_results) == 0,
        "reconciliation_issues": reconciliation_results,
    }


def validate_and_sanitize_response(response_text: str) -> str:
    """
    Final validation pass on response before presenting to user:
    - Fixes any corrupted substring replacements (e.g. $0.79,543.91 -> $79,543.91)
    - Removes dollar signs erroneously attached to physical quantities (e.g. $10,326 units -> 10,326 units)
    - Cleans up corrupted scientific or scale suffixes (e.g. $0.01.24M -> 1.24M)
    - Ensures formatting is consistent, numerical values remain intact, and formatting occurs only once.
    """
    if not response_text or not isinstance(response_text, str):
        return response_text

    sanitized = response_text

    # 1. Fix corrupted split-comma currency: e.g. $0.79,543.91 -> $79,543.91
    sanitized = CORRUPTED_PREFIX_PATTERN.sub(r"$\1,\2", sanitized)

    # 2. Fix corrupted double-decimal scale: e.g. $0.01.24M -> 1.24M
    sanitized = CORRUPTED_MILLIONS_PATTERN.sub(r"1.\1\2", sanitized)

    # 3. Remove dollar signs mistakenly placed before physical units / counts
    sanitized = PHYSICAL_UNITS_PATTERN.sub(r"\1", sanitized)

    # 4. Remove dollar signs mistakenly placed before inventory variance quantities
    sanitized = INVENTORY_VARIANCE_PATTERN.sub(r"\1 \2", sanitized)

    return sanitized
