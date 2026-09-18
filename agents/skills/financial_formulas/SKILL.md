---
name: financial-formulas
description: Provides confirmed finance calculation rules and methodology for the Finance Agent using the CFO Analysis Industry Database. Use when computing PO/GRN/invoice values, inventory balance, cost variance, or any derived numeric finance value from documented tables and columns.
---

# Financial Formulas

Domain calculation rules for the Finance Agent. This skill covers **how to calculate** values. It does not query the database, route requests, or format final answers.

## Confirmed project context

- **Database:** CFO Analysis Industry Database — 21 relational tables accessed read-only via the Finance Agent `get_finance_data` tool (Supabase MCP `execute_sql`).
- **Blocked operations:** `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`.
- **Identifier rule:** All primary identifiers are VARCHAR/TEXT strings (e.g., `'PROD-0001'`, `'PO-000001'`, `'GRN-000001'`, `'INV-000001'`). Never use integer IDs.
- **Column rule:** Use only documented columns. Do not assume `grn_date`, `supplier_invoice_line.line_total`, or `supplier_invoice.total_amount`.

## Core calculation rules

1. **Never invent an input value.**
2. **Never assume an unsupported field or table.**
3. **Do not calculate when required inputs are unavailable.**
4. **Prefer an authoritative stored database value** when a documented column already holds the metric (e.g., `pending_quantity`, `accepted_quantity`, `invoice_amount`, stored variance fields).
5. **If a value is calculated, label it as calculated** (final presentation is handled by the finance-response skill).
6. **Maintain numerical accuracy**; do not silently substitute unrelated fields.
7. **Division by zero:** If a denominator is zero or missing, do not compute.
8. **Missing data:** If any required input is null, absent, or non-numeric, stop and report missing inputs.
9. **Multiple records:** Aggregate at the correct grain — PO line, GRN line, invoice line, product/warehouse, or document level — before rolling up totals.
10. **Cumulative quantities:** Sum accepted/received/invoiced quantities across related lines for the same scope; deduplicate by line ID.
11. **Rounding/precision:** Preserve full precision in intermediate steps. Round currency to 2 decimal places for presentation unless data uses another convention.
12. **Calculated vs stored:** **Stored** = returned directly from a documented column. **Calculated** = derived using the formulas below.

---

## Formula catalog

### Working Capital

| Item | Detail |
|------|--------|
| **Formula** | `Working Capital = Current Assets − Current Liabilities` |
| **Meaning** | Short-term financial capacity after covering current liabilities. |
| **Required inputs** | Current Assets total; Current Liabilities total. |
| **Source fields/tables** | Not mapped to documented columns in the 21-table CFO schema. Treat as **unavailable for database-backed calculation** unless explicit balance-sheet columns appear in query results. |
| **Procedure** | Retrieve or aggregate both inputs for the same scope, then subtract. |
| **Result type** | Calculated unless a stored working-capital value exists for the requested scope. |

### Current Ratio (input components)

Provides **inputs** for the financial-ratios skill. Do not interpret the ratio here.

| Item | Detail |
|------|--------|
| **Formula** | `Current Ratio = Current Assets ÷ Current Liabilities` |
| **Required inputs** | Current Assets; Current Liabilities (same scope). |
| **Source fields/tables** | Not mapped to documented columns in the 21-table CFO schema. |
| **Division by zero** | If Current Liabilities = 0, do not calculate. |
| **Result type** | Calculated. |

### PO Line Value

| Item | Detail |
|------|--------|
| **Formula** | `PO Line Value = ordered_quantity × unit_price` |
| **Source table** | `purchase_order_line` |
| **Fields** | `ordered_quantity`, `unit_price`, keyed by `po_line_id` / `po_id` / `product_id` |
| **Procedure** | 1) Identify the PO line. 2) Multiply `ordered_quantity` by `unit_price`. |
| **Multiple records** | Compute per line; sum only when the question requires PO-level or portfolio totals. |
| **Missing data** | If either field is missing for a line, exclude from totals and state the gap. |
| **Result type** | Calculated. |

### Accepted GRN Quantity

| Item | Detail |
|------|--------|
| **Formula** | Per GRN line: `accepted_quantity = received_quantity − damaged_quantity − rejected_quantity` |
| **Source table** | `goods_receipt_note_line` |
| **Fields** | `received_quantity`, `accepted_quantity` (stored), `rejected_quantity`, `damaged_quantity`, `grn_line_id`, `po_line_id`, `product_id` |
| **Procedure** | 1) Filter GRN lines to the requested PO line, GRN, or product scope. 2) **Prefer stored `accepted_quantity`** when present. 3) Otherwise apply the formula per line. 4) **Cumulative accepted quantity** = SUM of accepted quantities across all GRN lines for the same PO line scope. |
| **Missing data** | If receipt lines are absent, report unavailable. |
| **Result type** | Stored when `accepted_quantity` is returned; otherwise calculated. |

