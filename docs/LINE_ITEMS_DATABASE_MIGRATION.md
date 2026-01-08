# Line Items Database Migration

## Overview

This document describes the migration from storing line items as JSON in the `invoices` table to a separate `line_items` table with a foreign key relationship.

## Migration Details

### Migration File
- **File**: `alembic/versions/7a7490408ff1_create_line_items_table_and_migrate_data.py`
- **Revision ID**: `7a7490408ff1`
- **Depends on**: `20251223_add_comprehensive_invoice_fields`

### What the Migration Does

1. **Creates the `line_items` table** with:
   - Primary key: `id` (UUID string)
   - Foreign key: `invoice_id` (references `invoices.id` with CASCADE delete)
   - All line item fields (line_number, description, quantity, unit_price, amount, taxes, etc.)
   - Indexes on `invoice_id` and `(invoice_id, line_number)`

2. **Migrates existing data** from JSON column to the new table:
   - Reads `line_items` JSON from all invoices
   - Parses JSON and creates corresponding rows in `line_items` table
   - Handles decimal string conversion properly
   - Generates UUIDs for each line item

3. **Keeps JSON column** for backward compatibility:
   - The `line_items` JSON column remains in the `invoices` table
   - This allows gradual migration and rollback if needed
   - Can be removed in a future migration after all code is updated

### Downgrade

The downgrade function:
- Migrates data back from `line_items` table to JSON column
- Drops indexes and the `line_items` table
- Restores original JSON-based storage

## Code Changes

### 1. Database Models

**`src/models/db_models.py`**:
- Added `relationship` to `Invoice` model for `line_items_relationship`
- Uses `lazy="selectin"` for eager loading by default

**`src/models/line_item_db_models.py`**:
- Already existed as a proposed model
- Now actively used after migration

### 2. Database Utilities

**`src/models/db_utils.py`**:
- Added `_get_line_items_from_db()` function that:
  - First tries to load from `line_items_relationship` (table)
  - Falls back to JSON column if relationship not loaded or empty
  - Supports migration period where data may be in either location

**`src/models/db_utils_line_items.py`** (NEW):
- `save_line_items_to_table()`: Saves line items to table, replacing existing ones
- `get_line_items_from_table()`: Retrieves line items from table

### 3. Database Service

**`src/services/db_service.py`**:
- Updated `save_invoice()` to call `save_line_items_to_table()` when line items are provided
- Line items are now saved to the table instead of (or in addition to) JSON

### 4. Alembic Configuration

**`alembic/env.py`**:
- Added import for `LineItem` model so Alembic can detect it

## Migration Strategy

### Phase 1: Dual Storage (Current)
- Line items saved to both table and JSON column
- Reading prefers table, falls back to JSON
- Allows gradual migration without breaking existing code

### Phase 2: Table-Only (Future)
- Remove JSON column writes (keep column for read compatibility)
- All new line items go to table only
- Migrate any remaining JSON-only line items

### Phase 3: Cleanup (Future)
- Remove JSON column entirely
- Update all code to use table only
- Remove fallback logic

## Running the Migration

### Prerequisites
1. Backup your database
2. Ensure all code changes are deployed
3. Test in a development environment first

### Steps

1. **Review the migration**:
   ```bash
   # Check migration file
   cat alembic/versions/7a7490408ff1_create_line_items_table_and_migrate_data.py
   ```

2. **Check current revision**:
   ```bash
   alembic current
   ```

3. **Run migration**:
   ```bash
   alembic upgrade head
   ```

4. **Verify migration**:
   ```bash
   # Check that line_items table exists
   sqlite3 findataextractor_demo.db ".tables"
   
   # Check line items were migrated
   sqlite3 findataextractor_demo.db "SELECT COUNT(*) FROM line_items;"
   ```

5. **Test application**:
   - Create a new invoice with line items
   - Verify line items are saved to table
   - Verify line items can be retrieved
   - Test aggregation validation

### Rollback

If you need to rollback:

```bash
alembic downgrade -1
```

This will:
- Migrate data back to JSON column
- Drop the `line_items` table
- Restore JSON-based storage

## Benefits

1. **Normalized Data Structure**: Line items in a separate table follow database normalization best practices
2. **Better Query Performance**: Can query line items directly without parsing JSON
3. **Easier Aggregation**: SQL can sum line items directly
4. **Data Integrity**: Foreign key constraints ensure referential integrity
5. **Scalability**: Better performance for invoices with many line items
6. **Metrics Support**: Enables line item-specific metrics and reporting

## Testing

After migration, verify:

1. **Data Integrity**:
   - All line items migrated correctly
   - No data loss
   - Decimal values preserved

2. **Functionality**:
   - Creating invoices with line items works
   - Reading invoices loads line items correctly
   - Updating invoices updates line items
   - Deleting invoices cascades to line items

3. **Performance**:
   - Queries are faster
   - Aggregation validation works
   - Line item metrics work

## Troubleshooting

### Migration Fails
- Check database logs for errors
- Verify JSON format is valid
- Check decimal string parsing

### Line Items Not Appearing
- Verify relationship is loaded: `selectinload(Invoice.line_items_relationship)`
- Check fallback to JSON is working
- Verify `_get_line_items_from_db()` is being called

### Performance Issues
- Ensure indexes are created
- Check query plans
- Consider adding additional indexes if needed

## Future Enhancements

1. **Remove JSON Column**: After all code is updated, remove `line_items` JSON column
2. **Add Constraints**: Add check constraints for line_number uniqueness per invoice
3. **Optimize Indexes**: Add composite indexes for common query patterns
4. **Bulk Operations**: Add bulk insert/update functions for performance
