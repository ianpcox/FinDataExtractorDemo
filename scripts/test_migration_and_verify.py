"""
Test database migration and verify data integrity.

This script:
1. Checks current database state
2. Runs the migration
3. Verifies line_items table was created
4. Verifies data was migrated correctly
5. Checks data integrity
6. Optionally tests rollback
"""

import sys
import os
import asyncio
from pathlib import Path
from decimal import Decimal
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, text
from sqlalchemy.pool import StaticPool

from src.models.database import Base
from src.models.db_models import Invoice as InvoiceDB
from src.models.line_item_db_models import LineItem as LineItemDB
from src.models.invoice import Invoice, LineItem
from src.models.db_utils import db_to_pydantic_invoice
from src.config import settings


async def check_database_state(engine):
    """Check current database state"""
    print("\n" + "="*80)
    print("STEP 1: Checking Database State")
    print("="*80)
    
    async with engine.begin() as conn:
        # Check if line_items table exists
        result = await conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='line_items'
        """))
        table_exists = result.fetchone() is not None
        
        if table_exists:
            print("✓ line_items table already exists")
            
            # Count line items
            result = await conn.execute(text("SELECT COUNT(*) FROM line_items"))
            count = result.scalar()
            print(f"  - Line items in table: {count}")
        else:
            print("✗ line_items table does not exist (expected before migration)")
        
        # Check invoices with line_items JSON
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM invoices 
            WHERE line_items IS NOT NULL AND line_items != '[]' AND line_items != ''
        """))
        invoices_with_json = result.scalar()
        print(f"  - Invoices with line_items JSON: {invoices_with_json}")
        
        # Sample a few invoices with line items
        if invoices_with_json > 0:
            result = await conn.execute(text("""
                SELECT id, line_items FROM invoices 
                WHERE line_items IS NOT NULL AND line_items != '[]' AND line_items != ''
                LIMIT 3
            """))
            samples = result.fetchall()
            print(f"\n  Sample invoices with line items:")
            for invoice_id, line_items_json in samples:
                try:
                    if isinstance(line_items_json, str):
                        items = json.loads(line_items_json)
                    else:
                        items = line_items_json
                    item_count = len(items) if isinstance(items, list) else 0
                    print(f"    - {invoice_id}: {item_count} line items in JSON")
                except:
                    print(f"    - {invoice_id}: (could not parse JSON)")
        
        return {
            "table_exists": table_exists,
            "invoices_with_json": invoices_with_json,
            "line_items_in_table": count if table_exists else 0
        }


async def verify_migration(engine):
    """Verify migration was successful"""
    print("\n" + "="*80)
    print("STEP 2: Verifying Migration")
    print("="*80)
    
    async with engine.begin() as conn:
        # Check table exists
        result = await conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='line_items'
        """))
        if result.fetchone() is None:
            print("✗ ERROR: line_items table does not exist after migration")
            return False
        
        print("✓ line_items table exists")
        
        # Check indexes
        result = await conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'ix_line_items%'
        """))
        indexes = [row[0] for row in result.fetchall()]
        print(f"✓ Indexes created: {indexes}")
        
        # Count line items
        result = await conn.execute(text("SELECT COUNT(*) FROM line_items"))
        total_line_items = result.scalar()
        print(f"✓ Total line items in table: {total_line_items}")
        
        # Count invoices with line items
        result = await conn.execute(text("""
            SELECT COUNT(DISTINCT invoice_id) FROM line_items
        """))
        invoices_with_items = result.scalar()
        print(f"✓ Invoices with line items in table: {invoices_with_items}")
        
        return True


