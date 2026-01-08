"""Unit tests for invoice_subtype contract stability (Enum ↔ string)"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.models.invoice import Invoice, InvoiceSubtype
from src.models.db_models import Invoice as InvoiceDB
from src.models.db_utils import pydantic_to_db_invoice, db_to_pydantic_invoice
from src.services.db_service import DatabaseService


class TestInvoiceSubtypeContract:
    """Test that invoice_subtype maintains type safety across DB ↔ Pydantic ↔ API"""

    def test_enum_to_db_conversion(self):
        """Pydantic Enum → DB must store as string"""
        for subtype_enum in InvoiceSubtype:
            invoice = Invoice(
                id=f"test-enum-{subtype_enum.value}",
                file_path="test/path.pdf",
                file_name="test.pdf",
                upload_date=datetime.utcnow(),
                invoice_subtype=subtype_enum,  # Enum
            )
            
            db_invoice = pydantic_to_db_invoice(invoice)
            
            # DB must store as string
            assert isinstance(db_invoice.invoice_subtype, str)
            assert db_invoice.invoice_subtype == subtype_enum.value

    def test_db_to_enum_conversion(self):
        """DB string → Pydantic must yield Enum"""
        for subtype_enum in InvoiceSubtype:
            invoice = Invoice(
                id=f"test-db-{subtype_enum.value}",
                file_path="test/path.pdf",
                file_name="test.pdf",
                upload_date=datetime.utcnow(),
                invoice_subtype=subtype_enum,
            )
            
            db_invoice = pydantic_to_db_invoice(invoice)
            pydantic_invoice = db_to_pydantic_invoice(db_invoice)
            
            # Pydantic must have Enum, not string
            assert isinstance(pydantic_invoice.invoice_subtype, InvoiceSubtype)
            assert pydantic_invoice.invoice_subtype == subtype_enum

    def test_enum_roundtrip_preservation(self):
        """Enum → DB → Enum must preserve value"""
        original_invoice = Invoice(
            id="test-roundtrip",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            invoice_subtype=InvoiceSubtype.SHIFT_SERVICE_INVOICE,
        )
        
        # Pydantic → DB
        db_invoice = pydantic_to_db_invoice(original_invoice)
        assert db_invoice.invoice_subtype == "SHIFT_SERVICE_INVOICE"
        
        # DB → Pydantic
        restored_invoice = db_to_pydantic_invoice(db_invoice)
        assert restored_invoice.invoice_subtype == InvoiceSubtype.SHIFT_SERVICE_INVOICE
        assert isinstance(restored_invoice.invoice_subtype, InvoiceSubtype)

    def test_none_subtype_handling(self):
        """None subtype must remain None through conversions"""
        invoice = Invoice(
            id="test-none-subtype",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            invoice_subtype=None,
        )
        
        db_invoice = pydantic_to_db_invoice(invoice)
        assert db_invoice.invoice_subtype is None
        
        restored_invoice = db_to_pydantic_invoice(db_invoice)
        assert restored_invoice.invoice_subtype is None

    def test_unknown_db_string_maps_to_none(self):
        """Unknown DB subtype string must map to None (safe degradation)"""
        # Simulate a DB record with an unknown subtype
        db_invoice = InvoiceDB(
            id="test-unknown-subtype",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            status="extracted",
            invoice_subtype="BOGUS_SUBTYPE_NOT_IN_ENUM",  # Unknown value
        )
        
        # DB → Pydantic should not crash
        pydantic_invoice = db_to_pydantic_invoice(db_invoice)
        
        # Unknown subtype should map to None
        assert pydantic_invoice.invoice_subtype is None

    def test_valid_string_legacy_input_accepted(self):
        """Valid subtype string (legacy input) must be accepted"""
        # Simulate legacy code passing a string instead of Enum
        # (This is allowed for backward compatibility)
        invoice = Invoice(
            id="test-string-input",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            invoice_subtype="PER_DIEM_TRAVEL_INVOICE",  # String, not Enum
        )
        
        # This should not crash; converter validates the string
        db_invoice = pydantic_to_db_invoice(invoice)
        assert db_invoice.invoice_subtype == "PER_DIEM_TRAVEL_INVOICE"

    def test_invalid_string_raises_error(self):
        """Invalid subtype string must raise error at Pydantic validation"""
        from pydantic import ValidationError
        
        # Pydantic validates the Enum before it reaches the converter
        with pytest.raises(ValidationError) as exc_info:
            invoice = Invoice(
                id="test-invalid-string",
                file_path="test/path.pdf",
                file_name="test.pdf",
                upload_date=datetime.utcnow(),
                invoice_subtype="INVALID_SUBTYPE",  # Invalid string
            )
        
        error_str = str(exc_info.value)
        assert "invoice_subtype" in error_str
        assert "INVALID_SUBTYPE" in error_str or "enum" in error_str.lower()

    @pytest.mark.asyncio
    async def test_database_roundtrip_via_save(self, db_session):
        """Full save → load cycle must preserve Enum type"""
        invoice = Invoice(
            id="test-db-roundtrip",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Test Vendor",
            invoice_subtype=InvoiceSubtype.STANDARD_INVOICE,
        )
        
        # Save to DB
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Load from DB
        loaded = await DatabaseService.get_invoice("test-db-roundtrip", db=db_session)
        
        # Must be Enum, not string
        assert loaded is not None
        assert isinstance(loaded.invoice_subtype, InvoiceSubtype)
        assert loaded.invoice_subtype == InvoiceSubtype.STANDARD_INVOICE

    @pytest.mark.asyncio
    async def test_all_subtypes_persist_correctly(self, db_session):
        """All InvoiceSubtype values must persist and load correctly"""
        for idx, subtype in enumerate(InvoiceSubtype):
            invoice = Invoice(
                id=f"test-all-subtypes-{idx}",
                file_path="test/path.pdf",
                file_name="test.pdf",
                upload_date=datetime.utcnow(),
                vendor_name=f"Vendor {idx}",
                invoice_subtype=subtype,
            )
            
            await DatabaseService.save_invoice(invoice, db=db_session)
            loaded = await DatabaseService.get_invoice(f"test-all-subtypes-{idx}", db=db_session)
            
            assert loaded.invoice_subtype == subtype
            assert isinstance(loaded.invoice_subtype, InvoiceSubtype)

    def test_default_subtype_is_enum(self):
        """Default invoice_subtype must be an Enum, not string"""
        invoice = Invoice(
            id="test-default",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            # invoice_subtype not specified → uses default
        )
        
        # Default should be STANDARD_INVOICE Enum
        assert invoice.invoice_subtype is not None
        assert isinstance(invoice.invoice_subtype, InvoiceSubtype)
        assert invoice.invoice_subtype == InvoiceSubtype.STANDARD_INVOICE

    def test_pydantic_model_enforces_enum_type(self):
        """Pydantic Invoice model must enforce Enum type"""
        # This should work (Enum)
        invoice_enum = Invoice(
            id="test-enum-type",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            invoice_subtype=InvoiceSubtype.TIMESHEET_INVOICE if hasattr(InvoiceSubtype, 'TIMESHEET_INVOICE') else InvoiceSubtype.STANDARD_INVOICE,
        )
        assert isinstance(invoice_enum.invoice_subtype, InvoiceSubtype)
        
        # This should also work (None)
        invoice_none = Invoice(
            id="test-none-type",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            invoice_subtype=None,
        )
        assert invoice_none.invoice_subtype is None

    @pytest.mark.asyncio
    async def test_update_subtype_preserves_type(self, db_session):
        """Updating invoice_subtype must preserve Enum type"""
        # Create with one subtype
        invoice = Invoice(
            id="test-update-subtype",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Original Vendor",
            invoice_subtype=InvoiceSubtype.STANDARD_INVOICE,
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Update with different subtype
        invoice_update = Invoice(
            id="test-update-subtype",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Updated Vendor",
            invoice_subtype=InvoiceSubtype.SHIFT_SERVICE_INVOICE,
        )
        await DatabaseService.save_invoice(invoice_update, db=db_session)
        
        # Load and verify
        loaded = await DatabaseService.get_invoice("test-update-subtype", db=db_session)
        assert loaded.invoice_subtype == InvoiceSubtype.SHIFT_SERVICE_INVOICE
        assert isinstance(loaded.invoice_subtype, InvoiceSubtype)

