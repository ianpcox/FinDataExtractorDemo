"""
Simple script to purge invoices from database using SQLite directly.

WARNING: This will permanently delete data. Use with caution.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta


def purge_invoices(db_path: str, confirm: bool = False, status: str = None, 
                   older_than_days: int = None, invoice_ids: list = None):
    """Purge invoices from database"""
    
    if not Path(db_path).exists():
        print(f"ERROR: Database file not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Show current state
    print("="*80)
    print("CURRENT DATABASE STATE")
    print("="*80)
    
    cursor.execute("SELECT COUNT(*) FROM invoices")
    total_invoices = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM line_items")
    total_line_items = cursor.fetchone()[0]
    
    print(f"Total invoices: {total_invoices}")
    print(f"Total line items: {total_line_items}")
    
    if total_invoices == 0:
        print("\nNo invoices to delete.")
        conn.close()
        return True
    
    # Count by status
    cursor.execute("SELECT status, COUNT(*) FROM invoices GROUP BY status")
    status_counts = cursor.fetchall()
    print("\nInvoices by status:")
    for status, count in status_counts:
        print(f"  - {status}: {count}")
    
    # Determine what to delete
    if invoice_ids:
        # Delete specific invoices
        placeholders = ",".join("?" * len(invoice_ids))
        cursor.execute(f"SELECT COUNT(*) FROM invoices WHERE id IN ({placeholders})", invoice_ids)
        count = cursor.fetchone()[0]
        
        if count == 0:
            print(f"\nNo invoices found with specified IDs")
            conn.close()
            return True
        
        print(f"\nWill delete {count} invoices with specified IDs")
        if not confirm:
            response = input("Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Cancelled.")
                conn.close()
                return False
        
        # Delete line items
        cursor.execute(f"DELETE FROM line_items WHERE invoice_id IN ({placeholders})", invoice_ids)
        deleted_line_items = cursor.rowcount
        
        # Delete invoices
        cursor.execute(f"DELETE FROM invoices WHERE id IN ({placeholders})", invoice_ids)
        deleted_invoices = cursor.rowcount
        
    elif status:
        # Delete by status
        cursor.execute("SELECT COUNT(*) FROM invoices WHERE status = ?", (status,))
        count = cursor.fetchone()[0]
        
        if count == 0:
            print(f"\nNo invoices found with status: {status}")
            conn.close()
            return True
        
        print(f"\nWill delete {count} invoices with status: {status}")
        if not confirm:
            response = input("Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Cancelled.")
                conn.close()
                return False
        
        # Get invoice IDs
        cursor.execute("SELECT id FROM invoices WHERE status = ?", (status,))
        invoice_ids = [row[0] for row in cursor.fetchall()]
        
        # Delete line items
        if invoice_ids:
            placeholders = ",".join("?" * len(invoice_ids))
            cursor.execute(f"DELETE FROM line_items WHERE invoice_id IN ({placeholders})", invoice_ids)
            deleted_line_items = cursor.rowcount
        else:
            deleted_line_items = 0
        
        # Delete invoices
        cursor.execute("DELETE FROM invoices WHERE status = ?", (status,))
        deleted_invoices = cursor.rowcount
        
    elif older_than_days:
        # Delete older than N days
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        cursor.execute("SELECT COUNT(*) FROM invoices WHERE upload_date < ?", (cutoff_date,))
        count = cursor.fetchone()[0]
        
        if count == 0:
            print(f"\nNo invoices found older than {older_than_days} days")
            conn.close()
            return True
        
        print(f"\nWill delete {count} invoices older than {older_than_days} days")
        if not confirm:
            response = input("Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Cancelled.")
                conn.close()
                return False
        
        # Get invoice IDs
        cursor.execute("SELECT id FROM invoices WHERE upload_date < ?", (cutoff_date,))
        invoice_ids = [row[0] for row in cursor.fetchall()]
        
        # Delete line items
        if invoice_ids:
            placeholders = ",".join("?" * len(invoice_ids))
            cursor.execute(f"DELETE FROM line_items WHERE invoice_id IN ({placeholders})", invoice_ids)
            deleted_line_items = cursor.rowcount
        else:
            deleted_line_items = 0
        
        # Delete invoices
        cursor.execute("DELETE FROM invoices WHERE upload_date < ?", (cutoff_date,))
        deleted_invoices = cursor.rowcount
        
    else:
        # Delete all
        print(f"\nWill delete ALL {total_invoices} invoices and {total_line_items} line items")
        if not confirm:
            response = input("Are you sure? Type 'DELETE ALL' to confirm: ")
            if response != 'DELETE ALL':
                print("Cancelled.")
                conn.close()
                return False
        
        # Delete line items
        cursor.execute("DELETE FROM line_items")
        deleted_line_items = cursor.rowcount
        
        # Delete invoices
        cursor.execute("DELETE FROM invoices")
        deleted_invoices = cursor.rowcount
    
    conn.commit()
    
    print(f"\n[OK] Deleted {deleted_invoices} invoices and {deleted_line_items} line items")
    
    # Show final state
    cursor.execute("SELECT COUNT(*) FROM invoices")
    remaining_invoices = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM line_items")
    remaining_line_items = cursor.fetchone()[0]
    
    print(f"\nRemaining: {remaining_invoices} invoices, {remaining_line_items} line items")
    
    conn.close()
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Purge invoices from database")
    parser.add_argument(
        "--db",
        type=str,
        default="findataextractor.db",
        help="Database file path (default: findataextractor.db)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Delete all invoices"
    )
    parser.add_argument(
        "--status",
        type=str,
        help="Delete invoices with specific status"
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        help="Delete specific invoices by ID"
    )
    parser.add_argument(
        "--older-than",
        type=int,
        help="Delete invoices older than N days"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    # Find database file
    db_path = args.db
    if not Path(db_path).exists():
        # Try common names
        for name in ["findataextractor.db", "findataextractor_demo.db"]:
            if Path(name).exists():
                db_path = name
                break
    
    if not Path(db_path).exists():
        print(f"ERROR: Database file not found: {args.db}")
        print("Please specify the correct database path with --db")
        sys.exit(1)
    
    # Determine action
    if args.ids:
        success = purge_invoices(db_path, args.confirm, invoice_ids=args.ids)
    elif args.status:
        success = purge_invoices(db_path, args.confirm, status=args.status)
    elif args.older_than:
        success = purge_invoices(db_path, args.confirm, older_than_days=args.older_than)
    elif args.all:
        success = purge_invoices(db_path, args.confirm)
    else:
        print("No action specified. Use --help for options.")
        print("\nExamples:")
        print("  python scripts/purge_invoices_simple.py --all --confirm")
        print("  python scripts/purge_invoices_simple.py --status processing")
        print("  python scripts/purge_invoices_simple.py --older-than 30")
        print("  python scripts/purge_invoices_simple.py --ids invoice-id-1 invoice-id-2")
        sys.exit(1)
    
    sys.exit(0 if success else 1)
