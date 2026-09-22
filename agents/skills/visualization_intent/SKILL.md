---
name: visualization-intent
description: Defines when financial analysis should be presented using tables, charts, or other visual formats.
---

# Visualization Intent Skill

## Purpose

Determine the appropriate presentation format for finance analysis results.

## Core Rules

- Use visualizations only when they improve understanding.
- Do not create visualizations for simple factual answers.
- Use only retrieved or calculated data.
- Do not invent or estimate chart values.
- Keep visualizations focused on the user's question.

## Table

Use a table when:

- Comparing a small number of products, vendors, customers, or periods.
- Showing multiple metrics for the same entities.
- Exact values are important.
- The user explicitly asks to compare or list values.

## Line Chart

Use a line chart for:

- Monthly trends.
- Yearly trends.
- Time-series analysis.
- Revenue or invoice amount trends.
- Inventory movement over time.
- Production trends over time.

Use chronological order on the x-axis.

## Bar Chart

Use a bar chart for:

- Comparing products.
- Comparing vendors.
- Comparing customers.
- Ranking categories.
- Comparing quantities or amounts across independent categories.

Use a horizontal bar chart when there are many categories.

## Pie Chart

Use a pie chart only for simple part-to-whole analysis with a small number of categories.

Examples:

- Product cost components.
- Cost distribution.
- Revenue composition.

Do not use pie charts for time-series trends.

## Scatter Chart

Use a scatter chart when the user asks about relationships between two numerical variables.

Examples:

- Invoice quantity vs invoice amount.
- Ordered quantity vs invoice quantity.
- Cost vs production quantity.

## Visualization Selection

Use:

- Simple retrieval → text or table.
- Comparison → table or bar chart.
- Trend → line chart.
- Ranking → bar chart.
- Part-to-whole → pie chart.
- Numeric relationship → scatter chart.
- Multiple metrics → table or appropriate chart.

## Multi-Metric Visualization

When multiple metrics are requested:

- Use a table when exact values are important.
- Use separate visualizations only when each adds meaningful information.
- Do not overload one chart with unrelated metrics.

## Data Requirements

Before visualization:

- Verify that the required data was successfully retrieved.
- Use consistent units.
- Use consistent time periods.
- Preserve chronological order for time-series data.
- Do not replace missing values with zero unless the database explicitly records zero.

## Error Handling

- If there is insufficient data, do not create a misleading visualization.
- If the query returns no records, report that no matching data was found.
- If the database fails, stop visualization generation and report the technical issue.

## Response Requirements

- Keep the visualization directly related to the user's question.
- Provide a short explanation of what the visualization shows.
- Use clear labels and units.
- Do not add unnecessary charts.