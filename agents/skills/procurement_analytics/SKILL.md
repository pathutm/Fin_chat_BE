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