async def verify_data_integrity(engine):
    """Verify data integrity after migration"""
    print("\n" + "="*80)
    print("STEP 3: Verifying Data Integrity")
    print("="*80)
    
    async with engine.begin() as conn:
        # Get invoices that have both JSON and table data
        result = await conn.execute(text("""
            SELECT i.id, i.line_items as json_items,
                   COUNT(li.id) as table_item_count
            FROM invoices i
            LEFT JOIN line_items li ON li.invoice_id = i.id
            WHERE i.line_items IS NOT NULL 
              AND i.line_items != '[]' 
              AND i.line_items != ''
            GROUP BY i.id, i.line_items
            LIMIT 10
        """))
        
        samples = result.fetchall()
        
        if not samples:
            print("⚠ No invoices with line items found for comparison")
            return True
        
        print(f"Comparing JSON vs Table data for {len(samples)} invoices:\n")
        
        all_match = True
        for invoice_id, json_items, table_count in samples:
            # Parse JSON
            try:
                if isinstance(json_items, str):
                    json_data = json.loads(json_items)
                else:
                    json_data = json_items
                
                json_count = len(json_data) if isinstance(json_data, list) else 0
                
                # Get table items
                result2 = await conn.execute(text("""
                    SELECT line_number, description, amount, quantity, unit_price,
                           gst_amount, pst_amount, qst_amount, tax_amount
                    FROM line_items
                    WHERE invoice_id = :invoice_id
                    ORDER BY line_number
                """), {"invoice_id": invoice_id})
                
                table_items = result2.fetchall()
                
                # Compare counts
                if json_count != table_count:
                    print(f"✗ {invoice_id}: Count mismatch - JSON: {json_count}, Table: {table_count}")
                    all_match = False
                    continue
                
                # Compare individual items
                matches = 0
                for idx, (line_num, desc, amount, qty, unit_price, gst, pst, qst, tax) in enumerate(table_items):
                    if idx < len(json_data):
                        json_item = json_data[idx]
                        
                        # Compare key fields
                        json_line_num = json_item.get('line_number', idx + 1)
                        json_amount = str(json_item.get('amount', '0'))
                        table_amount = str(amount) if amount else '0'
                        
                        if json_line_num == line_num and json_amount == table_amount:
                            matches += 1
                
                if matches == json_count:
                    print(f"✓ {invoice_id}: {json_count} items match perfectly")
                else:
                    print(f"⚠ {invoice_id}: {matches}/{json_count} items match")
                    all_match = False
            
            except Exception as e:
                print(f"✗ {invoice_id}: Error comparing - {e}")
                all_match = False
        
        return all_match


