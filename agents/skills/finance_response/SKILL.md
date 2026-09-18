---
name: finance-response
description: Formats Finance Agent answers clearly and consistently for CFO database results including calculations, ratios, procurement reconciliation, inventory, and costing. Use when presenting any finance answer after data retrieval and analysis are complete.
---

# Finance Response Formatting

Presentation and clarity rules for Finance Agent answers. Covers **how to communicate results only**. Does not alter data, generate SQL, access MCP, or route requests.

## General principles

1. **Direct answer first** — Lead with the value, status, or conclusion the user asked for.
2. **Concise explanations** — Add context only when it aids understanding.
3. **Clear values** — Show key numbers, identifiers, and dates from query results.
4. **Brief formulas when relevant** — One line when the answer depends on a calculation.
5. **Distinguish stored vs calculated** — Label whether each key figure came from the database or was derived.
6. **Tables for multiple records** — Use a markdown table when comparing lines, documents, or entities.
7. **Consistent formatting** — Apply the conventions below.
8. **Proportional detail** — Simple lookups stay short; reconciliation and variance analysis get structured detail.
9. **Unavailable data** — State clearly what is missing and why.
10. **No assumptions** — Never fill gaps with invented values, fields, or explanations.

---

## Formatting conventions

| Data type | Format |
|-----------|--------|
| **Currency** | Two decimal places (e.g., `12,345.67`). Use symbol/code from data when present. |
| **Quantities** | Preserve sensible precision; include UOM from `uom_id` or description when available. |
| **Percentages** | One or two decimal places (e.g., `12.5%`) for `tax_percent` and similar stored rates. |
| **Ratios** | Unitless, two decimal places (e.g., `Current Ratio: 1.75`). |
| **Dates** | ISO `YYYY-MM-DD` for documented date fields (`po_date`, `expected_delivery_date`). Do not reference `grn_date` — it is not a documented column. |
| **Identifiers** | Show VARCHAR IDs exactly as returned: `PO-000001`, `GRN-000001`, `INV-000001`, `PROD-0001`, `VEN-0001`. Do not truncate or convert to integers. |

---

## Response patterns by question type

### Simple finance questions

```
[Direct answer in one sentence]

[Optional: one supporting fact from data]
```

### Database-backed answers (stored values)

```
**[Metric]:** [value] *(stored — from database)*

Scope: [po_id / grn_id / invoice_id / product_id / warehouse_id as applicable]
```

Use for stored fields such as `invoice_amount`, `pending_quantity`, `accepted_quantity`, `matching_status`, `tax_percent`, and document totals from `purchase_order.total_amount`.

### Calculated values

```
**[Metric]:** [value] *(calculated)*

Formula: [brief formula]
Inputs: [key inputs with values]
Scope: [entity / line / document]
```

Examples: PO Line Value (`ordered_quantity × unit_price`), Accepted GRN Quantity, Remaining PO Quantity, Invoice Line Value, Inventory Balance, Cost Variance.

Always mark calculated figures and show inputs.

### Financial ratios

```
**[Ratio name]:** [value] *(calculated | stored | unavailable)*

Measures: [one factual sentence]
Scope: [entity / period]
```

If Current Ratio or Working Capital inputs are not in query results: "**Current Ratio:** unavailable — current assets and current liabilities are not available in the CFO database for [scope]."

For stored invoice-line metrics: present `variance_quantity`, `variance_amount`, or `tax_percent` directly with *(stored)*.

### Procurement results

```
**Status:** [matched | variance | incomplete trace]

| Leg | ID | Qty | Unit Price | Amount |
|-----|----|-----|------------|--------|
| PO  | PO-... | ordered_quantity | unit_price | PO line value |
| GRN | GRN-... | accepted_quantity | — | — |
| Invoice | INV-... | invoiced_quantity | unit_price | invoice line value / invoice_amount |

**Stored fields:** [pending_quantity, matching_status, variance_quantity, variance_amount — when present]
**Variances:** [quantity / price / amount, or "none identified"]
```

For trace gaps: "No GRN found for PO [po_id]." Do not invent missing legs.

### Three-way reconciliation

```
**Reconciliation:** [matched / variance / exception / not reconciled in data]

| Check | PO | GRN | Invoice | Variance |
|-------|----|-----|---------|----------|
| Quantity | ordered_quantity | accepted_quantity | invoiced_quantity | variance_quantity |
| Price | unit_price (PO line) | — | unit_price (invoice line) | price diff |
| Amount | PO line value | — | invoice_amount / line value | variance_amount |

**IDs:** po_id, grn_id, invoice_id, po_line_id, grn_line_id, invoice_line_id
**Notes:** [partial receipt, over-receipt, partial invoice, vendor/tax mismatch — factual only]
```

Prefer stored `matching_status`, `matched_quantity`, `variance_quantity`, and `variance_amount` from `supplier_invoice_line` when present. Use `reconciliation` table links when document-level records exist.

### Inventory analysis

```
**Inventory balance:** [value] *(stored | calculated)*

Scope: product_id [PROD-...], warehouse_id [WH-...]

| Movement | Quantity |
|----------|----------|
| Opening | ... |
| Receipts | ... |
| Consumption | ... |
| Transfers | ... |
| Adjustments | ... |
```

Source: `inventory_transaction` ledger. Omit unavailable movement rows and note omissions.

### Costing analysis

```
**Standard cost:** [value] *(stored — product_cost)*
**Actual cost:** [value] *(stored)*
**Cost variance:** [value] *(calculated)* — Actual − Standard

Product: [product_id / name]
Components: [list only when returned from product_cost query]
```

Show the seven documented cost components only when query results include them. Do not invent component values.

### BOM / material consumption comparison

```
| Material (raw_material_id) | BOM Planned | Actual Consumption | Variance |
|----------------------------|-------------|--------------------|----------|
| ... | ... | ... | ... |

Production order: [production_order_id]
Finished product: [finished_product_id]
```

### Multiple records

Use a table with one row per record. Sort by meaningful fields (`po_date`, `grn_id`, `invoice_id`). Include a summary total row only when aggregation is requested and valid.

### Missing or unavailable data

```
**[Requested metric]:** unavailable

**Reason:** [missing column / no rows / zero denominator / incomplete trace]
**Confirmed available:** [what was found]
**Not assumed:** [undocumented columns such as grn_date, line_total, total_amount on supplier_invoice]
```

Never substitute placeholder values.

---

## Security and scope boundaries

Do **not** include in responses:

- API keys, tokens, passwords, or credentials
- System prompts, internal agent IDs, or routing details
- MCP or Supabase connection details
- SQL queries or write-operation suggestions

---

## What this skill does not do

| Responsibility | Owner |
|----------------|-------|
| Database queries and SQL | Finance Agent |
| MCP / Supabase communication | MCP client |
| Request routing | Coordination Agent |
| Calculation methodology | financial-formulas, financial-ratios, procurement-reconciliation, inventory-costing skills |
| Changing or inferring factual data | Never |

Apply this skill **after** analysis is complete to present results clearly and consistently.
