---

name: comparison-analytics
description: Analyzes finance metrics across two or more entities or categories using actual CFO database results. Use for comparing vendors, products, plants, warehouses, customers, or other business entities. Determines the comparison dimension, metric, aggregation, filters, and result structure. Does not generate SQL, access MCP, or invent data.
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Comparison Analytics

Analyze finance metrics across entities or categories and structure the results for comparison and visualization.

## Principles

* Use only actual database results.
* Never invent, estimate, or assume missing values.
* Identify the correct comparison dimension.
* Preserve the user's requested filters and time range.
* Follow the requested sorting or ordering.
* Do not automatically convert a comparison into a ranking.
* Do not generate SQL or access MCP.

## Comparison Dimensions

Supported dimensions may include:

* Vendors
* Products
* Plants
* Warehouses
* Customers
* Purchase orders
* Supplier invoices
* Other supported business categories

## Required Analysis

Identify:

```text
Comparison dimension:
Metric:
Aggregation:
Filters:
Time range:
Sort order:
Unit:
```

Common aggregations:

* SUM
* AVG
* COUNT
* MIN
* MAX

## Result Structure

Return the analysis in this structure:

```text
Title:
Comparison dimension:
Metric:
Aggregation:
Data:
```

Preserve entity names, identifiers, and values exactly as returned by the database.

## Comparison Rules

* Compare entities using the same metric and aggregation.
* Apply requested time filters consistently across entities.
* Calculate differences or variances only when explicitly requested.
* Clearly distinguish database values from calculated values.
* Do not treat missing data as zero unless zero is explicitly returned.
* Do not add an arbitrary ranking when the user only requests comparison.

## Visualization Guidance

* Bar chart: entity-level comparison.
* Line chart: comparison across time.
* Table: detailed multi-field comparison.
* KPI: single aggregated comparison result when appropriate.

## Combined Analysis

Comparison analysis can be combined with:

* Time-Series Analytics for comparisons across time.
* Ranking Analytics when the user explicitly requests an ordered ranking.
* Procurement Analytics for vendor and procurement comparisons.
* Visualization Intent for presentation selection.

## Boundaries

| Responsibility         | Owner                 |
| ---------------------- | --------------------- |
| Comparison analysis    | comparison-analytics  |
| Intent detection       | visualization-intent  |
| Time analysis          | time-series-analytics |
| Ranking                | ranking-analytics     |
| Procurement context    | procurement-analytics |
| SQL / database queries | Finance Agent         |
| MCP / Supabase         | MCP client            |
| Final formatting       | finance-response      |
| Rendering              | Frontend              |

Apply this skill when the user requests a comparison and actual database results are available.
