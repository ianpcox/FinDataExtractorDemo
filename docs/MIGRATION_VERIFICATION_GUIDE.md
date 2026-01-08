# Migration Verification Guide

## Overview

This guide explains how to verify that the line items database migration was successful and that data integrity is maintained.

## Quick Verification

### Step 1: Run the Migration

```bash
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade 20251223_add_fields -> 7a7490408ff1, create_line_items_table_and_migrate_data
```

### Step 2: Verify Migration

```bash
python scripts/verify_migration_simple.py
```

This script checks:
- ✓ `line_items` table exists
- ✓ Indexes are created
- ✓ Line items are migrated from JSON
- ✓ Data integrity (JSON vs table comparison)
- ✓ Sample line item data

## Detailed Verification

### 1. Check Table Exists

```bash
sqlite3 findataextractor_demo.db ".tables"
```

Should show `line_items` in the list.

### 2. Check Table Structure

```bash
sqlite3 findataextractor_demo.db "PRAGMA table_info(line_items);"
```

Should show all columns: `id`, `invoice_id`, `line_number`, `description`, `amount`, etc.

### 3. Count Line Items

```bash
sqlite3 findataextractor_demo.db "SELECT COUNT(*) FROM line_items;"
```

### 4. Count Invoices with Line Items

```bash
sqlite3 findataextractor_demo.db "SELECT COUNT(DISTINCT invoice_id) FROM line_items;"
```

### 5. Compare JSON vs Table

```bash
sqlite3 findataextractor_demo.db "
SELECT 
    i.id,
    (SELECT COUNT(*) FROM json_each(i.line_items)) as json_count,
    (SELECT COUNT(*) FROM line_items li WHERE li.invoice_id = i.id) as table_count
FROM invoices i
WHERE i.line_items IS NOT NULL
LIMIT 10;
"
```

Counts should match for each invoice.

### 6. Sample Line Item Data

```bash
sqlite3 findataextractor_demo.db "
SELECT invoice_id, line_number, description, amount
FROM line_items
ORDER BY invoice_id, line_number
LIMIT 5;
"
```

## Python Verification Script

For comprehensive verification, use the full Python script:

```bash
python scripts/test_migration_and_verify.py
```

This script (requires virtual environment):
1. Checks database state
2. Verifies migration
3. Verifies data integrity
4. Tests ORM access
5. Tests aggregation validation

## Verification Checklist

- [ ] Migration runs without errors
- [ ] `line_items` table exists
- [ ] Indexes are created (`ix_line_items_invoice_id`, `ix_line_items_line_number`)
- [ ] Line items are migrated from JSON to table
- [ ] JSON and table counts match for each invoice
- [ ] ORM can access line items via relationship
- [ ] Pydantic conversion works correctly
- [ ] Aggregation validation works with migrated data

## Common Issues

### Issue: Table doesn't exist after migration

**Solution**: Check migration ran successfully:
```bash
alembic current
alembic history
```

### Issue: Line items not migrated

**Possible causes**:
- No invoices with line_items JSON in database
- JSON format is invalid
- Migration encountered errors

**Solution**: Check for invoices with line items:
```bash
sqlite3 findataextractor_demo.db "SELECT COUNT(*) FROM invoices WHERE line_items IS NOT NULL;"
```

### Issue: Count mismatch between JSON and table

**Possible causes**:
- Migration partially failed
- Data was modified after migration
- JSON format issues

**Solution**: Re-run migration or manually verify specific invoices.

### Issue: ORM access fails

**Possible causes**:
- Relationship not loaded
- Model imports incorrect
- Database session issues

**Solution**: Verify model imports and relationship configuration.

## Rollback (if needed)

If you need to rollback the migration:

```bash
alembic downgrade -1
```

This will:
- Migrate data back to JSON column
- Drop the `line_items` table
- Restore JSON-based storage

**Warning**: Only rollback if necessary. Data will be migrated back to JSON format.

## Post-Migration Testing

After migration, test:

1. **Create new invoice with line items**:
   ```python
   from src.models.invoice import Invoice, LineItem
   from src.services.db_service import DatabaseService
   
   invoice = Invoice(...)
   invoice.line_items = [LineItem(...), ...]
   await DatabaseService.save_invoice(invoice, db=session)
   ```

2. **Load invoice with line items**:
   ```python
   invoice = await DatabaseService.get_invoice(invoice_id, db=session)
   assert len(invoice.line_items) > 0
   ```

3. **Test aggregation validation**:
   ```python
   from src.validation.aggregation_validator import AggregationValidator
   
   validation = AggregationValidator.get_validation_summary(invoice)
   assert validation["all_valid"]
   ```

## Performance Verification

After migration, verify performance:

```bash
pytest tests/integration/test_large_invoice_performance.py::TestLargeInvoicePerformance::test_database_save_performance -v
pytest tests/integration/test_large_invoice_performance.py::TestLargeInvoicePerformance::test_database_load_performance -v
```

## Success Criteria

Migration is successful if:
- ✓ All checks pass in verification script
- ✓ Line items can be saved to table
- ✓ Line items can be loaded from table
- ✓ ORM relationship works
- ✓ Aggregation validation works
- ✓ Performance is acceptable

## Next Steps

After successful migration:
1. Monitor production usage
2. Track performance metrics
3. Consider removing JSON column in future migration
4. Update any remaining code that uses JSON column
