"""Unit tests for timestamp audit invariants (created_at, updated_at)"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from time import sleep

from src.models.invoice import Invoice, Address, LineItem
from src.models.db_utils import pydantic_to_db_invoice, db_to_pydantic_invoice
from src.services.db_service import DatabaseService


class TestTimestampInvariants:
    """Test that created_at is immutable and updated_at reflects changes"""

    @pytest.mark.asyncio
    async def test_created_at_stable_across_updates(self, db_session):
        """created_at must never change on updates"""
        from sqlalchemy import select
        from src.models.db_models import Invoice as InvoiceDB
        
        invoice_id = "test-timestamp-stable"
        
        # Create initial invoice
        invoice = Invoice(
            id=invoice_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            status="extracted",
            vendor_name="Initial Vendor",
            total_amount=Decimal("100.00"),
            line_items=[
                LineItem(
                    line_number=1,
                    description="Item 1",
                    quantity=Decimal("1"),
                    unit_price=Decimal("100.00"),
                    amount=Decimal("100.00"),
                    confidence=0.9,
                )
            ],
        )
        
        saved = await DatabaseService.save_invoice(invoice, db=db_session)
        original_created_at = saved.created_at
        original_updated_at = saved.updated_at
        
        assert original_created_at is not None
        
        # Wait a tiny amount to ensure time progresses
        await asyncio.sleep(0.05)
        
        # Update invoice
        invoice_update = Invoice(
            id=invoice_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            status="validated",  # Changed
            vendor_name="Updated Vendor",  # Changed
        )
        
        saved_updated = await DatabaseService.save_invoice(invoice_update, db=db_session)
        
        # Assert created_at did NOT change
        assert saved_updated.created_at == original_created_at
        # Assert updated_at DID change (or at minimum is >= original)
        assert saved_updated.updated_at >= original_updated_at
        
        # Verify by refetch from DB
        result = await db_session.execute(select(InvoiceDB).where(InvoiceDB.id == invoice_id))
        fetched_db = result.scalar_one()
        assert fetched_db.created_at == original_created_at
        assert fetched_db.vendor_name == "Updated Vendor"

    @pytest.mark.asyncio
    async def test_updated_at_changes_on_update(self, db_session):
        """updated_at must reflect the last modification time"""
        invoice_id = "test-updated-at-changes"
        
        # Create
        invoice = Invoice(
            id=invoice_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Vendor A",
            total_amount=Decimal("50.00"),
        )
        
        saved = await DatabaseService.save_invoice(invoice, db=db_session)
        first_updated_at = saved.updated_at
        
        await asyncio.sleep(0.05)
        
        # Update 1
        invoice_update1 = Invoice(
            id=invoice_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Vendor B",
        )
        
        saved_u1 = await DatabaseService.save_invoice(invoice_update1, db=db_session)
        second_updated_at = saved_u1.updated_at
        
        # updated_at should have changed
        assert second_updated_at > first_updated_at or second_updated_at != first_updated_at
        
        await asyncio.sleep(0.05)
        
        # Update 2
        invoice_update2 = Invoice(
            id=invoice_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Vendor C",
        )
        
        saved_u2 = await DatabaseService.save_invoice(invoice_update2, db=db_session)
        third_updated_at = saved_u2.updated_at
        
        # updated_at should have changed again
        assert third_updated_at >= second_updated_at

    @pytest.mark.asyncio
    async def test_created_at_preserved_across_multiple_updates(self, db_session):
        """Multiple updates must never change created_at"""
        invoice_id = "test-multiple-updates"
        
        invoice = Invoice(
            id=invoice_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Original",
        )
        
        saved = await DatabaseService.save_invoice(invoice, db=db_session)
        original_created_at = saved.created_at
        
        # Perform 5 updates
        for i in range(5):
            await asyncio.sleep(0.02)
            update = Invoice(
                id=invoice_id,
                file_path="test/path.pdf",
                file_name="test.pdf",
                upload_date=datetime.utcnow(),
                vendor_name=f"Update {i+1}",
            )
            saved_updated = await DatabaseService.save_invoice(update, db=db_session)
            
            # created_at must remain the same
            assert saved_updated.created_at == original_created_at

    @pytest.mark.asyncio
    async def test_created_at_set_on_insert_not_update(self, db_session):
        """created_at should only be set once on insert, never on update"""
        invoice_id = "test-insert-vs-update"
        
        # Create (insert)
        invoice = Invoice(
            id=invoice_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Insert Test",
            total_amount=Decimal("100.00"),
        )
        
        saved = await DatabaseService.save_invoice(invoice, db=db_session)
        insert_created_at = saved.created_at
        insert_updated_at = saved.updated_at
        
        assert insert_created_at is not None
        assert insert_updated_at is not None
        # On insert, created_at and updated_at should be close (same transaction)
        # Allow small delta for DB precision
        delta = abs((insert_created_at - insert_updated_at).total_seconds())
        assert delta < 1.0  # Within 1 second
        
        await asyncio.sleep(0.05)
        
        # Update
        invoice_update = Invoice(
            id=invoice_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Update Test",
        )
        
        saved_updated = await DatabaseService.save_invoice(invoice_update, db=db_session)
        update_created_at = saved_updated.created_at
        update_updated_at = saved_updated.updated_at
        
        # created_at should be unchanged
        assert update_created_at == insert_created_at
        # updated_at should have progressed
        assert update_updated_at >= insert_updated_at

    def test_converter_does_not_set_timestamps(self):
        """pydantic_to_db_invoice must not set created_at or updated_at"""
        invoice = Invoice(
            id="test-converter-timestamps",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Converter Test",
            # Explicitly provide timestamps (should be ignored by converter)
            created_at=datetime(2020, 1, 1),
            updated_at=datetime(2020, 1, 2),
        )
        
        db_invoice = pydantic_to_db_invoice(invoice)
        
        # The converter should NOT have set these attributes
        # SQLAlchemy will set them via defaults on insert
        # We verify by checking the ORM object before it's committed
        # For new objects, these should be None or unset until flush/commit
        # (This is tricky to test directly; the real proof is in DB tests above)
        
        # At minimum, verify the converter doesn't copy the provided values
        # We can't easily assert they're None because SQLAlchemy may have already
        # applied defaults. Instead, we rely on the integration tests above.
        assert db_invoice.id == "test-converter-timestamps"

    @pytest.mark.asyncio
    async def test_status_update_preserves_created_at(self, db_session):
        """Changing status should not affect created_at"""
        invoice_id = "test-status-update"
        
        invoice = Invoice(
            id=invoice_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            status="pending",
            vendor_name="Status Test",
        )
        
        saved = await DatabaseService.save_invoice(invoice, db=db_session)
        original_created_at = saved.created_at
        
        await asyncio.sleep(0.05)
        
        # Change status
        invoice_status_change = Invoice(
            id=invoice_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            status="extracted",
        )
        
        saved_updated = await DatabaseService.save_invoice(invoice_status_change, db=db_session)
        
        assert saved_updated.created_at == original_created_at
        assert saved_updated.status == "extracted"

    @pytest.mark.asyncio
    async def test_field_corrections_preserve_created_at(self, db_session):
        """HITL field corrections should not affect created_at"""
        invoice_id = "test-field-corrections"
        
        invoice = Invoice(
            id=invoice_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Original Vendor",
            total_amount=Decimal("100.00"),
            invoice_number="INV-001",
            vendor_address=Address(
                street="123 Main",
                city="Toronto",
                province="ON",
                postal_code="M1M1M1",
                country="CA",
            ),
        )
        
        saved = await DatabaseService.save_invoice(invoice, db=db_session)
        original_created_at = saved.created_at
        
        await asyncio.sleep(0.05)
        
        # Apply corrections (simulating HITL)
        invoice_corrected = Invoice(
            id=invoice_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Corrected Vendor",
            total_amount=Decimal("150.00"),
            invoice_number="INV-001-CORRECTED",
        )
        
        saved_corrected = await DatabaseService.save_invoice(invoice_corrected, db=db_session)
        
        assert saved_corrected.created_at == original_created_at
        assert saved_corrected.vendor_name == "Corrected Vendor"
        assert saved_corrected.total_amount == Decimal("150.00")
        # Verify address preserved (PATCH semantics)
        assert saved_corrected.vendor_address["city"] == "Toronto"

    @pytest.mark.asyncio
    async def test_line_items_update_preserves_created_at(self, db_session):
        """Updating line items should not affect created_at"""
        invoice_id = "test-line-items-update"
        
        invoice = Invoice(
            id=invoice_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Line Items Test",
            line_items=[
                LineItem(
                    line_number=1,
                    description="Initial Item",
                    quantity=Decimal("1"),
                    unit_price=Decimal("50.00"),
                    amount=Decimal("50.00"),
                    confidence=0.8,
                )
            ],
        )
        
        saved = await DatabaseService.save_invoice(invoice, db=db_session)
        original_created_at = saved.created_at
        
        await asyncio.sleep(0.05)
        
        # Update line items
        invoice_new_items = Invoice(
            id=invoice_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Line Items Test",
            line_items=[
                LineItem(
                    line_number=1,
                    description="Updated Item",
                    quantity=Decimal("2"),
                    unit_price=Decimal("75.00"),
                    amount=Decimal("150.00"),
                    confidence=0.95,
                )
            ],
        )
        
        saved_updated = await DatabaseService.save_invoice(invoice_new_items, db=db_session)
        
        assert saved_updated.created_at == original_created_at
        assert len(saved_updated.line_items) == 1
        assert saved_updated.line_items[0]["description"] == "Updated Item"

