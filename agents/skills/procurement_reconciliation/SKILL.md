---
name: procurement-reconciliation
description: Guides procurement tracing and three-way matching using the CFO Analysis Industry Database tables, relationships, and confirmed fields. Use when analyzing purchase orders, GRNs, supplier invoices, quantity/price/amount variances, or reconciliation status.
---

# Procurement & 3-Way Reconciliation

Procurement analysis and three-way matching rules for the Finance Agent. Covers **procurement flow, matching, and variance identification**. Does not execute SQL, route requests, or format final responses.

## Confirmed procurement flow

```
purchase_order
  → purchase_order_line
    → goods_receipt_note
      → goods_receipt_note_line
        → supplier_invoice
          → supplier_invoice_line
            → reconciliation
```

Related entities used in joins: `vendor`, `warehouse`, `plant`, `cost_centre`, `product`, `cost_centre_allocation`.

## Confirmed relationships

| From | To | Join key |
|------|----|----------|
| `purchase_order_line` | `purchase_order` | `po_id` |
| `purchase_order_line` | `product` | `product_id` |
| `purchase_order` | `vendor` | `vendor_id` |
| `purchase_order` | `warehouse` | `warehouse_id` |
| `purchase_order` | `plant` | `plant_id` |
| `purchase_order` | `cost_centre` | `cost_centre_id` |
| `goods_receipt_note` | `purchase_order` | `po_id` |
| `goods_receipt_note` | `vendor` | `vendor_id` |
| `goods_receipt_note` | `warehouse` | `warehouse_id` |
| `goods_receipt_note_line` | `goods_receipt_note` | `grn_id` |
| `goods_receipt_note_line` | `purchase_order_line` | `po_line_id` |
| `goods_receipt_note_line` | `product` | `product_id` |
| `supplier_invoice` | `goods_receipt_note` | `grn_id` |
| `supplier_invoice` | `purchase_order` | `po_id` |
| `supplier_invoice` | `vendor` | `vendor_id` |
| `supplier_invoice` | `product` | `product_id` |
| `supplier_invoice_line` | `supplier_invoice` | `invoice_id` |
| `supplier_invoice_line` | `goods_receipt_note_line` | `grn_line_id` |
| `supplier_invoice_line` | `purchase_order_line` | `po_line_id` |
| `supplier_invoice_line` | `product` | `product_id` |
| `reconciliation` | `purchase_order` | `po_id` |
| `reconciliation` | `goods_receipt_note` | `grn_id` |
| `reconciliation` | `supplier_invoice` | `invoice_id` |
| `cost_centre_allocation` | `goods_receipt_note_line` | `grn_line_id` |
| `cost_centre_allocation` | `cost_centre` | `cost_centre_id` |

## Confirmed identifiers

All VARCHAR/TEXT strings — never use integer IDs.

| Entity | Primary key | Example format |
|--------|-------------|----------------|
| `purchase_order` | `po_id` | `PO-000001` |
| `purchase_order_line` | `po_line_id` | (string) |
| `goods_receipt_note` | `grn_id` | `GRN-000001` |
| `goods_receipt_note_line` | `grn_line_id` | (string) |
| `supplier_invoice` | `invoice_id` | `INV-000001` |
| `supplier_invoice_line` | `invoice_line_id` | (string) |
| `reconciliation` | `reconciliation_id` | (string) |
| `vendor` | `vendor_id` | `VEN-0001` |
| `product` | `product_id` | `PROD-0001` |

**Product resolution:** When the user says "Product 1" or a product name, resolve via the `product` table first, then use the string `product_id` in subsequent joins. Never use `WHERE product_id = 1`.

## Confirmed procurement fields

### purchase_order

`po_id`, `po_number`, `company_id`, `vendor_id`, `plant_id`, `warehouse_id`, `cost_centre_id`, `po_date`, `expected_delivery_date`, `subtotal`, `discount_amount`, `cgst_amount`, `sgst_amount`, `igst_amount`, `freight_amount`, `total_amount`, `status`

