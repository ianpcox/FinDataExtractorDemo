# Purge Invoices Guide

## Overview

Scripts to safely purge/delete invoices from the database. Supports multiple deletion strategies with safety confirmations.

## Scripts Available

### 1. `scripts/purge_invoices_simple.py` (Recommended)
Simple SQLite-based script that works without virtual environment.

### 2. `scripts/purge_invoices.py` (Full-featured)
Full async SQLAlchemy-based script with more features.

## Usage

### Delete All Invoices
```bash
# With confirmation prompt
python scripts/purge_invoices_simple.py --all

# Skip confirmation (use with caution!)
python scripts/purge_invoices_simple.py --all --confirm
```

### Delete by Status
```bash
# Delete all invoices with "processing" status
python scripts/purge_invoices_simple.py --status processing

# Delete all invoices with "extracted" status
python scripts/purge_invoices_simple.py --status extracted
```

### Delete by Date
```bash
# Delete invoices older than 30 days
python scripts/purge_invoices_simple.py --older-than 30

# Delete invoices older than 7 days
python scripts/purge_invoices_simple.py --older-than 7
```

### Delete Specific Invoices
```bash
# Delete specific invoices by ID
python scripts/purge_invoices_simple.py --ids invoice-id-1 invoice-id-2 invoice-id-3
```

### Specify Database
```bash
# Use a different database file
python scripts/purge_invoices_simple.py --all --db findataextractor_demo.db
```

## Safety Features

1. **Confirmation Prompts**: By default, requires confirmation before deleting
2. **Preview**: Shows what will be deleted before deletion
3. **Cascade Delete**: Automatically deletes associated line items
4. **Status Report**: Shows current state before and after deletion

## What Gets Deleted

When you delete invoices:
- ✅ Invoice records are deleted
- ✅ Line items are automatically deleted (CASCADE)
- ✅ All related data is removed

## Examples

### Clean up test data
```bash
# Delete all invoices (useful for testing)
python scripts/purge_invoices_simple.py --all --confirm
```

### Clean up old invoices
```bash
# Delete invoices older than 90 days
python scripts/purge_invoices_simple.py --older-than 90
```

### Clean up failed extractions
```bash
# Delete invoices stuck in processing
python scripts/purge_invoices_simple.py --status processing --confirm
```

## Current Database State

After running the purge script, you'll see:
```
================================================================================
CURRENT DATABASE STATE
================================================================================
Total invoices: 0
Total line items: 0
```

## Warnings

⚠️ **WARNING**: This permanently deletes data. There is no undo!

- Always backup your database before purging
- Use `--dry-run` (in full script) to preview changes
- Double-check what you're deleting
- Consider exporting important data first

## Backup Before Purging

```bash
# Backup database before purging
cp findataextractor.db findataextractor.db.backup

# Or use SQLite backup
sqlite3 findataextractor.db ".backup findataextractor.db.backup"
```

## Verification

After purging, verify:
```bash
# Check invoice count
sqlite3 findataextractor.db "SELECT COUNT(*) FROM invoices;"

# Check line item count
sqlite3 findataextractor.db "SELECT COUNT(*) FROM line_items;"

# Verify migration still works
python scripts/verify_migration_simple.py findataextractor.db
```
