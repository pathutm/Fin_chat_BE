---
name: visualization-intent
description: Defines when financial analysis should be presented using tables, charts, or other visual formats, enforcing strict database data accuracy and integrity.
---

# Visualization Intent & Data Accuracy Skill

## Purpose

Determine the appropriate presentation format for finance analysis results while enforcing strict database-driven data integrity, preventing any hallucinated, missing, duplicated, hidden, repeated, or invented chart values.

## Data Accuracy & Integrity Enforcements

### 1. Database is the Source of Truth
- Every number shown in a chart must come directly from the verified database result or from a deterministic calculation based only on that result.
- The LLM must NEVER invent, guess, or hallucinate chart values under any circumstances.
- Data Flow: `DATABASE` → `VERIFIED RESULT` → `CHART DATASET` → `EXISTING CHART`

### 2. No Data Loss (Complete Data Preservation)
- If the database returns 42 records, the chart dataset MUST contain all 42 records unless the user's question explicitly requests an aggregation.
- Strictly DO NOT:
  - Drop records
  - Hide records
  - Sample records
  - Truncate records
  - Randomly select records
  - Show only "important" or "representative" records
  - Replace detailed records with an unrequested summary

### 3. No Duplication
- Each database record must appear exactly once in the chart dataset.
- Strictly DO NOT duplicate:
  - Months or time periods
  - Vendors or customers
  - Products or categories
  - Invoices or transactions
  - Revenue or cost values
  - Any other database records

### 4. Preserve User Requested Granularity
- If the user asks for monthly data, preserve monthly data without altering granularity.
- Example: *"Show revenue and invoice amount trends over each month."*
  - If the database contains 42 monthly records, preserve all 42 months in the chart dataset.
  - DO NOT convert them to yearly data.
  - DO NOT combine or roll up months unless requested.
  - DO NOT display only a few representative months.

### 5. Multiple Metrics Consistency
- If the user requests multiple metrics (e.g., Revenue + Invoice Amount), every metric must use the exact same underlying records and time periods.
- For every period/entity returned: `{ period, metric_1, metric_2 }`.
- DO NOT use mismatched periods or different subset records for different metrics.

### 6. Missing Database Values
- If the database contains `NULL` or missing data, DO NOT invent a value.
- DO NOT replace missing values with `0`, averages, estimates, previous values, or future values unless the database query or user's request explicitly defines that calculation rule.

### 7. Deterministic Calculations Only
- Totals, averages, percentages, ratios, variances, rankings, and comparisons must be calculated deterministically from the verified database result.
- Never estimate, interpolate, or guess calculation results.

### 8. Chart Axis vs Data Points
- The chart UI may visually reduce the density of axis labels for readability, but this must NEVER remove or filter out the underlying data points.
- Example: 42 records must have 42 plotted data points even if only a subset of x-axis date labels are rendered.

### 9. No Second Source of Data
- The chart dataset must be constructed strictly from the same verified database result used for the textual response.
- DO NOT allow a separate chart dataset to be constructed independently from generated textual explanation prose.

### 10. Financial Currency Integrity
- For financial values, preserve the exact underlying numeric database value.
- Only presentation formatting may convert the display to the application's required `$` format.
- DO NOT alter or scale the underlying database value.

### 11. Existing Chart Component Stability
- DO NOT modify or redesign existing chart components or visualization behavior.
- DO NOT change chart types, styling, colors, layout, filters, legends, tooltips, zoom, or export logic.
- This skill applies strictly to chart-data accuracy, integrity, and source-of-truth alignment.

### 12. Mandatory Pre-Render Validation Checklist
Before producing chart data, logically verify:
- `database_records == chart_records` (unless explicit aggregation was requested)
- No missing records
- No duplicate records
- No repeated periods or entities
- All requested metrics are present
- Requested granularity is fully preserved
- Every chart value is 100% traceable to the database result

If the requested chart data cannot be supported by the verified database result, DO NOT invent values. Clearly report that available database data does not support the requested chart.

---

## Visualization Selection Guidelines

### Table
Use a table when:
- Comparing a small number of products, vendors, customers, or periods.
- Showing multiple detailed metrics for the same entities.
- Exact values are paramount.
- The user explicitly asks to compare or list values in tabular format.

### Line Chart
Use a line chart for:
- Time-series trends (monthly, quarterly, yearly).
- Revenue or invoice amount trends over time.
- Inventory movement or production trends over time.
- Always preserve chronological order on the time axis.

### Bar Chart
Use a bar chart for:
- Comparing distinct categories (products, vendors, customers).
- Ranking categories by a metric.
- Comparing quantities or amounts across independent entities.

### Pie / Donut Chart
Use a pie or donut chart only for simple part-to-whole composition with a small number of categories (e.g., cost distribution, revenue composition).
DO NOT use pie charts for time-series trend analysis.

### Scatter Chart
Use a scatter chart for relationships between two numerical variables (e.g., invoice quantity vs. invoice amount).

---

## Final Core Rule

```
EXACT DATABASE DATA 
  → EXACT CHART DATA 
  → NO HALLUCINATION 
  → NO MISSING DATA 
  → NO HIDDEN DATA 
  → NO DUPLICATES 
  → NO REPEATED DATA 
  → NO INVENTED VALUES 
  → NO UNAUTHORIZED AGGREGATION
```