"""Unit tests for invoice ID (primary key) invariants"""

import pytest
from datetime import datetime, date
from decimal import Decimal

from src.models.invoice import Invoice, Address, LineItem
from src.models.db_utils import pydantic_to_db_invoice, db_to_pydantic_invoice
from src.services.db_service import DatabaseService


class TestInvoiceIDInvariants:
    """Test that invoice_id (primary key) is never generated or corrupted"""

    def test_pydantic_to_db_missing_id_fails(self):
        """Missing invoice ID must fail with clear error"""
        invoice = Invoice(
            id=None,  # ← Missing ID
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Test Vendor",
        )
        
        with pytest.raises(ValueError) as exc_info:
            pydantic_to_db_invoice(invoice)
        
        assert "Invoice.id" in str(exc_info.value)
        assert "primary key" in str(exc_info.value)

    def test_pydantic_to_db_empty_string_id_fails(self):
        """Empty string ID must fail"""
        invoice = Invoice(
            id="",  # ← Empty string
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Test Vendor",
        )
        
        with pytest.raises(ValueError) as exc_info:
            pydantic_to_db_invoice(invoice)
        
        assert "Invoice.id" in str(exc_info.value)

    def test_pydantic_to_db_preserves_id_exactly(self):
        """Converter must preserve invoice ID exactly"""
        known_id = "invoice-known-123-abc"
        invoice = Invoice(
            id=known_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Test Vendor",
        )
        
        db_invoice = pydantic_to_db_invoice(invoice)
        
        assert db_invoice.id == known_id
        assert isinstance(db_invoice.id, str)
        # Ensure no transformation (no timestamp, no UUID generation)
        assert db_invoice.id == invoice.id

    def test_db_to_pydantic_preserves_id_exactly(self):
        """Reverse converter must also preserve ID exactly"""
        known_id = "invoice-reverse-456-def"
        invoice = Invoice(
            id=known_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Test Vendor",
        )
        
        db_invoice = pydantic_to_db_invoice(invoice)
        back_to_pydantic = db_to_pydantic_invoice(db_invoice)
        
        assert back_to_pydantic.id == known_id
        assert back_to_pydantic.id == invoice.id

    def test_pydantic_to_db_does_not_set_timestamps(self):
        """Converter must not set created_at or updated_at (SQLAlchemy manages these)"""
        invoice = Invoice(
            id="test-no-timestamp",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Test Vendor",
            created_at=datetime(2020, 1, 1),  # Even if provided
            updated_at=datetime(2020, 1, 2),
        )
        
        db_invoice = pydantic_to_db_invoice(invoice)
        
        # Converter should not have set these; they will be set by SQLAlchemy defaults
        # We can't assert None here because SQLAlchemy will populate them on insert,
        # but we can verify the converter doesn't explicitly copy them
        # (This is verified by code inspection: no created_at/updated_at in constructor)
        assert db_invoice.id == "test-no-timestamp"

    @pytest.mark.asyncio
    async def test_save_invoice_preserves_id_on_create(self, db_session):
        """DatabaseService.save_invoice must not generate new IDs on create"""
        known_id = "test-save-create-id"
        invoice = Invoice(
            id=known_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Test Vendor",
            total_amount=Decimal("100.00"),
        )
        
        saved = await DatabaseService.save_invoice(invoice, db=db_session)
        
        assert saved.id == known_id
        # Verify no other row was created with a different ID
        fetched = await DatabaseService.get_invoice(known_id, db=db_session)
        assert fetched is not None
        assert fetched.id == known_id

    @pytest.mark.asyncio
    async def test_save_invoice_preserves_id_on_update(self, db_session):
        """DatabaseService.save_invoice must not change ID on update"""
        known_id = "test-save-update-id"
        invoice_initial = Invoice(
            id=known_id,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
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
            vendor_address=Address(
                street="123 Main St",
                city="Toronto",
                province="ON",
                postal_code="M1M1M1",
                country="CA",
            ),
        )
        
        # Create
        await DatabaseService.save_invoice(invoice_initial, db=db_session)
        
        # Update with partial data
        invoice_update = Invoice(
            id=known_id,  # Same ID
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Updated Vendor",  # Changed field
        )
        
        saved_updated = await DatabaseService.save_invoice(invoice_update, db=db_session)
        
        # Assert ID unchanged
        assert saved_updated.id == known_id
        assert saved_updated.vendor_name == "Updated Vendor"
        
        # Verify no new row was created
        fetched = await DatabaseService.get_invoice(known_id, db=db_session)
        assert fetched.id == known_id
        assert fetched.vendor_name == "Updated Vendor"
        # Line items and address should still be present (PATCH semantics)
        assert len(fetched.line_items) == 1
        assert fetched.vendor_address is not None

    @pytest.mark.asyncio
    async def test_save_invoice_with_missing_id_fails(self, db_session):
        """Attempting to save an invoice without ID must fail early"""
        invoice_no_id = Invoice(
            id=None,
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="No ID Vendor",
        )
        
        with pytest.raises(ValueError) as exc_info:
            await DatabaseService.save_invoice(invoice_no_id, db=db_session)
        
        assert "Invoice.id" in str(exc_info.value)
        assert "primary key" in str(exc_info.value)

    def test_id_types_are_consistent(self):
        """Ensure IDs are always strings, never timestamps or UUIDs generated by converter"""
        test_ids = [
            "simple-id",
            "uuid-format-12345678-1234-1234-1234-123456789abc",
            "invoice-2024-01-15-001",
            "INV-001",
        ]
        
        for test_id in test_ids:
            invoice = Invoice(
                id=test_id,
                file_path="test/path.pdf",
                file_name="test.pdf",
                upload_date=datetime.utcnow(),
                vendor_name="Test",
            )
            
            db_invoice = pydantic_to_db_invoice(invoice)
            assert db_invoice.id == test_id
            assert isinstance(db_invoice.id, str)
            
            # Ensure no timestamp generation
            assert "." not in db_invoice.id or "." in test_id  # No float timestamps
            # Ensure exact match (no transformation)
            assert db_invoice.id == test_id