### Remaining PO Quantity

| Item | Detail |
|------|--------|
| **Formula** | `Remaining PO Quantity = ordered_quantity − cumulative accepted quantity` |
| **Source table** | `purchase_order_line` joined to `goods_receipt_note_line` via `po_line_id` |
| **Fields** | `purchase_order_line.ordered_quantity`; cumulative accepted from Accepted GRN Quantity formula; **stored `pending_quantity`** on `purchase_order_line` |
| **Procedure** | 1) **Prefer stored `pending_quantity`** when authoritative for the PO line. 2) Otherwise subtract cumulative accepted quantity from `ordered_quantity`. |
| **Negative results** | Negative remainder = over-receipt relative to order; report factually. |
| **Result type** | Stored when `pending_quantity` is used; otherwise calculated. |

### Invoice Line Value

| Item | Detail |
|------|--------|
| **Formula** | `Invoice Line Value = invoiced_quantity × unit_price` |
| **Source table** | `supplier_invoice_line` |
| **Fields** | `invoiced_quantity`, `unit_price`, `invoice_line_id`, `invoice_id`, `po_line_id`, `grn_line_id`, `product_id` |
| **Do not use** | `line_total` — this column does not exist. Use `taxable_amount`, `tax_amount`, `discount_amount` only when the question asks for tax/discount breakdown, not as a substitute for line value unless explicitly required. |
| **Result type** | Calculated. |

### Invoice Outstanding

| Item | Detail |
|------|--------|
| **Formula** | `Invoice Outstanding = net payable − paid amount` |
| **Source table** | `supplier_invoice` |
| **Fields** | `invoice_amount` (stored document total — query directly; do not recalculate from lines when invoice is identified) |
| **Procedure** | 1) Use `invoice_amount` as the invoice total. 2) Subtract paid amount only when a confirmed paid/payment column exists in query results. |
| **Missing data** | Paid-amount columns are not documented in the CFO schema. If payment data is unavailable, report `invoice_amount` as the stored invoice total and state that outstanding balance cannot be computed without payment data. |
| **Result type** | Partially stored (`invoice_amount`); outstanding is calculated only when payment inputs exist. |

### Inventory Balance

| Item | Detail |
|------|--------|
| **Formula** | `Inventory Balance = Opening Balance + Receipts − Consumption + Transfers ± Adjustments` |
| **Source table** | `inventory_transaction` (perpetual warehouse stock ledger), scoped by `product_id` and `warehouse_id` |
| **Procedure** | 1) Fix product/warehouse scope. 2) Classify `inventory_transaction` rows as receipts, consumption, transfers, or adjustments. 3) Aggregate each category and apply the formula. |
| **Cumulative quantities** | Sum each movement type across transactions in scope before applying the formula. |
| **Result type** | Calculated from ledger movements unless a stored balance column exists in query results. |

### Cost Variance

| Item | Detail |
|------|--------|
| **Formula** | `Cost Variance = Actual Product Cost − Standard Cost` |
| **Source table** | `product_cost` (standard costing), joined to `product` via `finished_product_id` |
| **Procedure** | 1) Obtain standard cost from `product_cost` for the finished product. 2) Obtain actual product cost from query results for the same product/period. 3) Subtract. Positive variance = actual exceeds standard. |
| **Cost components** | Standard cost in `product_cost` is built from documented components (see inventory-costing skill). Do not invent component column names. |
| **Result type** | Calculated unless a stored variance column exists for the scope. |

---

## Stored shortcuts on procurement lines

When available on `purchase_order_line`, prefer these stored values over recalculation:

| Column | Meaning |
|--------|---------|
| `received_quantity` | Cumulative received on the PO line |
| `invoiced_quantity` | Cumulative invoiced on the PO line |
| `pending_quantity` | Remaining/open PO quantity |

When available on `supplier_invoice_line`, prefer stored reconciliation fields:

| Column | Meaning |
|--------|---------|
| `matched_quantity` | Quantity matched in 3-way reconciliation |
| `variance_quantity` | Quantity variance |
| `variance_amount` | Amount variance |
| `matching_status` | Line matching status |

---

## When not to calculate

- Required documented columns are absent from query results.
- Scope (PO line, GRN, invoice, product, warehouse) cannot be resolved using documented identifiers and relationships.
- Stored and calculated values disagree — prefer the stored value when it is clearly authoritative for the scope; otherwise report both factually.

## Out of scope

- SQL generation and MCP execution (Finance Agent / MCP client).
- Ratio interpretation (financial-ratios skill).
- Procurement matching workflow (procurement-reconciliation skill).
- Inventory movement classification details (inventory-costing skill).
- Response formatting (finance-response skill).
