"""
P1 tests: Explicit Clear Semantics

Tests that fields can be intentionally cleared using clear_fields without
reintroducing accidental clobber risks.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from src.models.invoice import Invoice, InvoiceState, LineItem, Address
from src.services.db_service import DatabaseService


@pytest.fixture
def sample_invoice_with_data() -> Invoice:
    """Invoice with populated fields for clear testing"""
    return Invoice(
        id="test-clear-invoice-1",
        file_path="path/to/file.pdf",
        file_name="file.pdf",
        upload_date=datetime.utcnow(),
        invoice_number="CLR-001",
        total_amount=Decimal("100.00"),
        processing_state=InvoiceState.EXTRACTED,
        review_version=0,
        line_items=[
            LineItem(
                line_number=1,
                description="Item 1",
                quantity=Decimal("1"),
                unit_price=Decimal("50.00"),
                amount=Decimal("50.00"),
                confidence=0.9,
            ),
            LineItem(
                line_number=2,
                description="Item 2",
                quantity=Decimal("1"),
                unit_price=Decimal("50.00"),
                amount=Decimal("50.00"),
                confidence=0.9,
            ),
        ],
        tax_breakdown={"GST": "5.00", "PST": "7.00"},
        review_notes="Test notes",
        po_number="PO-123",
    )


class TestExplicitClear:
    """Tests for explicit clear semantics"""

    @pytest.mark.asyncio
    async def test_default_patch_safe_no_accidental_clear(self, db_session, sample_invoice_with_data):
        """
        P1: Default behavior remains patch-safe - omitted fields do not change in DB
        """
        invoice = sample_invoice_with_data
        await DatabaseService.save_invoice(invoice, db=db_session)

        # Create a partial update that does NOT include line_items
        # Use update_with_review_version to simulate HITL update
        patch = {
            "vendor_name": "Updated Vendor",
            # line_items intentionally omitted
            # tax_breakdown intentionally omitted
        }

        success = await DatabaseService.update_with_review_version(
            invoice.id,
            patch,
            expected_review_version=0,
            db=db_session,
        )
        assert success is True

        # Verify line_items and tax_breakdown are unchanged
        fetched = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert fetched.vendor_name == "Updated Vendor"
        assert len(fetched.line_items) == 2  # NOT cleared
        assert fetched.line_items[0].description == "Item 1"
        assert fetched.line_items[1].description == "Item 2"
        assert fetched.tax_breakdown is not None  # NOT cleared
        assert "GST" in fetched.tax_breakdown

    @pytest.mark.asyncio
    async def test_empty_list_without_clear_flag_does_not_clear(self, db_session, sample_invoice_with_data):
        """
        P1: Sending empty list without clear_fields does NOT clear
        (conservative to prevent accidental clobber)
        """
        invoice = sample_invoice_with_data
        await DatabaseService.save_invoice(invoice, db=db_session)

        # Sending [] without explicit clear intent
        # Since update_with_review_version is a raw patch, we need to test via save_invoice
        # which has the conservative logic
        partial_invoice = Invoice(
            id=invoice.id,
            file_path=invoice.file_path,
            file_name=invoice.file_name,
            upload_date=invoice.upload_date,
            vendor_name="New Vendor",
            line_items=[],  # Empty list, but not explicitly marked for clear
        )
        # Mark line_items as explicitly set
        partial_invoice.model_fields_set.add("line_items") if hasattr(partial_invoice, "model_fields_set") else None

        # save_invoice with conservative logic should skip empty collections
        await DatabaseService.save_invoice(partial_invoice, db=db_session)

        fetched = await DatabaseService.get_invoice(invoice.id, db=db_session)
        # Conservative: empty list does not clear unless explicitly requested
        assert len(fetched.line_items) == 2  # Preserved

    @pytest.mark.asyncio
    async def test_explicit_clear_line_items(self, db_session, sample_invoice_with_data):
        """
        P1: Explicit clear via update_with_review_version clears line_items
        """
        invoice = sample_invoice_with_data
        await DatabaseService.save_invoice(invoice, db=db_session)

        # Explicitly clear line_items using proper DB format
        from src.models.db_utils import line_items_to_json
        patch = {
            "line_items": line_items_to_json([]),  # Explicit clear
        }

        success = await DatabaseService.update_with_review_version(
            invoice.id,
            patch,
            expected_review_version=0,
            db=db_session,
        )
        assert success is True

        fetched = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert fetched.line_items == []  # Cleared

    @pytest.mark.asyncio
    async def test_explicit_clear_tax_breakdown(self, db_session, sample_invoice_with_data):
        """
        P1: Explicit clear via update_with_review_version clears tax_breakdown
        """
        invoice = sample_invoice_with_data
        await DatabaseService.save_invoice(invoice, db=db_session)

        # Explicitly clear tax_breakdown (dict)
        patch = {
            "tax_breakdown": {},  # Explicit clear
        }

        success = await DatabaseService.update_with_review_version(
            invoice.id,
            patch,
            expected_review_version=0,
            db=db_session,
        )
        assert success is True

        fetched = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert fetched.tax_breakdown == {} or fetched.tax_breakdown is None  # Cleared

    @pytest.mark.asyncio
    async def test_explicit_clear_scalar_field(self, db_session, sample_invoice_with_data):
        """
        P1: Explicit clear of scalar field sets it to None
        """
        invoice = sample_invoice_with_data
        await DatabaseService.save_invoice(invoice, db=db_session)

        # Explicitly clear po_number
        patch = {
            "po_number": None,  # Explicit clear
        }

        success = await DatabaseService.update_with_review_version(
            invoice.id,
            patch,
            expected_review_version=0,
            db=db_session,
        )
        assert success is True

        fetched = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert fetched.po_number is None  # Cleared

    @pytest.mark.asyncio
    async def test_explicit_clear_with_optimistic_lock(self, db_session, sample_invoice_with_data):
        """
        P1: Explicit clear works with optimistic locking
        """
        invoice = sample_invoice_with_data
        await DatabaseService.save_invoice(invoice, db=db_session)

        # Clear line_items with correct version
        from src.models.db_utils import line_items_to_json
        patch = {
            "line_items": line_items_to_json([]),
        }

        success = await DatabaseService.update_with_review_version(
            invoice.id,
            patch,
            expected_review_version=0,
            db=db_session,
        )
        assert success is True

        fetched = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert fetched.review_version == 1  # Incremented
        assert fetched.line_items == []  # Cleared

        # Try to clear again with stale version (should fail)
        patch2 = {
            "tax_breakdown": {},
        }
        success2 = await DatabaseService.update_with_review_version(
            invoice.id,
            patch2,
            expected_review_version=0,  # Stale!
            db=db_session,
        )
        assert success2 is False  # Failed due to stale version

    @pytest.mark.asyncio
    async def test_explicit_clear_multiple_fields(self, db_session, sample_invoice_with_data):
        """
        P1: Can clear multiple fields in single atomic update
        """
        invoice = sample_invoice_with_data
        await DatabaseService.save_invoice(invoice, db=db_session)

        # Clear multiple fields at once
        from src.models.db_utils import line_items_to_json
        patch = {
            "line_items": line_items_to_json([]),
            "tax_breakdown": {},
            "po_number": None,
            "review_notes": None,
        }

        success = await DatabaseService.update_with_review_version(
            invoice.id,
            patch,
            expected_review_version=0,
            db=db_session,
        )
        assert success is True

        fetched = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert fetched.line_items == []
        assert fetched.tax_breakdown == {} or fetched.tax_breakdown is None
        assert fetched.po_number is None
        assert fetched.review_notes is None or fetched.review_notes == ""

    @pytest.mark.asyncio
    async def test_explicit_clear_and_update_same_request(self, db_session, sample_invoice_with_data):
        """
        P1: Can clear some fields and update others in same request
        """
        invoice = sample_invoice_with_data
        await DatabaseService.save_invoice(invoice, db=db_session)

        # Clear line_items but update vendor_name
        from src.models.db_utils import line_items_to_json
        patch = {
            "line_items": line_items_to_json([]),  # Clear
            "vendor_name": "New Vendor Name",  # Update
        }

        success = await DatabaseService.update_with_review_version(
            invoice.id,
            patch,
            expected_review_version=0,
            db=db_session,
        )
        assert success is True

        fetched = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert fetched.line_items == []  # Cleared
        assert fetched.vendor_name == "New Vendor Name"  # Updated

