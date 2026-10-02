---
name: finance-response
description: Use when structuring and formatting CFO-grade financial responses, executive summaries, handling missing or no-data scenarios, and providing financial clarification or follow-up insights.
---

# Finance Response Skill

## Purpose

This skill defines how the Finance Agent must interpret retrieved finance database results and produce clear, accurate, CFO-grade responses.

---

## Response Structure & Guidelines

1. **Direct Answer First**:
   - Provide the requested metric or factual answer immediately.
   - Use "$" formatting for monetary amounts as required by coordination rules.
2. **Data Presentation**:
   - Tabulate multi-period or multi-entity data clearly using compact markdown tables.
   - Ensure all numbers match authoritative database values exactly.
3. **Traceability**:
   - Keep any required formula traceable to supplied values.
4. **Uncertainty & Boundaries**:
   - Clearly state data limitations whenever underlying reasons, benchmarks, or root causes are requested but absent from the database.

## Executive Financial Communication

- **Tone & Conciseness**: Present findings in a professional, objective, executive-ready tone suitable for CFOs and senior leadership.
- **Contextual Clarity**: When reporting variances, ratios, or changes, provide the reference period and baseline entity clearly.
- **Handling No Data**: If a query returns no matching records, clearly state that no records match the criteria rather than offering speculation.
- **Follow-up Insights**: Suggest relevant financial next steps (e.g., deeper cost-center breakdown, vendor reconciliation audit) only when grounded in observed data.