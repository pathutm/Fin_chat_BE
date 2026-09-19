---

name: procurement-analytics
description: Analyzes procurement-related finance questions using actual CFO database results. Use for purchase orders, purchase order lines, vendors, goods receipt notes, supplier invoices, invoice lines, procurement amounts, quantities, and procurement document relationships. Does not generate SQL, access MCP, or invent data.
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Procurement Analytics

Analyze procurement-related finance questions using the CFO database structure and actual retrieved results.

## Procurement Tables

Primary procurement tables include:

* `purchase_order`
* `purchase_order_line`
* `vendor`
* `goods_receipt_note`
* `goods_receipt_note_line`
* `supplier_invoice`
* `supplier_invoice_line`
* `reconciliation`

## Procurement Flow

```text
Purchase Order
→ Purchase Order Line
→ Vendor
→ Goods Receipt Note
→ GRN Line
→ Supplier Invoice
→ Invoice Line
→ Reconciliation
```

Related production flow:

```text
Customer Order
→ Production Order
→ BOM
→ Purchase Order
```

## Purchase Order Analysis

Support analysis of:

* Purchase order amounts
* Purchase order dates
* Purchase order status
* Vendor purchase orders
* Expected delivery
* Procurement trends
* Procurement comparisons
* Procurement rankings

Use only fields returned by the database.

## Purchase Order Line Analysis

Support:

* Ordered quantity
* Unit price
* PO line value

A line value may be calculated as:

```text
ordered quantity × unit price
```

Only calculate when both inputs are available, and clearly identify the result as calculated.

## Vendor Analysis

Support:

* Purchase order amount
* Invoice amount
* Purchase order count
* Vendor comparisons
* Vendor rankings

Vendor analysis can be combined with comparison, ranking, and time-series analytics.

## Goods Receipt Analysis

Support:

* Received quantities
* Accepted quantities
* GRN details
* PO-to-GRN relationships
* Partial receipts
* Receipt variances

Do not treat ordered, received, accepted, and invoiced quantities as interchangeable.

## Supplier Invoice Analysis

Relevant fields include:

* `invoice_id`
* `grn_id`
* `po_id`
* `vendor_id`
* `invoice_date`
* `invoice_number`
* `invoice_quantity`
* `tax`
* `freight_amount`
* `discount_amount`
* `invoice_amount`
* `payment_due_date`
* `payment_terms`

Support invoice amount, quantity, vendor, date, payment terms, and related procurement analysis.

## Supplier Invoice Line Analysis

Support:

* Invoiced quantity
* Unit price
* Variance quantity
* Variance amount
* Tax percentage when returned

A line value may be calculated as:

```text
invoiced quantity × unit price
```

Only calculate when the required values are available.

## Procurement Amounts

Identify the document level before analyzing amounts.

Do not substitute:

* Invoice amount for PO amount
* PO amount for invoice amount
* Line amount for document amount

Use the actual stored value or clearly identify calculated values.

## Procurement Quantities

Keep these quantities distinct:

* Ordered quantity
* Received quantity
* Accepted quantity
* Invoiced quantity

Do not assume they are equal.

## Reconciliation

Use available relationships between:

```text
Purchase Order
→ Goods Receipt Note
→ Supplier Invoice
→ Reconciliation
```

When available, use stored fields such as:

* `matching_status`
* `matched_quantity`
* `variance_quantity`
* `variance_amount`

If a required document or relationship is missing, report the missing information rather than inventing it.

## Combined Analysis

Procurement Analytics can be combined with:

* Time-Series Analytics for procurement trends.
* Comparison Analytics for vendor or procurement comparisons.
* Ranking Analytics for top or bottom vendors.
* Visualization Intent for presentation selection.

## Missing Data

* Use only returned database values.
* Report missing or incomplete procurement data.
* Never fabricate procurement records, amounts, quantities, dates, or relationships.
* Do not assume undocumented fields.

## Boundaries

| Responsibility         | Owner                 |
| ---------------------- | --------------------- |
| Procurement analysis   | procurement-analytics |
| Intent detection       | visualization-intent  |
| Time analysis          | time-series-analytics |
| Comparison             | comparison-analytics  |
| Ranking                | ranking-analytics     |
| SQL / database queries | Finance Agent         |
| MCP / Supabase         | MCP client            |
| Final formatting       | finance-response      |
| Rendering              | Frontend              |

This skill provides procurement-domain analysis only. Do not generate SQL, call MCP, access Supabase directly, fabricate data, or modify source data.
