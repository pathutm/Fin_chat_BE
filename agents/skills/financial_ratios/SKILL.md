---
name: financial-ratios
description: Calculates and explains financial ratios supportable from the CFO Analysis Industry Database. Use when the user asks for ratio interpretation based on documented tables, stored variance fields, or confirmed calculable inputs.
---

# Financial Ratios

Ratio calculation and factual interpretation rules for the Finance Agent. This skill covers **ratios only**. Use the financial-formulas skill for underlying calculations.

## Confirmed project context

- **Database:** CFO Analysis Industry Database (21 relational tables, read-only).
- **No ratio thresholds, benchmarks, or good/bad labels** are defined in project documentation. Interpretation must remain factual and descriptive only.
- **Do not add generic ratios** (debt-to-equity, ROE, ROA, quick ratio, inventory turnover, etc.) unless required inputs exist in documented tables for the requested scope.

## Ratio supportability

| State | Meaning |
|-------|---------|
| **Stored** | A ratio or metric column is returned directly from the database. |
| **Calculated** | Required inputs exist in query results and the ratio is derived using documented formulas. |
| **Unavailable** | Required inputs are not documented in the CFO schema; do not calculate or guess. |

---

## Supported ratios

### Current Ratio

| Item | Detail |
|------|--------|
| **Formula** | `Current Ratio = Current Assets ÷ Current Liabilities` |
| **Required inputs** | Current Assets total; Current Liabilities total. |
| **Confirmed source fields/tables** | **Not mapped** to documented columns in the 21-table CFO schema. |
| **Supportability** | **Unavailable** for database-backed answers unless query results contain explicit current-asset and current-liability totals for the requested scope. |
| **What it measures** | Ability to cover short-term obligations with short-term assets. |
| **Interpretation** | When calculable, state the value and meaning factually (e.g., "Current assets are 1.5 times current liabilities for [scope]."). Do not label as good, bad, healthy, or weak. |
| **Zero denominator** | If Current Liabilities = 0, ratio is unavailable. |
| **Precision** | Unitless ratio to 2 decimal places (e.g., 1.50), not a percentage. |

When unavailable, direct conceptual explanations to the General Agent; do not invent balance-sheet figures.

### Working Capital (absolute liquidity metric)

Not a ratio, but commonly paired with Current Ratio.

| Item | Detail |
|------|--------|
| **Formula** | `Working Capital = Current Assets − Current Liabilities` |
| **Required inputs** | Current Assets; Current Liabilities. |
| **Confirmed source fields/tables** | **Not mapped** to documented columns in the 21-table CFO schema. |
| **Supportability** | **Unavailable** for database-backed answers unless both inputs exist in query results. |
| **What it measures** | Net short-term resource cushion after current liabilities. |
| **Interpretation** | State the amount and scope factually. Positive = assets exceed liabilities by that amount; negative = liabilities exceed assets. No normative judgment. |
| **Precision** | Currency, 2 decimal places. |

---

## Procurement variance metrics (documented, not generic ratios)

These are **documented CFO database metrics** on `supplier_invoice_line`. Treat as stored reconciliation indicators, not generic financial ratios:

| Metric | Source | Meaning |
|--------|--------|---------|
| `variance_quantity` | `supplier_invoice_line` | Stored quantity variance from 3-way matching |
| `variance_amount` | `supplier_invoice_line` | Stored amount variance from 3-way matching |
| `matching_status` | `supplier_invoice_line` | Stored line-level match status |

When presenting these, describe what the stored field represents. Do not recalculate if the stored value is authoritative for the line. Full matching logic is in the procurement-reconciliation skill.

### Tax rate on invoice lines

| Item | Detail |
|------|--------|
| **Field** | `tax_percent` on `supplier_invoice_line` |
| **Supportability** | **Stored** — report directly when the question asks for invoice-line tax rate. |
| **Interpretation** | State the percentage applied on the line; do not infer tax policy beyond the stored value. |

---

## Calculation workflow

1. Identify the ratio or metric requested and the scope.
2. Check for a **stored** value in documented columns.
3. If not stored, verify required inputs exist in query results.
4. If inputs are missing, classify as **Unavailable** and list what is missing.
5. If inputs exist, compute using financial-formulas rules.
6. Interpret factually — describe what the number means, not whether it is desirable.

## Handling comparisons

- Use the same definition and input sources for each comparison point.
- Note scope differences (period, product, vendor, document) factually.
- Do not attribute causes unless supported by query data.

## Percentage vs ratio

- **Current Ratio** is a unitless decimal ratio, not multiplied by 100.
- **`tax_percent`** is a stored percentage on invoice lines — present with a `%` suffix.
- Do not convert formats unless the storage convention is visible in query results.

## Out of scope

- Underlying input aggregation (financial-formulas skill).
- Procurement trace and 3-way match workflow (procurement-reconciliation skill).
- SQL, MCP, routing, or response formatting.
