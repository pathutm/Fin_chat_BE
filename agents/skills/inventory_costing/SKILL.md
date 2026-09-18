---
name: inventory-costing
description: Guides inventory movement analysis, material consumption, BOM comparison, and product cost variance using the CFO Analysis Industry Database tables, relationships, and confirmed costing rules.
---

# Inventory & Costing

Inventory and product costing rules for the Finance Agent. Covers **inventory movements, material consumption, BOM analysis, and cost variance**. Does not execute SQL, route requests, or format final responses.

## Confirmed project context

- **Database:** CFO Analysis Industry Database (21 relational tables, read-only).
- **Business flow segment:** … → Reconciliation → Cost Centre Allocation → **Inventory Transaction** → **Material Consumption** → **Product Cost** → Line of Business

## Confirmed tables and relationships

| Table | Role | Key relationships |
|-------|------|-------------------|
| `inventory_transaction` | Perpetual warehouse stock ledger | `product_id` → `product`; `warehouse_id` → `warehouse` |
| `warehouse` | Warehouse master | Referenced by `inventory_transaction`, `purchase_order`, `goods_receipt_note` |
| `product` | Product master | `lob_id` → `line_of_business`; referenced across procurement, BOM, costing |
| `material_consumption` | Actual production material usage | `production_order_id` → `production_order`; `finished_product_id`, `raw_material_id` → `product`; `cost_centre_id` → `cost_centre` |
| `production_order` | Production runs | `finished_product_id` → `product`; `plant_id` → `plant`; `production_cost_centre_id` → `cost_centre` |
| `bill_of_material` | Planned raw-material requirements | `finished_product_id`, `raw_material_id` → `product` |
| `product_cost` | Finished-product standard costing | `finished_product_id` → `product` |
| `cost_centre_allocation` | Cost allocation from GRN lines | `grn_line_id` → `goods_receipt_note_line`; `cost_centre_id` → `cost_centre` |

### Confirmed identifiers

| Entity | Primary key |
|--------|-------------|
| `inventory_transaction` | `transaction_id` |
| `material_consumption` | `consumption_id` |
| `production_order` | `production_order_id` |
| `product_cost` | `product_cost_id` |
| `product` | `product_id` (VARCHAR, e.g., `'PROD-0001'`) |
| `warehouse` | `warehouse_id` |

All identifiers are VARCHAR/TEXT strings.

### Production and BOM scale (documented)

- 22 finished products
- 38 raw materials
- 88 BOM records
- Each finished product has raw-material BOM relationships in `bill_of_material`

---

## Confirmed formulas

### Inventory Balance

```
Inventory Balance = Opening Balance + Receipts − Consumption + Transfers ± Adjustments
```

| Item | Detail |
|------|--------|
| **Source table** | `inventory_transaction` |
| **Scope** | Filter by `product_id` and `warehouse_id` |
| **Movement types** | The ledger covers **receipts**, **consumption**, **transfers**, and **adjustments** |
| **Procedure** | 1) Fix product/warehouse scope. 2) Classify transaction rows by movement type. 3) Aggregate each category. 4) Apply formula. |
| **Warehouse-level** | Always scope by both `product_id` and `warehouse_id` when warehouse is relevant. |
| **Result type** | Calculated from ledger movements unless a stored balance exists in query results. |

### Cost Variance

```
Cost Variance = Actual Product Cost − Standard Cost
```

| Item | Detail |
|------|--------|
| **Standard cost source** | `product_cost` joined via `finished_product_id` |
| **Actual cost** | From query results for the same finished product and period |
| **Procedure** | Obtain both values for the same scope; subtract. Positive = actual exceeds standard. |
| **Result type** | Calculated unless a stored variance column exists. |

---

## Inventory analysis

### Movement classification

Classify `inventory_transaction` rows into the formula categories:

| Movement | Effect on balance |
|----------|-------------------|
| **Receipts** | Add |
| **Consumption** | Subtract |
| **Transfers** | Add inbound / subtract outbound (or apply net transfer total) |
| **Adjustments** | Apply signed adjustment values |

### Workflow

1. Resolve `product_id` (and `warehouse_id` if needed) using the `product` table.
2. Retrieve `inventory_transaction` rows for the scope.
3. Aggregate by movement type.
4. Apply the Inventory Balance formula.
5. Label result as stored or calculated.

---

## Material consumption

### Actual material consumption

Sum consumption from `material_consumption` for the scoped `raw_material_id`, `finished_product_id`, `production_order_id`, or `cost_centre_id`.

### Production-related consumption

Link via `material_consumption.production_order_id` → `production_order.production_order_id`.

### BOM / planned vs actual

Compare planned requirements from `bill_of_material` to actual usage from `material_consumption` for the same `finished_product_id` and `raw_material_id`.

**Material variance (when both sides exist):**

```
Material Variance = Actual Consumption − Planned/BOM Quantity
```

Use the same `product_id` string identifiers on both sides. Do not compute if BOM or consumption data is absent for the scope.

---

## Product costing

### Standard product costing

`product_cost` contains finished-product standard costing information, keyed by `finished_product_id`.

### Documented cost components

The project documents these standard cost components for finished products:

- Direct Raw Material Cost
- Direct Labour Cost
- Machine Extrusion Cost
- Utilities & Power Cost
- Quality Assurance & Testing Cost
- Packaging & Bundling Cost
- Manufacturing Overhead Allocation

Report component breakdown only when query results expose these values. Do not invent component column names beyond what query results confirm.

### Actual vs standard

When both actual and standard product cost exist for the same finished product:

1. Report each value.
2. Compute Cost Variance using the confirmed formula.
3. Prefer stored variance if present for the scope.

### Cost variance interpretation

State factually: "Actual cost exceeds standard by [amount]" or "Actual cost is below standard by [amount]." Do not assign root cause unless supported by additional query data.

---

## Cost centre allocation

`cost_centre_allocation` links procurement receipts to cost centres:

- `cost_centre_allocation.grn_line_id` → `goods_receipt_note_line.grn_line_id`
- `cost_centre_allocation.cost_centre_id` → `cost_centre.cost_centre_id`

Use when questions connect received materials to cost centre allocation.

---

## Aggregation and data quality

- **Multiple transactions:** Sum within the same `product_id` / `warehouse_id` scope; deduplicate by `transaction_id`.
- **Cumulative quantities:** Sum chronologically for period-end balance.
- **Negative balances:** Report factually; do not clamp to zero unless data convention requires it.
- **Missing movement category:** Treat as zero only when confirmed no activity; otherwise note the category as missing.

---

## Rules of conduct

1. Use documented tables, VARCHAR identifiers, and relationships only.
2. Resolve product names to `product_id` strings before joining.
3. Prefer stored balances, `pending_quantity`, and stored variance over recalculation when authoritative.
4. Database access remains **read-only**.

## Out of scope

- SQL generation and MCP execution.
- Procurement three-way match (procurement-reconciliation skill).
- Liquidity ratios (financial-ratios skill).
- General non-inventory formulas (financial-formulas skill).
- Response formatting (finance-response skill).
