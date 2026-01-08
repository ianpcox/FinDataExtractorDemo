"""
Test script to verify line item persistence from UI through API to database table.

This script:
1. Creates a test invoice with line items
2. Simulates UI validation/update
3. Verifies data is saved to line_items table (not JSON)
4. Verifies data can be loaded back correctly
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
from sqlalchemy import select, text
from sqlalchemy.pool import StaticPool

from src.models.database import Base
from src.models.db_models import Invoice as InvoiceDB
from src.models.line_item_db_models import LineItem as LineItemDB
from src.models.invoice import Invoice, LineItem, InvoiceState
from src.services.db_service import DatabaseService
from src.models.db_utils import db_to_pydantic_invoice
from src.config import settings


async def test_line_item_persistence():
    """Test line item persistence end-to-end"""
    
    print("="*80)
    print("LINE ITEM PERSISTENCE TEST")
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
            # Step 1: Create test invoice with line items (simulating extraction)
            print("\n[STEP 1] Creating test invoice with line items...")
            
            invoice_id = f"test-persistence-{uuid4().hex[:8]}"
            
            line_items = [
                LineItem(
                    line_number=1,
                    description="Test Item 1 - Original",
                    quantity=Decimal("2"),
                    unit_price=Decimal("50.00"),
                    amount=Decimal("100.00"),
                    confidence=0.85,
                    tax_rate=Decimal("0.13"),
                    tax_amount=Decimal("13.00"),
                    gst_amount=Decimal("5.00"),
                    pst_amount=Decimal("8.00"),
                ),
                LineItem(
                    line_number=2,
                    description="Test Item 2 - Original",
                    quantity=Decimal("3"),
                    unit_price=Decimal("30.00"),
                    amount=Decimal("90.00"),
                    confidence=0.90,
                    tax_rate=Decimal("0.13"),
                    tax_amount=Decimal("11.70"),
                ),
            ]
            
            invoice = Invoice(
                id=invoice_id,
                file_path="test/persistence_test.pdf",
                file_name="persistence_test.pdf",
                upload_date=datetime.utcnow(),
                status="extracted",
                processing_state=InvoiceState.EXTRACTED,
                invoice_number="TEST-PERSIST-001",
                invoice_date=datetime.utcnow().date(),
                vendor_name="Test Vendor",
                subtotal=Decimal("190.00"),
                tax_amount=Decimal("24.70"),
                total_amount=Decimal("214.70"),
                currency="CAD",
                line_items=line_items,
                extraction_confidence=0.88
            )
            
            # Save invoice (this should save line items to table)
            await DatabaseService.save_invoice(invoice, db=session)
            await session.commit()
            
            print(f"[OK] Invoice created: {invoice_id}")
            print(f"     Line items: {len(line_items)}")
            
            # Step 2: Verify line items are in table (not just JSON)
            print("\n[STEP 2] Verifying line items are in line_items table...")
            
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
            
            # Check JSON column (should be empty or minimal)
            result = await session.execute(
                text("SELECT line_items FROM invoices WHERE id = :invoice_id"),
                {"invoice_id": invoice_id}
            )
            json_data = result.scalar_one_or_none()
            if json_data:
                import json
                try:
                    parsed = json.loads(json_data) if isinstance(json_data, str) else json_data
                    json_count = len(parsed) if isinstance(parsed, list) else 0
                    print(f"[INFO] JSON column has {json_count} items (may be for backward compatibility)")
                except:
                    print(f"[INFO] JSON column exists but couldn't parse")
            
            # Step 3: Load invoice and verify line items come from table
            print("\n[STEP 3] Loading invoice and verifying line items...")
            
            loaded_invoice = await DatabaseService.get_invoice(invoice_id, db=session)
            
            if not loaded_invoice:
                print(f"[ERROR] Invoice not found: {invoice_id}")
                return False
            
            if len(loaded_invoice.line_items) == len(line_items):
                print(f"[OK] Loaded {len(loaded_invoice.line_items)} line items")
            else:
                print(f"[ERROR] Expected {len(line_items)}, loaded {len(loaded_invoice.line_items)}")
                return False
            
            # Verify first line item matches
            if loaded_invoice.line_items[0].description == line_items[0].description:
                print("[OK] First line item matches")
            else:
                print(f"[ERROR] Description mismatch: {loaded_invoice.line_items[0].description} vs {line_items[0].description}")
                return False
            
            # Step 4: Simulate UI update (modify line item)
            print("\n[STEP 4] Simulating UI update (modifying line item)...")
            
            # Modify first line item (as UI would)
            loaded_invoice.line_items[0].description = "Test Item 1 - UPDATED"
            loaded_invoice.line_items[0].amount = Decimal("150.00")
            loaded_invoice.subtotal = sum(item.amount for item in loaded_invoice.line_items)
            
            # Save updated invoice (simulating API save)
            await DatabaseService.save_invoice(loaded_invoice, db=session)
            await session.commit()
            
            print("[OK] Invoice updated")
            
            # Step 5: Verify update persisted to table
            print("\n[STEP 5] Verifying update persisted to table...")
            
            result = await session.execute(
                text("""
                    SELECT description, amount 
                    FROM line_items 
                    WHERE invoice_id = :invoice_id AND line_number = 1
                """),
                {"invoice_id": invoice_id}
            )
            row = result.fetchone()
            
            if row:
                table_description, table_amount = row
                if table_description == "Test Item 1 - UPDATED" and str(table_amount) == "150.00":
                    print("[OK] Update persisted to table correctly")
                else:
                    print(f"[ERROR] Table data mismatch: desc='{table_description}', amount={table_amount}")
                    return False
            else:
                print("[ERROR] Line item not found in table")
                return False
            
            # Step 6: Verify can reload updated data
            print("\n[STEP 6] Verifying updated data can be reloaded...")
            
            reloaded_invoice = await DatabaseService.get_invoice(invoice_id, db=session)
            
            if reloaded_invoice.line_items[0].description == "Test Item 1 - UPDATED":
                print("[OK] Updated data loads correctly")
            else:
                print(f"[ERROR] Reloaded description: {reloaded_invoice.line_items[0].description}")
                return False
            
            # Step 7: Test deletion (simulating UI delete)
            print("\n[STEP 7] Testing line item deletion...")
            
            # Remove first line item
            reloaded_invoice.line_items = reloaded_invoice.line_items[1:]
            
            await DatabaseService.save_invoice(reloaded_invoice, db=session)
            await session.commit()
            
            # Verify deletion
            result = await session.execute(
                text("SELECT COUNT(*) FROM line_items WHERE invoice_id = :invoice_id"),
                {"invoice_id": invoice_id}
            )
            remaining_count = result.scalar()
            
            if remaining_count == 1:
                print(f"[OK] Deletion successful: {remaining_count} item remaining")
            else:
                print(f"[ERROR] Expected 1 item, found {remaining_count}")
                return False
            
            # Cleanup
            print("\n[STEP 8] Cleaning up test data...")
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
            print("ALL TESTS PASSED")
            print("="*80)
            print("\nLine item persistence is working correctly:")
            print("  ✓ Line items saved to line_items table")
            print("  ✓ Line items loaded from table")
            print("  ✓ Updates persist to table")
            print("  ✓ Deletions persist to table")
            print("  ✓ Data can be reloaded correctly")
            
            return True
    
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(test_line_item_persistence())
    sys.exit(0 if success else 1)
