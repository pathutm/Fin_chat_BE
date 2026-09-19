---

name: ranking-analytics
description: Analyzes finance metrics to identify and order the highest, lowest, top-N, or bottom-N entities using actual CFO database results. Use for rankings of vendors, products, plants, warehouses, customers, purchase orders, invoices, or other supported entities. Determines the ranking dimension, metric, aggregation, direction, limit, and filters. Does not generate SQL, access MCP, or invent data.
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Ranking Analytics

Analyze finance metrics to identify and order entities according to the user's requested ranking.

## Principles

* Use only actual database results.
* Never invent, estimate, or assume missing values.
* Identify the correct ranking dimension and metric.
* Preserve requested filters and time range.
* Follow the requested ranking direction.
* Do not choose an arbitrary limit when the user does not specify one.
* Do not generate SQL or access MCP.

## Ranking Triggers

Use for requests containing:

* Top-N
* Bottom-N
* Highest
* Lowest
* Largest
* Smallest
* Most
* Least
* Maximum
* Minimum

## Required Analysis

Identify:

```text
Ranking dimension:
Metric:
Aggregation:
Direction:
Limit:
Filters:
Time range:
Unit:
```

Direction:

* Top / highest / largest / most / maximum → descending
* Bottom / lowest / smallest / least / minimum → ascending

Common aggregations:

* SUM
* AVG
* COUNT
* MIN
* MAX

## Ranking Structure

Return the analysis in this structure:

```text
Title:
Ranking dimension:
Metric:
Aggregation:
Direction:
Limit:
Data:
```

Preserve entity names, identifiers, and values exactly as returned by the database.

## Ranking Rules

* Apply the requested limit when provided.
* If no limit is specified, do not arbitrarily select Top 5 or Top 10.
* Preserve ties when values are equal.
* Do not invent tie-breaking rules.
* Apply requested time filters consistently.
* Do not treat missing data as zero unless zero is explicitly returned.
* Clearly distinguish stored values from calculated values.

## Combined Analysis

Ranking analysis can be combined with:

* Time-Series Analytics for rankings by period.
* Comparison Analytics when entity comparisons are also requested.
* Procurement Analytics for vendor, PO, GRN, and invoice rankings.
* Visualization Intent for presentation selection.

## Visualization Guidance

* Bar chart: ranked entities.
* Table: detailed ranking records.
* Line chart: ranking changes across time when explicitly requested.

## Boundaries

| Responsibility         | Owner                 |
| ---------------------- | --------------------- |
| Ranking analysis       | ranking-analytics     |
| Intent detection       | visualization-intent  |
| Time analysis          | time-series-analytics |
| Comparison             | comparison-analytics  |
| Procurement context    | procurement-analytics |
| SQL / database queries | Finance Agent         |
| MCP / Supabase         | MCP client            |
| Final formatting       | finance-response      |
| Rendering              | Frontend              |

Apply this skill when the user requests a ranking and actual database results are available.
