---

name: time-series-analytics
description: Analyzes finance metrics across time using actual CFO database results. Use for daily, weekly, monthly, quarterly, yearly, historical, or trend questions. Determines the time dimension, granularity, aggregation, ordering, and trend structure. Does not generate SQL, access MCP, or invent data.
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Time-Series Analytics

Analyze finance metrics across time and structure the results for downstream visualization and response formatting.

## Principles

* Use only actual database results.
* Never invent, estimate, or assume missing values.
* Identify the correct date field from available database fields.
* Preserve the user's requested time range and granularity.
* Order time periods chronologically.
* Do not treat missing periods as zero unless the database explicitly returns zero.
* Do not generate SQL or access MCP.

## Supported Time Granularity

* Daily
* Weekly
* Monthly
* Quarterly
* Yearly

## Required Analysis

Identify:

```text
Metric:
Date field:
Time range:
Time granularity:
Aggregation:
Unit:
Sort order:
```

Common aggregations:

* SUM
* AVG
* COUNT
* MIN
* MAX

Use the appropriate supported date field, such as `po_date`, `invoice_date`, or `expected_delivery_date`, based on the database result and user request. Do not assume undocumented fields.

## Time-Series Structure

Return the analysis in this structure:

```text
Title:
Metric:
Time granularity:
Date field:
Aggregation:
Data:
```

Preserve the actual returned period and value for every record.

## Visualization Guidance

* Line chart: trends over time.
* Bar chart: discrete period comparisons.
* Table: when detailed records are requested.
* KPI: when the request asks for one aggregated value.

## Combined Analysis

Time-series analysis can be combined with:

* Ranking for top or bottom entities by period.
* Comparison for entity-level trends.
* Procurement Analytics for procurement-related time trends.
* Visualization Intent for presentation selection.

## Boundaries

| Responsibility         | Owner                 |
| ---------------------- | --------------------- |
| Time-series analysis   | time-series-analytics |
| Intent detection       | visualization-intent  |
| Comparison             | comparison-analytics  |
| Ranking                | ranking-analytics     |
| Procurement context    | procurement-analytics |
| SQL / database queries | Finance Agent         |
| MCP / Supabase         | MCP client            |
| Final formatting       | finance-response      |
| Rendering              | Frontend              |

Apply this skill after time-series intent is identified and actual database results are available.
