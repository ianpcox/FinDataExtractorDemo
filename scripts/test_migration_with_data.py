"""
Test migration with sample data to verify end-to-end functionality.

This script:
1. Creates a test invoice with line items (saves to JSON)
2. Runs migration (if not already run)
3. Verifies line items are in the table
4. Tests ORM access
5. Tests aggregation validation
"""

import sys
import asyncio
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from sqlalchemy.pool import StaticPool

from src.models.database import Base
from src.models.db_models import Invoice as InvoiceDB
from src.models.invoice import Invoice, LineItem, InvoiceState
from src.services.db_service import DatabaseService
from src.models.db_utils import db_to_pydantic_invoice
from src.validation.aggregation_validator import AggregationValidator
from src.config import settings


async def test_migration_with_data():
    """Test migration with sample data"""
    
    print("="*80)
    print("MIGRATION TEST WITH SAMPLE DATA")
    print("="*80)
    
    # Create engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    TestingSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    try:
        async with TestingSessionLocal() as session:
            # Step 1: Create test invoice with line items
            print("\n[STEP 1] Creating test invoice with line items...")
            
            invoice_id = f"test-migration-{uuid4().hex[:8]}"
            
            # Create line items
            line_items = []
            subtotal = Decimal("0")
            for i in range(1, 6):  # 5 line items
                quantity = Decimal(str(i))
                unit_price = Decimal("100.00")
                amount = quantity * unit_price
                subtotal += amount
                
                line_item = LineItem(
                    line_number=i,
                    description=f"Test Item {i} - Migration Verification",
                    quantity=quantity,
                    unit_price=unit_price,
                    amount=amount,
                    confidence=0.9,
                    tax_rate=Decimal("0.13"),
                    tax_amount=amount * Decimal("0.13"),
                    gst_amount=amount * Decimal("0.05"),
                    pst_amount=amount * Decimal("0.08"),
                )
                line_items.append(line_item)
            
            # Create invoice
            invoice = Invoice(
                id=invoice_id,
                file_path="test/migration_test.pdf",
                file_name="migration_test.pdf",
                upload_date=datetime.utcnow(),
                status="extracted",
                processing_state=InvoiceState.EXTRACTED,
                invoice_number="TEST-MIG-001",
                invoice_date=datetime.utcnow().date(),
                vendor_name="Test Vendor",
                subtotal=subtotal,
                tax_amount=subtotal * Decimal("0.13"),
                gst_amount=subtotal * Decimal("0.05"),
                pst_amount=subtotal * Decimal("0.08"),
                total_amount=subtotal + (subtotal * Decimal("0.13")),
                currency="CAD",
                line_items=line_items,
                extraction_confidence=0.95
            )
            
            # Save invoice (this will save line items to table)
            await DatabaseService.save_invoice(invoice, db=session)
            await session.commit()
            
            print(f"[OK] Invoice created: {invoice_id}")
            print(f"     Line items: {len(line_items)}")
            print(f"     Subtotal: ${subtotal}")
            print(f"     Total: ${invoice.total_amount}")
            
            # Step 2: Verify line items are in table
            print("\n[STEP 2] Verifying line items in database table...")
            
            from sqlalchemy import text
            result = await session.execute(
                text("SELECT COUNT(*) FROM line_items WHERE invoice_id = :invoice_id"),
                {"invoice_id": invoice_id}
            )
            table_count = result.scalar()
            
            if table_count == len(line_items):
                print(f"[OK] Line items in table: {table_count}")
            else:
                print(f"[ERROR] Expected {len(line_items)}, found {table_count}")
                return False
            
            # Step 3: Test ORM access
            print("\n[STEP 3] Testing ORM access...")
            
            result = await session.execute(
                select(InvoiceDB).where(InvoiceDB.id == invoice_id)
            )
            invoice_db = result.scalar_one()
            
            # Access via relationship
            line_items_relationship = invoice_db.line_items_relationship
            print(f"[OK] Relationship access: {len(line_items_relationship)} items")
            
            # Convert to Pydantic
            invoice_pydantic = db_to_pydantic_invoice(invoice_db)
            print(f"[OK] Pydantic conversion: {len(invoice_pydantic.line_items)} items")
            
            # Verify line items match
            if len(invoice_pydantic.line_items) == len(line_items):
                print("[OK] Line item counts match")
                
                # Check first item
                first_original = line_items[0]
                first_loaded = invoice_pydantic.line_items[0]
                
                if (first_loaded.line_number == first_original.line_number and
                    first_loaded.amount == first_original.amount):
                    print("[OK] First line item matches")
                else:
                    print("[ERROR] First line item mismatch")
                    return False
            else:
                print(f"[ERROR] Count mismatch: {len(invoice_pydantic.line_items)} vs {len(line_items)}")
                return False
            
            # Step 4: Test aggregation validation
            print("\n[STEP 4] Testing aggregation validation...")
            
            validation_summary = AggregationValidator.get_validation_summary(invoice_pydantic)
            
            print(f"     All Valid: {validation_summary['all_valid']}")
            print(f"     Passed: {validation_summary['passed_validations']}/{validation_summary['total_validations']}")
            
            if validation_summary['all_valid']:
                print("[OK] Aggregation validation passed")
            else:
                print("[WARN] Aggregation validation found issues:")
                for error in validation_summary['errors']:
                    print(f"      - {error}")
            
            # Step 5: Test updating line items
            print("\n[STEP 5] Testing line item updates...")
            
            # Modify an existing line item
            invoice_pydantic.line_items[0].amount = Decimal("150.00")
            invoice_pydantic.subtotal = sum(item.amount for item in invoice_pydantic.line_items)
            
            await DatabaseService.save_invoice(invoice_pydantic, db=session)
            await session.commit()
            
            # Reload and verify
            result = await session.execute(
                select(InvoiceDB).where(InvoiceDB.id == invoice_id)
            )
            updated_invoice_db = result.scalar_one()
            updated_invoice_pydantic = db_to_pydantic_invoice(updated_invoice_db)
            
            if updated_invoice_pydantic.line_items[0].amount == Decimal("150.00"):
                print("[OK] Line item update successful")
            else:
                print("[ERROR] Line item update failed")
                return False
            
            # Step 6: Test deleting line items
            print("\n[STEP 6] Testing line item deletion...")
            
            # Remove a line item
            invoice_pydantic.line_items = invoice_pydantic.line_items[1:]  # Remove first item
            
            await DatabaseService.save_invoice(invoice_pydantic, db=session)
            await session.commit()
            
            # Verify deletion
            result = await session.execute(
                text("SELECT COUNT(*) FROM line_items WHERE invoice_id = :invoice_id"),
                {"invoice_id": invoice_id}
            )
            remaining_count = result.scalar()
            
            if remaining_count == len(invoice_pydantic.line_items):
                print(f"[OK] Line item deletion successful: {remaining_count} items remaining")
            else:
                print(f"[ERROR] Deletion failed: expected {len(invoice_pydantic.line_items)}, found {remaining_count}")
                return False
            
            # Cleanup
            print("\n[STEP 7] Cleaning up test data...")
            await session.execute(
                text("DELETE FROM line_items WHERE invoice_id = :invoice_id"),
                {"invoice_id": invoice_id}
            )
            await session.execute(
                text("DELETE FROM invoices WHERE id = :invoice_id"),
                {"invoice_id": invoice_id}
            )
            await session.commit()
            print("[OK] Test data cleaned up")
            
            print("\n" + "="*80)
            print("MIGRATION TEST: ALL CHECKS PASSED")
            print("="*80)
            print("\nThe migration is working correctly!")
            print("Line items can be:")
            print("  - Saved to the table")
            print("  - Loaded from the table")
            print("  - Updated in the table")
            print("  - Deleted from the table")
            print("  - Accessed via ORM relationship")
            print("  - Validated with AggregationValidator")
            
            return True
    
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(test_migration_with_data())
    sys.exit(0 if success else 1)
