---
name: procurement-reconciliation
description: Defines procurement, purchase order, goods receipt, supplier invoice, and reconciliation analysis methods.
---

# Procurement Reconciliation Skill

## Purpose

Apply consistent methods for purchase order, goods receipt, supplier invoice, and reconciliation analysis.

## Core Rules

- Use only retrieved database values or user-provided values.
- Use confirmed database relationships for joins.
- Do not invent missing procurement records.
- Do not perform write or destructive operations.
- Use read-only data for all analysis.
- Keep PO, GRN, and invoice quantities clearly separated.

## Purchase Order Analysis

For purchase orders, use:

- Ordered Quantity
- Unit Price
- PO Date
- Expected Delivery Date
- Payment Terms
- PO Status

Purchase Order Amount:

`Ordered Quantity × Unit Price`

Use `purchase_order_line.ordered_quantity` and `purchase_order_line.unit_price`.

## Goods Receipt Analysis

For goods receipts, use:

- Delivered Quantity
- Damaged Quantity
- Rejected Quantity
- Accepted Quantity
- Remaining PO Quantity

Acceptance Rate:

`Accepted Quantity / Delivered Quantity × 100`

Rejection Rate:

`Rejected Quantity / Delivered Quantity × 100`

If delivered quantity is zero, do not calculate the percentage.

## Supplier Invoice Analysis

For invoice-level analysis, use:

- Invoice Amount
- Invoice Quantity
- Tax
- Freight Amount
- Discount Amount
- Payment Due Date
- Payment Terms

For invoice-line analysis, use:

- Invoice Quantity
- Unit Price
- Line Amount

Use `supplier_invoice.invoice_amount` for invoice-level amount.

Use `supplier_invoice_line.line_amount` for invoice-line amount.

## PO vs Invoice Comparison & Metric Integrity
 
 Compare:
 
 - PO Quantity
 - Invoice Quantity
 - PO Unit Price
 - Invoice Unit Price
 - PO Amount vs. Invoice Amount
 
 Quantity Difference:
 
 `PO Quantity − Invoice Quantity`
 
 Unit Price Difference:
 
 `Invoice Unit Price − PO Unit Price`
 
 Amount Difference:
 
 `PO Amount − Invoice Amount`
 
 ### Critical Reconciliation Safeguards:
 - **Amount Difference is NOT Savings**: Never label `PO Amount − Invoice Amount` as "savings". It is a billing difference or reconciliation variance.
 - **Mismatches are Not Fraud or Overcharging**: A mismatch in quantity or price does NOT automatically imply supplier manipulation, fraud, or overcharging.
 - **No Invented Root Causes**: If the underlying cause of a mismatch or failed reconciliation is not documented in the database, explicitly state: "The available data shows the mismatch, but the underlying reason cannot be determined from the available records."
 - Do not treat differences as errors unless the data or user request supports that interpretation.

## Three-Way Matching

Compare:

1. Purchase Order
2. Goods Receipt Note
3. Supplier Invoice

Key fields:

- PO Quantity
- GRN Accepted Quantity
- Invoice Quantity
- Unit Price
- Tax

Use the `reconciliation` table when reconciliation results are already available.

## Reconciliation Analysis

Use:

- Vendor Match
- Product Match
- Unit Price Match
- Tax Match
- Reconciliation Status
- PO Quantity
- GRN Accepted Quantity
- Invoice Quantity
- Invoice Amount

For failed reconciliation analysis, filter using the recorded `reconciliation_status`.

## Procurement Mismatch Analysis

Identify differences between:

- Ordered Quantity and Accepted Quantity
- Accepted Quantity and Invoice Quantity
- PO Unit Price and Invoice Unit Price
- PO and Invoice tax information
- Vendor matching information
- Product matching information

Do not assume a mismatch is an error without supporting data.

## Vendor Procurement Analysis

When analyzing vendors:

- Use purchase orders for purchase volume.
- Use supplier invoices for invoice amounts.
- Use goods receipt notes for received quantities.
- Use reconciliation for matching performance.

Keep these metrics separate.

## Overdue Purchase Orders

For overdue PO analysis:

- Use `expected_delivery_date`.
- Compare it with the relevant reference date.
- Consider `po_status` when interpreting the result.
- Do not mark completed or closed orders as overdue solely based on date.

## Overdue Invoices

For overdue invoice analysis:

- Use `payment_due_date`.
- Compare it with the relevant reference date.
- Use invoice/payment status only when available.
- Do not assume an invoice is overdue without a valid date comparison.

## Procurement Trend Analysis

For monthly procurement trends:

- Group records by the relevant date.
- Keep chronological order.
- Report quantities and monetary values separately.
- Do not treat missing months as zero.

## Error Handling

- If no matching procurement records exist, report that no matching records were found.
- If a required field is missing, do not invent it.
- If a query fails because of an unknown field, do not guess another field.
- If database connectivity or permission fails, stop and report the technical issue.
- Do not perform repeated trial-and-error queries.

## Response Requirements

- Clearly identify whether the result comes from PO, GRN, invoice, or reconciliation data.
- Show quantities with their units.
- Show monetary values with the appropriate currency.
- Clearly identify mismatches and calculated differences.
- Keep results traceable to retrieved database values.