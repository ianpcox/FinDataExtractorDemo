"""
Purge invoices from the database.

This script allows you to:
1. Delete all invoices (with confirmation)
2. Delete invoices by status
3. Delete invoices by date range
4. Delete specific invoices by ID

WARNING: This will permanently delete data. Use with caution.
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, delete, text
from sqlalchemy.pool import StaticPool

from src.models.database import Base
from src.models.db_models import Invoice as InvoiceDB
from src.config import settings


async def count_invoices(session: AsyncSession) -> dict:
    """Count invoices by status"""
    result = await session.execute(
        text("""
            SELECT status, COUNT(*) as count
            FROM invoices
            GROUP BY status
        """)
    )
    counts = {row[0]: row[1] for row in result.fetchall()}
    
    # Total count
    result = await session.execute(text("SELECT COUNT(*) FROM invoices"))
    total = result.scalar()
    
    return {"total": total, "by_status": counts}


async def count_line_items(session: AsyncSession) -> int:
    """Count line items"""
    result = await session.execute(text("SELECT COUNT(*) FROM line_items"))
    return result.scalar()


async def purge_all_invoices(session: AsyncSession, confirm: bool = False) -> int:
    """Delete all invoices from database"""
    if not confirm:
        raise ValueError("Must set confirm=True to purge all invoices")
    
    # Count before deletion
    result = await session.execute(text("SELECT COUNT(*) FROM invoices"))
    invoice_count = result.scalar()
    
    result = await session.execute(text("SELECT COUNT(*) FROM line_items"))
    line_item_count = result.scalar()
    
    print(f"Deleting {invoice_count} invoices and {line_item_count} line items...")
    
    # Delete line items first (though CASCADE should handle this)
    await session.execute(delete(LineItemDB))
    
    # Delete invoices
    await session.execute(delete(InvoiceDB))
    
    await session.commit()
    
    print(f"✓ Deleted {invoice_count} invoices and {line_item_count} line items")
    return invoice_count


async def purge_invoices_by_status(session: AsyncSession, status: str) -> int:
    """Delete invoices by status"""
    # Count before deletion
    result = await session.execute(
        text("SELECT COUNT(*) FROM invoices WHERE status = :status"),
        {"status": status}
    )
    count = result.scalar()
    
    if count == 0:
        print(f"No invoices found with status: {status}")
        return 0
    
    # Get invoice IDs
    result = await session.execute(
        text("SELECT id FROM invoices WHERE status = :status"),
        {"status": status}
    )
    invoice_ids = [row[0] for row in result.fetchall()]
    
    # Delete line items for these invoices
    if invoice_ids:
        await session.execute(
            text("DELETE FROM line_items WHERE invoice_id IN ({})".format(
                ",".join(f"'{id}'" for id in invoice_ids)
            ))
        )
    
    # Delete invoices
    await session.execute(
        text("DELETE FROM invoices WHERE status = :status"),
        {"status": status}
    )
    
    await session.commit()
    
    print(f"✓ Deleted {count} invoices with status: {status}")
    return count


async def purge_invoices_by_ids(session: AsyncSession, invoice_ids: List[str]) -> int:
    """Delete specific invoices by ID"""
    if not invoice_ids:
        return 0
    
    # Delete line items first
    placeholders = ",".join(f"'{id}'" for id in invoice_ids)
    await session.execute(
        text(f"DELETE FROM line_items WHERE invoice_id IN ({placeholders})")
    )
    
    # Delete invoices
    await session.execute(
        text(f"DELETE FROM invoices WHERE id IN ({placeholders})")
    )
    
    await session.commit()
    
    print(f"✓ Deleted {len(invoice_ids)} invoices")
    return len(invoice_ids)


async def purge_old_invoices(session: AsyncSession, days: int) -> int:
    """Delete invoices older than specified days"""
    cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    cutoff_date = cutoff_date - timedelta(days=days)
    
    # Count before deletion
    result = await session.execute(
        text("SELECT COUNT(*) FROM invoices WHERE upload_date < :cutoff"),
        {"cutoff": cutoff_date}
    )
    count = result.scalar()
    
    if count == 0:
        print(f"No invoices found older than {days} days")
        return 0
    
    # Get invoice IDs
    result = await session.execute(
        text("SELECT id FROM invoices WHERE upload_date < :cutoff"),
        {"cutoff": cutoff_date}
    )
    invoice_ids = [row[0] for row in result.fetchall()]
    
    # Delete line items
    if invoice_ids:
        placeholders = ",".join(f"'{id}'" for id in invoice_ids)
        await session.execute(
            text(f"DELETE FROM line_items WHERE invoice_id IN ({placeholders})")
        )
    
    # Delete invoices
    await session.execute(
        text("DELETE FROM invoices WHERE upload_date < :cutoff"),
        {"cutoff": cutoff_date}
    )
    
    await session.commit()
    
    print(f"✓ Deleted {count} invoices older than {days} days")
    return count


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Purge invoices from database")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Delete all invoices (requires --confirm)"
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
        help="Confirm deletion (required for --all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    args = parser.parse_args()
    
    # Create engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    TestingSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    try:
        async with TestingSessionLocal() as session:
            # Show current state
            print("="*80)
            print("CURRENT DATABASE STATE")
            print("="*80)
            
            counts = await count_invoices(session)
            line_item_count = await count_line_items(session)
            
            print(f"Total invoices: {counts['total']}")
            print(f"Total line items: {line_item_count}")
            print("\nInvoices by status:")
            for status, count in counts['by_status'].items():
                print(f"  - {status}: {count}")
            
            if args.dry_run:
                print("\n" + "="*80)
                print("DRY RUN MODE - No changes will be made")
                print("="*80)
            
            # Determine what to delete
            if args.all:
                if not args.confirm:
                    print("\nERROR: --confirm required when using --all")
                    print("This will delete ALL invoices. Use --confirm to proceed.")
                    return 1
                
                if args.dry_run:
                    print(f"\nWould delete: {counts['total']} invoices and {line_item_count} line items")
                else:
                    deleted = await purge_all_invoices(session, confirm=True)
                    print(f"\n✓ Purged {deleted} invoices")
            
            elif args.status:
                if args.dry_run:
                    result = await session.execute(
                        text("SELECT COUNT(*) FROM invoices WHERE status = :status"),
                        {"status": args.status}
                    )
                    count = result.scalar()
                    print(f"\nWould delete: {count} invoices with status '{args.status}'")
                else:
                    deleted = await purge_invoices_by_status(session, args.status)
                    print(f"\n✓ Purged {deleted} invoices")
            
            elif args.ids:
                if args.dry_run:
                    print(f"\nWould delete: {len(args.ids)} invoices")
                    for inv_id in args.ids:
                        result = await session.execute(
                            text("SELECT file_name FROM invoices WHERE id = :id"),
                            {"id": inv_id}
                        )
                        row = result.fetchone()
                        if row:
                            print(f"  - {inv_id}: {row[0]}")
                        else:
                            print(f"  - {inv_id}: (not found)")
                else:
                    deleted = await purge_invoices_by_ids(session, args.ids)
                    print(f"\n✓ Purged {deleted} invoices")
            
            elif args.older_than:
                if args.dry_run:
                    from datetime import timedelta
                    cutoff = datetime.utcnow() - timedelta(days=args.older_than)
                    result = await session.execute(
                        text("SELECT COUNT(*) FROM invoices WHERE upload_date < :cutoff"),
                        {"cutoff": cutoff}
                    )
                    count = result.scalar()
                    print(f"\nWould delete: {count} invoices older than {args.older_than} days")
                else:
                    deleted = await purge_old_invoices(session, args.older_than)
                    print(f"\n✓ Purged {deleted} invoices")
            
            else:
                print("\nNo action specified. Use --help for options.")
                print("\nExamples:")
                print("  python scripts/purge_invoices.py --all --confirm")
                print("  python scripts/purge_invoices.py --status processing")
                print("  python scripts/purge_invoices.py --older-than 30")
                print("  python scripts/purge_invoices.py --ids invoice-id-1 invoice-id-2")
                print("  python scripts/purge_invoices.py --all --dry-run")
                return 1
            
            # Show final state
            if not args.dry_run:
                print("\n" + "="*80)
                print("FINAL DATABASE STATE")
                print("="*80)
                
                counts = await count_invoices(session)
                line_item_count = await count_line_items(session)
                
                print(f"Total invoices: {counts['total']}")
                print(f"Total line items: {line_item_count}")
                print("\nInvoices by status:")
                for status, count in counts['by_status'].items():
                    print(f"  - {status}: {count}")
            
            return 0
    
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        await engine.dispose()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