### purchase_order_line

`po_line_id`, `po_id`, `product_id`, `ordered_quantity`, `unit_price`, `received_quantity`, `invoiced_quantity`, `pending_quantity`, `status`

### goods_receipt_note

`grn_id`, `grn_number`, `po_id`, `vendor_id`, `warehouse_id`, `status`

**Do not assume `grn_date`.** For "first GRN" questions, order by `grn_id ASC LIMIT 1`.

### goods_receipt_note_line

`grn_line_id`, `grn_id`, `po_line_id`, `product_id`, `received_quantity`, `accepted_quantity`, `rejected_quantity`, `damaged_quantity`

### supplier_invoice

`invoice_id`, `invoice_number`, `po_id`, `grn_id`, `vendor_id`, `product_id`, `invoice_amount`, `status`

**`invoice_amount` is stored directly** on `supplier_invoice`. Do not assume `total_amount` exists. Query `invoice_amount` when the invoice is identified instead of recalculating from lines.

### supplier_invoice_line

`invoice_line_id`, `invoice_id`, `po_line_id`, `grn_line_id`, `product_id`, `hsn_sac_code`, `description`, `uom_id`, `invoiced_quantity`, `unit_price`, `discount_amount`, `taxable_amount`, `tax_percent`, `tax_amount`, `gl_account_id`, `matched_quantity`, `variance_quantity`, `variance_amount`, `matching_status`

**Do not assume `line_total` exists.**

---

## Tracing a procurement transaction

1. **Resolve identifiers** — map user references to documented keys (`po_number` → `po_id`, product name → `product_id`, etc.).
2. **Anchor** at the document or line the user asked about.
3. **Follow joins** using the relationship table above.
4. **Aggregate at the correct grain** — line-level for line variances, document-level for totals.
5. **State gaps** when a leg has no rows (PO without GRN, GRN without invoice).

---

## Confirmed procurement formulas

Apply via the financial-formulas skill:

| Metric | Formula | Primary source |
|--------|---------|----------------|
| **PO Line Value** | `ordered_quantity × unit_price` | `purchase_order_line` |
| **Accepted GRN Quantity** | `received_quantity − damaged_quantity − rejected_quantity` (prefer stored `accepted_quantity`) | `goods_receipt_note_line` |
| **Remaining PO Quantity** | `ordered_quantity − cumulative accepted quantity` (prefer stored `pending_quantity`) | `purchase_order_line` + GRN lines |
| **Invoice Line Value** | `invoiced_quantity × unit_price` | `supplier_invoice_line` |
| **Invoice Outstanding** | `net payable − paid amount` (payment columns not documented; use stored `invoice_amount` when outstanding cannot be computed) | `supplier_invoice` |

---

## Three-way matching

Compare **Purchase Order**, **Goods Receipt Note**, and **Supplier Invoice** for the same procurement scope (`po_id`, `po_line_id`, `grn_id`, `invoice_id`, `product_id`).

### Quantity matching

| Comparison | Procedure |
|------------|-----------|
| **Ordered vs received** | `purchase_order_line.ordered_quantity` vs cumulative accepted GRN quantity for the same `po_line_id`. |
| **Received vs invoiced** | Accepted GRN quantity vs `supplier_invoice_line.invoiced_quantity` or `purchase_order_line.invoiced_quantity`. |
| **Partial receipt** | Use `pending_quantity` or Remaining PO Quantity for open order; match invoice against received quantity separately. |
| **Partial invoicing** | Compare invoiced to received; quantify uninvoiced received quantity. |
| **Over-receipt** | Negative remaining/pending quantity; flag factually. |

**Quantity variances:**

- Order vs receipt: `Accepted GRN Quantity − ordered_quantity`
- Receipt vs invoice: `invoiced_quantity − Accepted GRN Quantity`
- **Prefer stored** `supplier_invoice_line.variance_quantity` when present for the line.

### Price matching

