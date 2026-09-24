---
name: financial-formulas
description: Defines standard financial calculation methods for cost analysis, variance analysis, growth analysis, and financial comparisons.
---

# Financial Formulas Skill

## Purpose

Apply consistent financial formulas when calculations are required from retrieved finance data.

## Core Rules

- **Validated Backend Value > LLM Recomputation**: If the database, tool response, or backend provides a calculated or aggregated value (totals, averages, counts, variances, percentages), the agent MUST use that supplied value directly. Do NOT independently sum, average, or recalculate from raw rows.
- Use only values returned from the database or provided by the user.
- Do not invent missing values.
- Treat supplied values as authoritative. If raw records and supplied aggregated values appear inconsistent, report the supplied value and note that underlying records appear inconsistent; do NOT derive a conflicting number.
- Use the correct financial formula for the requested calculation only when no validated backend result exists.
- Round calculated percentages to 2 decimal places unless the user specifies otherwise.
- If the denominator is zero, do not calculate the percentage. Report that the percentage cannot be calculated.
- **Metric Purity & No Conflation with Savings**:
  - `PO Amount − Invoice Amount` is a reconciliation difference or billing variance, NEVER "savings" unless explicitly defined.
  - `Actual Cost − Standard Cost` is cost variance, not savings.
  - Price differences (e.g. latest vs peak, standard vs actual) are variances, not savings.
  - Do not combine or substitute incompatible metrics.
- Keep calculations traceable to the retrieved database values.

## Cost Variance

For standard cost versus actual product cost:

- Cost variance = Actual Cost − Standard Cost
- Cost variance percentage = ((Actual Cost − Standard Cost) / Standard Cost) × 100

Use `product_cost.cost_variance` and `product_cost.cost_variance_percent` when those fields contain the required values.

## Percentage Change

For comparing an old value with a new value:

Percentage Change = ((New Value − Old Value) / Old Value) × 100

Use the old value as the baseline.

## Year-over-Year Change

For yearly financial values:

YoY Change = ((Current Year Value − Previous Year Value) / Previous Year Value) × 100

If the previous year's value is zero, report that YoY percentage cannot be calculated.

## Revenue Calculation

For customer orders:

Revenue = Ordered Quantity × Unit Price

Use `customer_order.ordered_quantity` and `customer_order.unit_price`.

## Purchase Order Amount

For purchase orders:

Purchase Order Amount = Ordered Quantity × Unit Price

Use `purchase_order_line.ordered_quantity` and `purchase_order_line.unit_price`.

Do not use nonexistent total amount fields from `purchase_order`.

## Invoice Amount

For invoice-level analysis:

Use `supplier_invoice.invoice_amount`.

For invoice-line analysis:

Use `supplier_invoice_line.line_amount`.

Do not substitute invoice-level and invoice-line amounts unless the user explicitly requests it.

## Average Unit Price

Average Unit Price = Total Value / Total Quantity

When appropriate, use:

SUM(quantity × unit_price) / SUM(quantity)

Do not calculate an average from unrelated records.

## Quantity Variance

Quantity Variance = Expected Quantity − Actual Quantity

Use the relevant expected and actual quantity fields from the retrieved data.

## Material Consumption Variance

For material consumption:

Variance Quantity = Expected Quantity − Actual Quantity

Use `material_consumption.variance_quantity` when available.

Use `material_consumption.variance_percent` when the percentage variance is requested and the database field provides it.

## Margin Calculation

If revenue and cost are available:

Profit = Revenue − Cost

Profit Margin = (Profit / Revenue) × 100

If revenue is zero, do not calculate the margin percentage.

## Multi-Metric Calculations

When the user requests multiple financial metrics:

- Calculate each metric independently.
- Keep the same time period and filtering conditions across metrics.
- Do not mix invoice-level, invoice-line, purchase-order, and customer-order values without explicitly identifying the source.
- Present each metric with its unit.

## Comparison Calculations

When comparing two products, vendors, customers, or periods:

- Retrieve the required values.
- Apply the same formula to both items.
- Show the calculated difference or percentage change when requested.
- Do not declare a winner unless the user explicitly asks for a comparison based on a defined metric.

## Trend Calculations

For time-series financial data:

- Keep chronological order.
- Calculate period-over-period changes only when sufficient consecutive periods are available.
- Do not infer missing periods as zero.
- Clearly distinguish actual database values from calculated values.

## Calculation Examples

### Product Cost Comparison

Required values:
- Standard Cost
- Actual Product Cost

Calculate:
- Cost Variance
- Cost Variance Percentage

### Yearly Invoice Trend

Required values:
- Invoice amount for each year

Calculate:
- Year-over-Year Change

### Monthly Financial Comparison

For each month, retain:
- Invoice Amount
- Invoice Count
- Invoice Quantity

Calculate additional percentages only when requested.

## Error Handling

- If required input data is missing, state that the calculation cannot be completed.
- If a denominator is zero, do not produce an invalid percentage.
- If database values conflict, use the authoritative retrieved database value and report the inconsistency if relevant.
- Never create estimated financial values unless the user explicitly requests an estimate.

## Response Requirements

- Show the formula only when useful for understanding the calculation.
- Show the final calculated value clearly.
- Use ₹ for INR values when appropriate.
- Use `%` for percentages.
- Keep calculations traceable to the retrieved database values.