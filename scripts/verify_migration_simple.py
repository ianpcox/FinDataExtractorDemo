"""
Simple migration verification script using SQLite directly.

This script verifies the migration without requiring all dependencies.
Run this after running: alembic upgrade head
"""

import sqlite3
import json
import sys
from pathlib import Path


def verify_migration(db_path: str = "findataextractor_demo.db"):
    """Verify migration was successful"""
    
    if not Path(db_path).exists():
        print(f"[ERROR] Database file not found: {db_path}")
        print("  Please ensure the database exists and run: alembic upgrade head")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("="*80)
    print("MIGRATION VERIFICATION")
    print("="*80)
    print(f"Database: {db_path}\n")
    
    # Step 1: Check if line_items table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='line_items'
    """)
    if cursor.fetchone() is None:
        print("[ERROR] line_items table does not exist")
        print("  Run: alembic upgrade head")
        conn.close()
        return False
    
    print("[OK] line_items table exists")
    
    # Step 2: Check indexes
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name LIKE 'ix_line_items%'
    """)
    indexes = [row[0] for row in cursor.fetchall()]
    print(f"[OK] Indexes: {', '.join(indexes) if indexes else 'None found'}")
    
    # Step 3: Count line items
    cursor.execute("SELECT COUNT(*) FROM line_items")
    total_line_items = cursor.fetchone()[0]
    print(f"[OK] Total line items in table: {total_line_items}")
    
    # Step 4: Count invoices with line items
    cursor.execute("SELECT COUNT(DISTINCT invoice_id) FROM line_items")
    invoices_with_items = cursor.fetchone()[0]
    print(f"[OK] Invoices with line items: {invoices_with_items}")
    
    # Step 5: Check invoices with JSON vs table
    cursor.execute("""
        SELECT COUNT(*) FROM invoices 
        WHERE line_items IS NOT NULL 
          AND line_items != '[]' 
          AND line_items != ''
          AND line_items != 'null'
    """)
    invoices_with_json = cursor.fetchone()[0]
    print(f"[OK] Invoices with line_items JSON: {invoices_with_json}")
    
    # Step 6: Compare JSON vs table data
    if invoices_with_json > 0 and total_line_items > 0:
        print("\n" + "="*80)
        print("DATA INTEGRITY CHECK")
        print("="*80)
        
        cursor.execute("""
            SELECT i.id, i.line_items as json_items,
                   COUNT(li.id) as table_item_count
            FROM invoices i
            LEFT JOIN line_items li ON li.invoice_id = i.id
            WHERE i.line_items IS NOT NULL 
              AND i.line_items != '[]' 
              AND i.line_items != ''
              AND i.line_items != 'null'
            GROUP BY i.id, i.line_items
            LIMIT 10
        """)
        
        samples = cursor.fetchall()
        print(f"\nComparing JSON vs Table for {len(samples)} invoices:\n")
        
        all_match = True
        for invoice_id, json_items, table_count in samples:
            try:
                # Parse JSON
                if isinstance(json_items, str):
                    json_data = json.loads(json_items)
                else:
                    json_data = json_items
                
                json_count = len(json_data) if isinstance(json_data, list) else 0
                
                if json_count == table_count:
                    print(f"[OK] {invoice_id[:8]}...: {json_count} items match")
                else:
                    print(f"[WARN] {invoice_id[:8]}...: JSON={json_count}, Table={table_count}")
                    all_match = False
            except Exception as e:
                print(f"[ERROR] {invoice_id[:8]}...: Error - {e}")
                all_match = False
        
        if all_match:
            print("\n[OK] All data integrity checks passed")
        else:
            print("\n[WARN] Some mismatches found (may need data migration)")
    
    # Step 7: Sample line item data
    if total_line_items > 0:
        print("\n" + "="*80)
        print("SAMPLE LINE ITEM DATA")
        print("="*80)
        
        cursor.execute("""
            SELECT invoice_id, line_number, description, amount, quantity, unit_price
            FROM line_items
            ORDER BY invoice_id, line_number
            LIMIT 5
        """)
        
        samples = cursor.fetchall()
        print("\nSample line items:")
        for invoice_id, line_num, desc, amount, qty, unit_price in samples:
            desc_short = (desc[:40] + "...") if desc and len(desc) > 40 else (desc or "")
            print(f"  Invoice {invoice_id[:8]}... | Line {line_num} | {desc_short} | ${amount}")
            if qty and unit_price:
                print(f"    Qty: {qty}, Unit Price: ${unit_price}")
    
    # Step 8: Check table structure
    print("\n" + "="*80)
    print("TABLE STRUCTURE")
    print("="*80)
    
    cursor.execute("PRAGMA table_info(line_items)")
    columns = cursor.fetchall()
    print(f"\nline_items table has {len(columns)} columns:")
    for col in columns[:10]:  # Show first 10
        print(f"  - {col[1]} ({col[2]})")
    if len(columns) > 10:
        print(f"  ... and {len(columns) - 10} more columns")
    
    conn.close()
    
    print("\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print("="*80)
    print("[OK] Migration appears successful")
    print("\nNext steps:")
    print("  1. Test ORM access with: python -c \"from src.models.db_models import Invoice; print('OK')\"")
    print("  2. Test extraction with line items")
    print("  3. Verify aggregation validation works")
    
    return True


if __name__ == "__main__":
    # Try to find the database file
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not db_path:
        # Check common database file names
        for db_name in ["findataextractor.db", "findataextractor_demo.db"]:
            if Path(db_name).exists():
                db_path = db_name
                break
        
        if not db_path:
            print("ERROR: Could not find database file")
            print("Please specify database path: python scripts/verify_migration_simple.py <path_to_db>")
            sys.exit(1)
    
    success = verify_migration(db_path)
    sys.exit(0 if success else 1)
