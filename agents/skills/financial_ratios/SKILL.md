---
name: financial-ratios
description: Defines standard financial ratio calculations for profitability, cost, efficiency, liquidity, and performance analysis.
---

# Financial Ratios Skill

## Purpose

Apply standard financial ratios when the required financial data is available.

## Core Rules

- Use only retrieved database values or user-provided values.
- Do not invent missing values.
- Use consistent periods and units.
- Round ratios and percentages to 2 decimal places.
- If the denominator is zero, do not calculate the ratio.
- Prefer existing database fields when they directly provide the requested metric.

## Profit Margin

Profit Margin = (Profit / Revenue) × 100

If profit is not directly available:

Profit = Revenue − Cost

## Cost Variance Percentage

Cost Variance Percentage = ((Actual Cost − Standard Cost) / Standard Cost) × 100

Use the existing `cost_variance_percent` field when available.

## Quantity Variance Percentage

Quantity Variance Percentage = ((Actual Quantity − Expected Quantity) / Expected Quantity) × 100

Use the existing `variance_percent` field when available.

## Invoice-to-PO Quantity Ratio

Invoice-to-PO Ratio = Invoice Quantity / PO Quantity

Use matching PO and invoice records.

## GRN Acceptance Rate

GRN Acceptance Rate = (Accepted Quantity / Delivered Quantity) × 100

If delivered quantity is zero, do not calculate the rate.

## GRN Rejection Rate

GRN Rejection Rate = (Rejected Quantity / Delivered Quantity) × 100

If delivered quantity is zero, do not calculate the rate.

## Damaged Quantity Rate

Damaged Quantity Rate = (Damaged Quantity / Delivered Quantity) × 100

If delivered quantity is zero, do not calculate the rate.

## Invoice Discount Percentage

Invoice Discount Percentage = (Discount Amount / Invoice Amount) × 100

Use only when both values are available and the requested interpretation is appropriate.

## Purchase Order Fulfillment Rate

Purchase Order Fulfillment Rate = (Accepted GRN Quantity / Ordered PO Quantity) × 100

Use matching PO and GRN records.

## Payment Due Analysis

For payment-related analysis:

- Identify invoice amount.
- Identify payment due date.
- Compare against the requested reference date when applicable.
- Do not assume an invoice is overdue without a valid date comparison.

## Year-over-Year Ratio Analysis

YoY Percentage Change = ((Current Period − Previous Period) / Previous Period) × 100

Use consistent periods.

## Product Cost Structure

When analyzing product cost:

Total Product Cost may include:

- Material Cost
- Direct Labour Cost
- Machine Cost
- Utilities Cost
- Quality Cost
- Packaging Cost
- Manufacturing Overhead Cost

Use the corresponding `product_cost` fields.

## Cost Component Percentage

Component Percentage = (Component Cost / Total Product Cost) × 100

Use `actual_product_cost` as the total when appropriate.

## Ratio Comparison

When comparing two products, vendors, customers, or periods:

- Calculate the same ratio for each item.
- Use the same denominator definition.
- Present the values side by side.
- Do not mix different time periods.

## Error Handling

- If required values are missing, state that the ratio cannot be calculated.
- If the denominator is zero, report that the ratio is undefined.
- Do not estimate missing financial values.
- Do not use unrelated fields to construct a ratio.

## Response Requirements

- Show the ratio name.
- Show the calculated value.
- Include `%` for percentage ratios.
- Include the relevant period or entity.
- Keep the calculation traceable to retrieved data.