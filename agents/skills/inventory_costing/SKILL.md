---
name: inventory-costing
description: Defines inventory costing, stock movement, material usage, and inventory variance analysis methods.
---

# Inventory Costing Skill

## Purpose

Apply consistent methods for inventory, material consumption, stock movement, and product costing analysis.

## Core Rules

- Use only retrieved database values or user-provided values.
- Do not invent inventory quantities or costs.
- Preserve the original units.
- Use chronological order for inventory trends.
- Prefer existing database calculation fields when available.
- Do not treat missing records as zero.

## Inventory Position

Use inventory transaction data to analyze:

- Opening Quantity
- Receipt Quantity
- Consumption Quantity
- Transfer Quantity
- Adjustment Quantity
- Closing Quantity

Use `inventory_transaction.closing_quantity` as the recorded closing quantity when available.

## Inventory Movement

For inventory movement analysis, calculate or report:

- Total Receipts
- Total Consumption
- Total Transfers
- Total Adjustments
- Average Closing Quantity

Use `inventory_transaction` fields for these metrics.

## Net Inventory Movement

Net Movement = Receipt Quantity − Consumption Quantity ± Adjustments

Include transfers separately unless the user explicitly asks to include them in net movement.

## Material Consumption

Use `material_consumption` for production material usage.

Relevant metrics:

- Expected Quantity
- Actual Quantity
- Variance Quantity
- Variance Percentage

Prefer `variance_quantity` and `variance_percent` when available.

## Material Consumption Variance

Variance Quantity = Expected Quantity − Actual Quantity

Variance Percentage = ((Actual Quantity − Expected Quantity) / Expected Quantity) × 100

If expected quantity is zero, do not calculate the percentage.

## Product Cost Analysis

Use `product_cost` for product-level costing.

Relevant cost components:

- Standard Cost
- Material Cost
- Direct Labour Cost
- Machine Cost
- Utilities Cost
- Quality Cost
- Packaging Cost
- Manufacturing Overhead Cost
- Actual Product Cost
- Cost Variance
- Cost Variance Percentage

## Cost Component Share

Component Share = (Component Cost / Actual Product Cost) × 100

Use only when actual product cost is available and non-zero.

## Inventory Trend Analysis

For monthly inventory analysis:

- Group inventory transactions by month.
- Maintain chronological order.
- Report receipts, consumption, transfers, adjustments, and closing quantity separately.
- Do not assume missing months represent zero activity.

## Inventory Comparison

When comparing products:

- Use the same time period.
- Use the same inventory metric.
- Compare quantities using the same unit of measure.
- Clearly identify each product.

## Inventory and Cost Analysis

When both inventory and cost information are requested:

- Use `inventory_transaction` for inventory movement.
- Use `product_cost` for product costing.
- Do not mix inventory quantity with monetary cost without explicitly identifying the metric.

## Inventory Reasoning Safeguards

- **Inventory Increase ≠ Poor Management**: An increase in stock or closing balance reflects quantity change only. Never conclude that "poor inventory management", "inefficient planning", or "waste" caused the increase without explicit supporting evidence.
- **No Invented Operational Causes**: Do not attribute inventory changes or consumption variances to unverified causes such as supply chain bottlenecks, machine breakdowns, or defective batches unless verified records explicitly state them.
- **State Data Boundaries Clearly**: If the user asks why inventory or material variance changed, and the data does not contain the reason, state: "The available data shows the change in inventory/variance, but the root cause cannot be determined from the available records."
- **Validated Values > LLM Recomputation**: Use recorded `variance_quantity`, `variance_percent`, and `cost_variance` fields rather than recomputing them independently.

## Error Handling

- If no inventory records exist, report that no matching inventory records were found.
- If required cost data is missing, state that the cost calculation cannot be completed.
- Do not estimate missing inventory values.
- Do not treat missing periods as zero.

## Response Requirements

- Identify the product, material, warehouse, or period being analyzed.
- Show quantities with their units.
- Show monetary values with the correct currency.
- Show calculated variances clearly.
- Keep results traceable to retrieved database values.