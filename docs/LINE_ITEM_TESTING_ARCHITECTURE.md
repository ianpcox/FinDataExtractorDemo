# Line Item Testing Architecture

## Overview

Line items have a 1:Many relationship with invoices and require nested testing to validate:
1. **Line Item Extraction**: Individual line item fields (quantity, unit_price, amount, taxes per line)
2. **Aggregation Validation**: Invoice-level totals match sum of line item values
3. **Data Integrity**: Foreign key relationship between Invoice and LineItem tables

## Current State

### Database Structure
- **Invoice Table**: Contains `line_items` as JSON column
- **No Separate LineItem Table**: Line items are embedded in Invoice record
- **No Foreign Key Relationship**: Line items are not normalized

### Test Coverage
- Basic line item extraction tests exist
- **No aggregation validation tests**
- **No nested test structure for line items**
- **No tests verifying invoice totals = sum(line item amounts)**

## Proposed Architecture

### 1. Database Structure (Future Migration)

```sql
-- Invoice table (high-level aggregated data)
CREATE TABLE invoices (
    id VARCHAR(36) PRIMARY KEY,
    invoice_number VARCHAR(100),
    invoice_date DATE,
    subtotal NUMERIC(18, 2),
    tax_amount NUMERIC(18, 2),
    gst_amount NUMERIC(18, 2),
    hst_amount NUMERIC(18, 2),
    qst_amount NUMERIC(18, 2),
    pst_amount NUMERIC(18, 2),
    total_amount NUMERIC(18, 2),
    -- ... other invoice fields
);

-- Line Item table (1:Many relationship)
CREATE TABLE line_items (
    id VARCHAR(36) PRIMARY KEY,
    invoice_id VARCHAR(36) NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantity NUMERIC(18, 4),
    unit_price NUMERIC(18, 4),
    amount NUMERIC(18, 2) NOT NULL,
    tax_rate NUMERIC(5, 4),
    tax_amount NUMERIC(18, 2),
    gst_amount NUMERIC(18, 2),
    pst_amount NUMERIC(18, 2),
    qst_amount NUMERIC(18, 2),
    combined_tax NUMERIC(18, 2),
    confidence FLOAT DEFAULT 0.0,
    -- ... other line item fields
    UNIQUE(invoice_id, line_number)
);

CREATE INDEX idx_line_items_invoice_id ON line_items(invoice_id);
```

### 2. Test Structure

#### Tier 1: Invoice-Level Tests
- Extract high-level invoice fields (invoice_number, dates, vendor, customer)
- Extract aggregated financial totals (subtotal, tax_amount, total_amount)

#### Tier 2: Line Item Tests (Nested)
- Extract individual line items
- Validate line item fields (description, quantity, unit_price, amount)
- Validate per-line-item taxes (gst_amount, pst_amount, qst_amount per line)

#### Tier 3: Aggregation Validation Tests
- **Subtotal Validation**: `invoice.subtotal == sum(line_item.amount)`
- **Tax Aggregation**: 
  - `invoice.gst_amount == sum(line_item.gst_amount)`
  - `invoice.pst_amount == sum(line_item.pst_amount)`
  - `invoice.qst_amount == sum(line_item.qst_amount)`
  - `invoice.tax_amount == sum(line_item.tax_amount)` OR `sum(line_item.gst_amount + pst_amount + qst_amount)`
- **Total Validation**: `invoice.total_amount == invoice.subtotal + invoice.tax_amount + invoice.shipping_amount + invoice.handling_fee - invoice.discount_amount`

### 3. Test Data Structure

```python
# Invoice-level data
invoice_data = {
    "invoice_number": "INV-001",
    "subtotal": 1000.00,
    "gst_amount": 50.00,
    "pst_amount": 70.00,
    "tax_amount": 120.00,
    "total_amount": 1120.00
}

# Line item data (nested)
line_items_data = [
    {
        "line_number": 1,
        "description": "Item A",
        "quantity": 10,
        "unit_price": 50.00,
        "amount": 500.00,
        "gst_amount": 25.00,
        "pst_amount": 35.00,
        "tax_amount": 60.00
    },
    {
        "line_number": 2,
        "description": "Item B",
        "quantity": 10,
        "unit_price": 50.00,
        "amount": 500.00,
        "gst_amount": 25.00,
        "pst_amount": 35.00,
        "tax_amount": 60.00
    }
]

# Aggregation validation
assert invoice_data["subtotal"] == sum(item["amount"] for item in line_items_data)  # 1000.00
assert invoice_data["gst_amount"] == sum(item["gst_amount"] for item in line_items_data)  # 50.00
assert invoice_data["pst_amount"] == sum(item["pst_amount"] for item in line_items_data)  # 70.00
assert invoice_data["tax_amount"] == sum(item["tax_amount"] for item in line_items_data)  # 120.00
```

## Implementation Plan

### Phase 1: Test Structure (Current)
1. ✅ Create nested test structure for line items
2. ✅ Add aggregation validation tests
3. ✅ Update metrics to handle line items separately

### Phase 2: Database Migration (Future)
1. Create separate `line_items` table
2. Migrate existing JSON line items to table
3. Update ORM models and relationships
4. Update extraction service to write to both tables

### Phase 3: Metrics Enhancement
1. Per-line-item metrics (precision, recall, F1)
2. Aggregation accuracy metrics
3. Line item coverage metrics

## Benefits

1. **Data Integrity**: Foreign key ensures line items belong to invoices
2. **Query Efficiency**: Can query line items without loading entire invoice JSON
3. **Aggregation Validation**: Enforces consistency between invoice totals and line item sums
4. **Test Clarity**: Nested structure makes it clear what's being tested
5. **Scalability**: Separate table is more efficient for large invoices with many line items
