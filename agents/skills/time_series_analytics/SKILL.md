---
name: time-series-analytics
description: Defines methods for analyzing financial, procurement, inventory, production, and invoice trends over time.
---

# Time Series Analytics Skill

## Purpose

Analyze chronological finance and business data consistently.

## Core Rules

- Use only retrieved database values or user-provided values.
- Preserve chronological order.
- Use consistent time periods.
- Do not treat missing periods as zero.
- Do not invent missing time-series values.
- Use the minimum required database queries.

## Time Granularity

Use the granularity requested by the user:

- Daily
- Weekly
- Monthly
- Quarterly
- Yearly

If no granularity is specified for a trend request, use monthly analysis when sufficient date data is available.

## Trend Analysis

For time-series analysis:

- Group data by the selected time period.
- Sort periods chronologically.
- Show the actual value for each period.
- Identify increases, decreases, and stable periods only from the retrieved data.

## Period-over-Period Change

Period Change = Current Period Value − Previous Period Value

Percentage Change:

`((Current Period Value − Previous Period Value) / Previous Period Value) × 100`

If the previous period value is zero, do not calculate the percentage.

## Year-over-Year Analysis

Use the same period from consecutive years.

YoY Change:

`((Current Year Value − Previous Year Value) / Previous Year Value) × 100`

## Monthly Analysis

For monthly trends:

- Group records by month.
- Keep months in chronological order.
- Preserve all available months.
- Do not fill missing months with assumed values.

## Trend Metrics

Depending on the request, analyze:

- Revenue
- Invoice Amount
- Invoice Quantity
- Order Quantity
- Inventory Receipts
- Inventory Consumption
- Production Quantity
- Material Consumption
- Cost
- Cost Variance

## Moving Averages

Use a moving average only when requested or useful for identifying a trend.

For an n-period moving average:

`Average = Sum of n periods / n`

Do not calculate a moving average when insufficient consecutive periods are available.

## Trend Interpretation

When summarizing a trend:

- Identify the highest period.
- Identify the lowest period.
- Describe increases and decreases factually based on retrieved numbers.
- Mention significant changes only when supported by the data.
- **Strict Prohibition on Invented Causes**: Do not infer or invent business causes (e.g., "higher customer demand", "supplier price hikes", "inflation", "production bottlenecks") without explicit supporting database evidence.
- **State Data Boundaries**: If asked why a trend increased or decreased, and the data does not contain the root cause, state: "The data shows an increase/decrease of X%, but the underlying business reason cannot be determined from the available records."

## Comparison of Trends

When comparing two entities over time:

- Use the same periods for both.
- Use the same metric.
- Preserve chronological order.
- Clearly identify each entity.

## Missing Data

- Do not assume missing periods represent zero.
- Do not interpolate missing values unless explicitly requested.
- Clearly indicate unavailable periods when relevant.

## Error Handling

- If no records are returned, report that no matching records were found.
- If dates are missing, do not create a time-series interpretation.
- If the database fails, stop and report the technical issue.

## Response Requirements

- Present time-series results in chronological order.
- Use a table or line chart when appropriate.
- Include the relevant time period and metric.
- Keep calculated changes traceable to retrieved values.