Compare `purchase_order_line.unit_price` to `supplier_invoice_line.unit_price` for the same `po_line_id` / `product_id`.

- `Price variance = invoice unit_price − PO unit_price`
- Extended impact: `Price variance × invoiced_quantity` at line level.

Respect `uom_id` — do not compare across mismatched units.

### Amount matching

- PO baseline: PO Line Value (`ordered_quantity × unit_price`)
- Invoice line: Invoice Line Value (`invoiced_quantity × unit_price`) or line tax components (`taxable_amount`, `tax_amount`, `discount_amount`) when the question requires tax breakdown
- Document total: stored `supplier_invoice.invoice_amount`
- **Prefer stored** `supplier_invoice_line.variance_amount` when present

### Vendor, material, and tax differences

Compare when documented fields exist across linked records:

- **Vendor mismatch:** `purchase_order.vendor_id` vs `goods_receipt_note.vendor_id` vs `supplier_invoice.vendor_id`
- **Material mismatch:** `product_id` across PO line, GRN line, invoice line
- **Tax-rate difference:** `supplier_invoice_line.tax_percent` and `tax_amount` vs PO tax fields (`cgst_amount`, `sgst_amount`, `igst_amount` on `purchase_order`)

Flag mismatches factually; do not infer tax rules beyond stored values.

---

## Reconciliation records

### reconciliation table

Links `po_id`, `grn_id`, and `invoice_id` via `reconciliation_id`. Use for document-level reconciliation status when rows exist.

### supplier_invoice_line stored matching fields

| Field | Use |
|-------|-----|
| `matching_status` | Line-level match / variance / exception status |
| `matched_quantity` | Quantity successfully matched |
| `variance_quantity` | Stored quantity variance |
| `variance_amount` | Stored amount variance |

| Situation | Handling |
|-----------|----------|
| **Matched** | Report `matching_status` and aligned IDs (`po_id`, `grn_id`, `invoice_id`, line IDs). |
| **Variance** | Report variance type and stored or calculated variance values. |
| **Exception** | Report status from `matching_status` or reconciliation record; do not invent exception codes. |

If no reconciliation row exists, perform logical three-way comparison from PO/GRN/invoice fields and state that no stored reconciliation record was found.

Project documentation also supports analysis of: quantity mismatches, price mismatches, amount mismatches, material/product mismatches, vendor mismatches, tax-rate differences, matched records, variance records, and exception records.

---

## Aggregation rules

- **Multiple PO lines:** Variance per line first; roll up only when requested.
- **Multiple GRNs per PO line:** Sum accepted quantities across all `goods_receipt_note_line` rows for the same `po_line_id` before comparing to order or invoice.
- **Multiple invoice lines:** Sum at matching grain using `po_line_id` / `grn_line_id` before comparison.
- **Avoid double-counting:** Deduplicate by `po_line_id`, `grn_line_id`, or `invoice_line_id`.

---

## Partial receipts, partial invoicing, and over-receipts

| Scenario | Approach |
|----------|----------|
| Partial receipt | `pending_quantity` or Remaining PO Quantity shows open order; reconcile invoice against received quantity. |
| Over-receipt | Negative `pending_quantity` or remaining quantity; flag over-receipt. |
| Partial invoice | Invoiced < received — quantify uninvoiced received quantity using `invoiced_quantity` vs accepted GRN quantity. |
| Invoice before receipt | Invoice exists without matching GRN — report as exception. |

---

## Rules of conduct

1. Use documented tables, columns, and VARCHAR identifiers only.
2. Do not assume `grn_date`, `line_total`, or `supplier_invoice.total_amount`.
3. Prefer stored `invoice_amount`, `pending_quantity`, `accepted_quantity`, and line variance fields when authoritative.
4. Do not declare a match unless data aligns or `matching_status` confirms it.
5. Database access remains **read-only**.

## Out of scope

- SQL generation and MCP execution.
- General formulas (financial-formulas skill).
- Inventory and product costing (inventory-costing skill).
- Response formatting (finance-response skill).
