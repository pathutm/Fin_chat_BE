---
name: ranking-analytics
description: Defines methods for ranking products, vendors, customers, costs, quantities, and operational metrics.
---

# Ranking Analytics Skill

## Purpose

Provide consistent ranking analysis using retrieved finance and business data.

## Core Rules

- Use only retrieved database values or user-provided values.
- Rank only using the metric requested by the user.
- Do not invent missing values.
- Do not treat missing values as zero.
- Use consistent units and time periods.
- Preserve ties when values are equal.

## Ranking Metrics

Possible ranking metrics include:

- Purchase Quantity
- Purchase Order Amount
- Invoice Amount
- Order Quantity
- Order Value
- Production Quantity
- Inventory Consumption
- Material Consumption
- Cost
- Cost Variance
- Cost Variance Percentage
- Rejected Quantity
- Reconciliation Mismatches

## Highest Ranking

When the user asks for the highest:

- Sort the requested metric in descending order.
- Return the highest value first.
- Include the entity name or identifier.
- Preserve ties.

## Lowest Ranking

When the user asks for the lowest:

- Sort the requested metric in ascending order.
- Return the lowest value first.
- Include the entity name or identifier.
- Preserve ties.

## Top-N Ranking

For requests such as top 5 or top 10:

- Return exactly the requested number when enough records exist.
- Sort by the requested metric.
- Preserve ties where applicable.
- Do not substitute another metric.

## Ranking by Percentage

For percentage-based rankings:

- Use the relevant database percentage field when available.
- Otherwise calculate the percentage using the appropriate formula.
- Sort the calculated percentages consistently.

## Time-Based Ranking

When ranking by time period:

- Use the same metric across all periods.
- Preserve chronological labels when presenting the result.
- Rank based on the requested measure, not the date.

## Ranking Comparison

When comparing ranked entities:

- Show the entity.
- Show the ranking metric.
- Show the value.
- Clearly state the requested ranking order.

## Missing Data

- Exclude records with missing values from a calculation only when necessary.
- Do not replace missing values with zero.
- State when insufficient data prevents reliable ranking.

## Error Handling

- If no matching records are found, report that no matching data was found.
- If database access fails, stop and report the technical issue.
- Do not perform repeated trial-and-error queries.

## Response Requirements

- Clearly identify the ranking metric.
- Show the requested ranking order.
- Include values and units.
- Keep rankings traceable to retrieved database data.