---
name: comparison-analytics
description: Defines methods for comparing financial, procurement, inventory, production, product, vendor, and customer data.
---

# Comparison Analytics Skill

## Purpose

Provide consistent comparisons between entities, periods, and financial metrics.

## Core Rules

- Use only retrieved database values or user-provided values.
- Compare the same metric across the same measurement basis.
- Use consistent units and time periods.
- Do not invent missing values.
- Do not assume missing values are zero.
- Keep comparisons factual and data-driven.

## Entity Comparison

For comparisons between:

- Products
- Vendors
- Customers
- Plants
- Warehouses
- Cost centres
- Purchase orders
- Invoices

Use the same metric and calculation method for each entity.

## Product Comparison

Possible metrics:

- Standard Cost
- Actual Product Cost
- Cost Variance
- Cost Variance Percentage
- Production Quantity
- Order Quantity
- Inventory Consumption
- Material Consumption

Keep the comparison period consistent when applicable.

## Vendor Comparison

Possible metrics:

- Purchase Quantity
- Purchase Order Amount
- Invoice Amount
- Received Quantity
- Rejected Quantity
- Reconciliation Issues

Do not mix purchase volume and invoice amount as the same metric.

## Customer Comparison

Possible metrics:

- Order Quantity
- Order Value
- Number of Orders
- Product Demand

Use consistent periods and units.

## Period Comparison

For comparing periods:

- Use the same metric.
- Use equivalent time periods.
- Calculate absolute difference when useful.
- Calculate percentage change when requested.

Percentage Change:

`((New Value − Old Value) / Old Value) × 100`

If the old value is zero, do not calculate the percentage.

## Multi-Metric Comparison

When multiple metrics are requested:

- Keep each metric separate.
- Use a table when exact values are important.
- Do not combine unrelated units into one calculated value.
- Clearly label each metric.

## Ranking Within Comparison

If the user asks which entity has the highest or lowest value:

- Compare the retrieved values.
- Identify the relevant entity or entities.
- Use the requested metric only.
- Do not rank entities using an unstated metric.

## Trend Comparison

When comparing trends:

- Use the same time periods.
- Use the same metric.
- Preserve chronological order.
- Identify differences in direction or magnitude only when supported by the data.

## Difference Analysis

Absolute Difference:

`Value A − Value B`

Percentage Difference:

Use the user-specified baseline.

If no baseline is specified for a change comparison, use Value B as the baseline:

`((Value A − Value B) / Value B) × 100`

## Missing Data

- If one entity has no matching records, report that the comparison cannot be completed for that entity.
- Do not replace missing values with zero.
- Do not create estimated values.

## Error Handling

- If no matching records are found, report the absence of data.
- If database access fails, stop and report the technical issue.
- Do not perform repeated trial-and-error queries.

## Response Requirements

- Present compared entities clearly.
- Show the metric and values.
- Include units and periods.
- Show calculated differences when relevant.
- Keep the comparison traceable to retrieved data.