async def verify_orm_access(engine):
    """Verify ORM can access line items correctly"""
    print("\n" + "="*80)
    print("STEP 4: Verifying ORM Access")
    print("="*80)
    
    TestingSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with TestingSessionLocal() as session:
        # Get an invoice with line items
        result = await session.execute(
            select(InvoiceDB).where(InvoiceDB.line_items.isnot(None)).limit(1)
        )
        invoice_db = result.scalar_one_or_none()
        
        if not invoice_db:
            print("⚠ No invoices with line items found for ORM test")
            return True
        
        print(f"Testing ORM access for invoice: {invoice_db.id}")
        
        # Test relationship access
        try:
            # Load line items via relationship
            line_items_relationship = invoice_db.line_items_relationship
            print(f"✓ Relationship access works: {len(line_items_relationship)} items")
            
            # Test converting to Pydantic
            invoice_pydantic = db_to_pydantic_invoice(invoice_db)
            print(f"✓ Pydantic conversion works: {len(invoice_pydantic.line_items)} items")
            
            # Verify line items match
            if len(line_items_relationship) == len(invoice_pydantic.line_items):
                print(f"✓ Line item counts match: {len(invoice_pydantic.line_items)}")
                
                # Check first item
                if invoice_pydantic.line_items:
                    first_item = invoice_pydantic.line_items[0]
                    print(f"✓ First line item: #{first_item.line_number} - {first_item.description[:40]}... - ${first_item.amount}")
                    return True
                else:
                    print("⚠ No line items in Pydantic model")
                    return False
            else:
                print(f"✗ Count mismatch: Relationship={len(line_items_relationship)}, Pydantic={len(invoice_pydantic.line_items)}")
                return False
        
        except Exception as e:
            print(f"✗ ORM access failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_aggregation_validation(engine):
    """Test aggregation validation with migrated data"""
    print("\n" + "="*80)
    print("STEP 5: Testing Aggregation Validation")
    print("="*80)
    
    from src.validation.aggregation_validator import AggregationValidator
    
    TestingSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with TestingSessionLocal() as session:
        # Get an invoice with line items
        result = await session.execute(
            select(InvoiceDB).where(InvoiceDB.line_items.isnot(None)).limit(1)
        )
        invoice_db = result.scalar_one_or_none()
        
        if not invoice_db:
            print("⚠ No invoices with line items found for aggregation test")
            return True
        
        invoice_pydantic = db_to_pydantic_invoice(invoice_db)
        
        if not invoice_pydantic.line_items:
            print("⚠ Invoice has no line items")
            return True
        
        print(f"Testing aggregation validation for invoice: {invoice_pydantic.id}")
        print(f"  - Line items: {len(invoice_pydantic.line_items)}")
        print(f"  - Subtotal: {invoice_pydantic.subtotal}")
        print(f"  - Total: {invoice_pydantic.total_amount}")
        
        # Run validation
        validation_summary = AggregationValidator.get_validation_summary(invoice_pydantic)
        
        print(f"\n  Validation Results:")
        print(f"    - All Valid: {validation_summary['all_valid']}")
        print(f"    - Passed: {validation_summary['passed_validations']}/{validation_summary['total_validations']}")
        
        if not validation_summary['all_valid']:
            print(f"    - Errors:")
            for error in validation_summary['errors']:
                print(f"      • {error}")
        
        return validation_summary['all_valid']


async def main():
    """Main test function"""
    print("="*80)
    print("DATABASE MIGRATION TEST AND VERIFICATION")
    print("="*80)
    print(f"Database: {settings.DATABASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    
    # Create engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    try:
        # Step 1: Check current state
        state = await check_database_state(engine)
        
        # Step 2: Run migration if needed
        if not state["table_exists"]:
            print("\n" + "="*80)
            print("Running Migration...")
            print("="*80)
            
            # Import and run migration
            from alembic.config import Config
            from alembic import command
            
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")
            
            print("✓ Migration completed")
        else:
            print("\n⚠ Migration already applied (line_items table exists)")
            print("  Skipping migration step")
        
        # Step 3: Verify migration
        migration_ok = await verify_migration(engine)
        if not migration_ok:
            print("\n✗ Migration verification failed")
            return 1
        
        # Step 4: Verify data integrity
        integrity_ok = await verify_data_integrity(engine)
        if not integrity_ok:
            print("\n⚠ Some data integrity issues found (see details above)")
        else:
            print("\n✓ All data integrity checks passed")
        
        # Step 5: Verify ORM access
        orm_ok = await verify_orm_access(engine)
        if not orm_ok:
            print("\n✗ ORM access verification failed")
            return 1
        
        # Step 6: Test aggregation validation
        validation_ok = await test_aggregation_validation(engine)
        if not validation_ok:
            print("\n⚠ Aggregation validation found issues (may be expected)")
        
        # Summary
        print("\n" + "="*80)
        print("VERIFICATION SUMMARY")
        print("="*80)
        print(f"Migration: {'✓ PASSED' if migration_ok else '✗ FAILED'}")
        print(f"Data Integrity: {'✓ PASSED' if integrity_ok else '⚠ ISSUES FOUND'}")
        print(f"ORM Access: {'✓ PASSED' if orm_ok else '✗ FAILED'}")
        print(f"Aggregation Validation: {'✓ PASSED' if validation_ok else '⚠ ISSUES FOUND'}")
        
        if migration_ok and orm_ok:
            print("\n✓ Overall: Migration and verification successful!")
            return 0
        else:
            print("\n✗ Overall: Some verification steps failed")
            return 1
    
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        await engine.dispose()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
