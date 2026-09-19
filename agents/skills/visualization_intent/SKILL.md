---

name: visualization-intent
description: Determines the analytical and presentation intent for CFO finance questions. Use for KPI, time-series, comparison, ranking, table, or text responses. Does not generate SQL, access MCP, retrieve data, or create chart code.
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Visualization Intent

Identify the user's primary analytical intent and provide the structure needed by downstream analytics and frontend visualization.

## Principles

* Understand the actual question and requested operation.
* Use only actual database results; never invent or estimate data.
* Preserve requested granularity and dimensions.
* Do not force visualization when text or a KPI is sufficient.
* Identify the metric, primary dimension, aggregation, and time dimension when applicable.
* Choose one primary intent unless multiple views are explicitly requested.
* Do not generate SQL, access MCP, or modify source data.

## Intent Categories

### KPI / Single Value

Use for one aggregated value such as total, amount, count, or average.

Preferred presentation: KPI.

### Time-Series / Trend

Use for metrics across time: daily, weekly, monthly, quarterly, yearly, historical, or trend questions.

Preferred visualization: Line or time-series.

Use the Time-Series Analytics Skill for detailed temporal analysis.

### Comparison

Use when comparing a metric across entities or categories such as vendors, products, plants, warehouses, or customers.

Preferred visualization: Bar.

Use the Comparison Analytics Skill for detailed comparison.

### Ranking

Use for top/bottom, highest/lowest, largest/smallest, most/least, or Top-N requests.

Preferred visualization: Bar.

Use the Ranking Analytics Skill for detailed ranking.

### Table / Multiple Records

Use for document-level details, lists, or multiple fields.

Preferred presentation: Table.

### Text

Use for definitions, explanations, status, or questions where visualization adds no value.

Preferred presentation: Text.

## Decision Rules

| Request pattern                                | Intent      |
| ---------------------------------------------- | ----------- |
| Total / amount / count / average               | KPI         |
| By month / week / quarter / year / over time   | Time-Series |
| Compare / across entities                      | Comparison  |
| Top / bottom / highest / lowest / most / least | Ranking     |
| List / records / details                       | Table       |
| Definition / explanation / status              | Text        |

If multiple patterns appear, follow the primary request.

## Required Intent Information

```text
Intent:
Metric:
Primary dimension:
Time dimension:
Aggregation:
Requested limit:
Requested granularity:
Preferred visualization:
```

Populate only supported fields.

## Boundaries

| Responsibility         | Owner                 |
| ---------------------- | --------------------- |
| Intent detection       | visualization-intent  |
| Time analysis          | time-series-analytics |
| Comparison             | comparison-analytics  |
| Ranking                | ranking-analytics     |
| Procurement context    | procurement-analytics |
| SQL / database queries | Finance Agent         |
| MCP / Supabase         | MCP client            |
| Routing                | Coordination Agent    |
| Final formatting       | finance-response      |
| Rendering              | Frontend              |

This skill determines intent only. Do not generate SQL, call MCP, access Supabase, fabricate data, or modify frontend configuration.

Apply this skill before the specialized analytics skill.
