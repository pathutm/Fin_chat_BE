---

name: procurement-analytics
description: Defines methods for analyzing procurement performance, purchasing activity, supplier performance, purchase orders, receipts, invoices, and procurement trends.
---

# Procurement Analytics Skill

## Purpose

Analyze procurement performance using retrieved purchase order, goods receipt, supplier invoice, vendor, and reconciliation data.

## Core Rules

- Use only retrieved database values or user-provided values.
- Use confirmed database relationships.
- Do not invent procurement values.
- Do not assume missing values are zero.
- Keep quantities, prices, and monetary amounts clearly separated.
- Use consistent time periods and units.

## Purchase Analysis

Analyze:

- Purchase Order Count
- Ordered Quantity
- Purchase Order Amount
- Average Unit Price
- Expected Delivery Date
- Purchase Order Status

Purchase Order Amount:

`Ordered Quantity × Unit Price`

Use `purchase_order_line.ordered_quantity` and `purchase_order_line.unit_price`.

## Supplier Performance

Analyze vendors using:

- Purchase Quantity
- Purchase Order Amount
- Invoice Amount
- Received Quantity
- Rejected Quantity
- Reconciliation Status

Keep supplier metrics based on the appropriate source table.

## Purchase Volume

Purchase Volume can be measured using:

- Total Ordered Quantity
- Total Purchase Order Amount
- Number of Purchase Orders

Use the metric requested by the user.

## Goods Receipt Performance

Analyze:

- Delivered Quantity
- Accepted Quantity
- Rejected Quantity
- Damaged Quantity
- Remaining PO Quantity

Acceptance Rate:

`Accepted Quantity / Delivered Quantity × 100`

Rejection Rate:

`Rejected Quantity / Delivered Quantity × 100`

## Invoice Procurement Analysis

Analyze:

- Total Invoice Amount
- Invoice Quantity
- Average Invoice Unit Price
- Discount Amount
- Tax
- Freight Amount

Use `supplier_invoice.invoice_amount` for invoice-level analysis.

Use `supplier_invoice_line.line_amount` for invoice-line analysis.

## Supplier Payment Analysis & Financial Exposure

Analyze supplier payments and exposure using `supplier_payment`:

- **Total Invoice Amount:** `SUM(supplier_invoice.invoice_amount)` ($4,994,148,535.18 across 9,360 invoices)
- **Total Paid Amount:** `SUM(supplier_payment.paid_amount)` ($4,483,341,727.37)
- **Total Outstanding Amount:** `SUM(supplier_payment.outstanding_amount)` ($497,495,271.38 across 1,116 unpaid/partially-paid invoices)
  - Ensure total outstanding always includes ALL unpaid statuses: Paid ($0) + Overdue ($202.47M) + Partially Paid ($92.19M) + On Hold ($101.03M) + Scheduled ($101.80M) = **$497,495,271.38**.

### Payment Status Breakdown

| Payment Status | Invoice Count | Paid Amount ($) | Outstanding Amount ($) | Notes |
|---|---|---|---|---|
| **Paid** | 8,244 | $4,382,682,696.84 | $0.00 | Fully settled |
| **Overdue** | 372 | $0.00 | $202,468,938.05 | 0 payments made, past due date |
| **Partially Paid** | 372 | $100,659,030.53 | $92,194,673.75 | Total partially paid invoices |
| **On Hold** | 186 | $0.00 | $101,033,280.99 | Pending dispute/hold resolution |
| **Scheduled** | 186 | $0.00 | $101,798,378.59 | Scheduled for future payment |
| **TOTAL** | **9,360** | **$4,483,341,727.37** | **$497,495,271.38** | — |

### Overdue Classification Detail
- **All Partially Paid Invoices:** 372 invoices ($92,194,673.75 outstanding).
- **Partially Paid & Overdue (`days_late_early > 0`):** 295 invoices ($73,354,936.49 outstanding).
- **Partially Paid & On-Time (`days_late_early <= 0`):** 77 invoices ($18,839,737.26 outstanding).
- **Combined Total Overdue Obligations:** 667 invoices ($275,823,874.54) = 372 Overdue ($202.47M) + 295 Late Partially Paid ($73.35M).

## PR → PO → Vendor Queries

When analyzing vendors with their Purchase Requisitions and Purchase Orders:
- Relationship path: `vendor` <- `purchase_order` -> `purchase_requisition` (via `purchase_order.vendor_id = vendor.vendor_id` and `purchase_order.pr_id = purchase_requisition.pr_id`).
- When combining line item amounts with header data, avoid `GROUP BY` column errors by either:
  1. Pre-aggregating line sums in a CTE (e.g. `WITH po_sums AS (SELECT po_id, SUM(ordered_quantity * unit_price) as po_amount FROM purchase_order_line GROUP BY po_id)`), or
  2. Querying header tables `purchase_order`, `purchase_requisition`, and `vendor` directly and joining the aggregated CTE.

## Procurement Variance

Quantity Variance:

`Ordered Quantity − Received Quantity`

Invoice Quantity Variance:

`Received Quantity − Invoice Quantity`

Price Variance:

`Invoice Unit Price − PO Unit Price`

Use only when the corresponding records can be correctly matched.

## Procurement Efficiency

Useful indicators include:

- PO fulfillment rate
- GRN acceptance rate
- GRN rejection rate
- Invoice-to-PO quantity ratio
- Procurement cost variance
- Reconciliation success rate

Calculate ratios only when the required denominator is available and non-zero.

## Overdue Procurement

For overdue purchase orders:

- Use `expected_delivery_date`.
- Compare against the relevant reference date.
- Consider `po_status`.
- Do not mark completed or closed orders as overdue without supporting evidence.

## Procurement Trend

For procurement trends:

- Group by the requested date period.
- Preserve chronological order.
- Analyze purchase quantity, purchase amount, invoice amount, or order count as requested.
- Do not treat missing periods as zero.

## Supplier Comparison

When comparing suppliers:

- Use the same metric for every supplier.
- Use the same time period.
- Preserve equal values as ties.
- Do not combine unrelated metrics into a single ranking.

## Procurement Risk Indicators

Identify data-supported indicators such as:

- High rejected quantities
- Large PO-to-invoice quantity differences
- Unit price mismatches
- Failed reconciliations
- Overdue purchase orders
- High procurement cost variance

Do not label a supplier or transaction as risky unless the retrieved data supports the conclusion.

## Error Handling

- If no matching procurement data exists, report that no matching records were found.
- If required fields are missing, do not invent replacements.
- If a database query fails because of an unknown field, do not guess another field.
- If database connectivity or permission fails, stop and report the technical issue.
- Do not perform repeated trial-and-error queries.

## Response Requirements

- Identify the procurement metric being analyzed.
- Clearly distinguish PO, GRN, invoice, vendor, and reconciliation data.
- Show quantities with units.
- Show monetary values with currency.
- Present trends and comparisons in a clear table or visualization when appropriate.
- Keep results traceable to retrieved database values.