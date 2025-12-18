"""
P1 Integration Tests: HITL Explicit Clear Semantics

Tests the HITL validate endpoint's clear_fields functionality.
"""

import pytest
import json
from datetime import datetime
from decimal import Decimal
from src.models.invoice import Invoice, InvoiceState, LineItem
from src.models.db_utils import pydantic_to_db_invoice
from src.services.db_service import DatabaseService


@pytest.fixture
def sample_hitl_invoice():
    """Invoice ready for HITL validation with data to clear"""
    return Invoice(
        id="hitl-clear-test-001",
        file_path="path/to/file.pdf",
        file_name="file.pdf",
        upload_date=datetime.utcnow(),
        invoice_number="HITL-CLR-001",
        vendor_name="Test Vendor",
        total_amount=Decimal("100.00"),
        processing_state=InvoiceState.EXTRACTED,
        status="extracted",
        review_version=0,
        line_items=[
            LineItem(
                line_number=1,
                description="Item 1",
                quantity=Decimal("2"),
                unit_price=Decimal("50.00"),
                amount=Decimal("100.00"),
                confidence=0.9,
            ),
        ],
        tax_breakdown={"GST": "5.00"},
        po_number="PO-CLEAR-TEST",
    )


@pytest.mark.integration
@pytest.mark.asyncio
class TestHITLExplicitClear:
    """Integration tests for HITL clear_fields functionality"""

    async def test_hitl_validate_with_clear_fields_success(self, test_client, db_session, sample_hitl_invoice):
        """
        Test that HITL validate endpoint successfully clears fields when clear_fields is provided
        """
        # Seed invoice
        invoice = sample_hitl_invoice
        db_invoice = pydantic_to_db_invoice(invoice)
        db_session.add(db_invoice)
        await db_session.commit()

        # Validate and clear line_items
        payload = {
            "invoice_id": invoice.id,
            "expected_review_version": 0,
            "overall_validation_status": "validated",
            "reviewer": "test_reviewer",
            "clear_fields": ["line_items", "tax_breakdown"],
        }

        response = test_client.post("/api/hitl/invoice/validate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["invoice_id"] == invoice.id

        # Verify fields were cleared in DB
        fetched = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert fetched.line_items == []  # Cleared
        assert fetched.tax_breakdown == {} or fetched.tax_breakdown is None  # Cleared
        assert fetched.review_version == 1  # Version incremented

    async def test_hitl_validate_clear_fields_invalid_field_rejected(self, test_client, db_session, sample_hitl_invoice):
        """
        Test that attempting to clear protected fields returns 400
        """
        # Seed invoice
        invoice = sample_hitl_invoice
        db_invoice = pydantic_to_db_invoice(invoice)
        db_session.add(db_invoice)
        await db_session.commit()

        # Attempt to clear protected field
        payload = {
            "invoice_id": invoice.id,
            "expected_review_version": 0,
            "overall_validation_status": "validated",
            "reviewer": "test_reviewer",
            "clear_fields": ["id"],  # Protected field!
        }

        response = test_client.post("/api/hitl/invoice/validate", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        detail = data["detail"]
        assert detail["error_code"] == "INVALID_CLEAR_FIELDS"
        assert "id" in detail["disallowed_fields"]

    async def test_hitl_validate_clear_fields_processing_state_rejected(self, test_client, db_session, sample_hitl_invoice):
        """
        Test that attempting to clear processing_state returns 400
        """
        # Seed invoice
        invoice = sample_hitl_invoice
        db_invoice = pydantic_to_db_invoice(invoice)
        db_session.add(db_invoice)
        await db_session.commit()

        # Attempt to clear processing_state
        payload = {
            "invoice_id": invoice.id,
            "expected_review_version": 0,
            "overall_validation_status": "validated",
            "reviewer": "test_reviewer",
            "clear_fields": ["processing_state"],  # Protected!
        }

        response = test_client.post("/api/hitl/invoice/validate", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "INVALID_CLEAR_FIELDS"

    async def test_hitl_validate_clear_fields_with_optimistic_lock(self, test_client, db_session, sample_hitl_invoice):
        """
        Test that clear_fields works with optimistic locking
        """
        # Seed invoice
        invoice = sample_hitl_invoice
        db_invoice = pydantic_to_db_invoice(invoice)
        db_session.add(db_invoice)
        await db_session.commit()

        # First clear with correct version
        payload1 = {
            "invoice_id": invoice.id,
            "expected_review_version": 0,
            "overall_validation_status": "validated",
            "reviewer": "reviewer1",
            "clear_fields": ["line_items"],
        }

        response1 = test_client.post("/api/hitl/invoice/validate", json=payload1)
        assert response1.status_code == 200

        # Second clear with stale version (should fail with 409)
        payload2 = {
            "invoice_id": invoice.id,
            "expected_review_version": 0,  # Stale!
            "overall_validation_status": "validated",
            "reviewer": "reviewer2",
            "clear_fields": ["tax_breakdown"],
        }

        response2 = test_client.post("/api/hitl/invoice/validate", json=payload2)
        assert response2.status_code == 409
        data2 = response2.json()
        assert data2["detail"]["error_code"] == "STALE_WRITE"

    async def test_hitl_validate_clear_fields_and_corrections_same_request(self, test_client, db_session, sample_hitl_invoice):
        """
        Test that clear_fields and field corrections can be applied in same request
        """
        # Seed invoice
        invoice = sample_hitl_invoice
        db_invoice = pydantic_to_db_invoice(invoice)
        db_session.add(db_invoice)
        await db_session.commit()

        # Clear line_items but update vendor_name
        payload = {
            "invoice_id": invoice.id,
            "expected_review_version": 0,
            "field_validations": [
                {
                    "field_name": "vendor_name",
                    "validated": True,
                    "corrected_value": "Updated Vendor Corp",
                    "confidence": 1.0,
                }
            ],
            "overall_validation_status": "validated",
            "reviewer": "test_reviewer",
            "clear_fields": ["line_items", "po_number"],
        }

        response = test_client.post("/api/hitl/invoice/validate", json=payload)

        assert response.status_code == 200

        # Verify both clear and update were applied
        fetched = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert fetched.line_items == []  # Cleared
        assert fetched.po_number is None  # Cleared
        assert fetched.vendor_name == "Updated Vendor Corp"  # Updated
        assert fetched.review_version == 1

    async def test_hitl_validate_clear_fields_empty_list_allowed(self, test_client, db_session, sample_hitl_invoice):
        """
        Test that clear_fields=[] (empty list) is valid and does nothing
        """
        # Seed invoice
        invoice = sample_hitl_invoice
        db_invoice = pydantic_to_db_invoice(invoice)
        db_session.add(db_invoice)
        await db_session.commit()

        # Empty clear_fields list (should be no-op for clears)
        payload = {
            "invoice_id": invoice.id,
            "expected_review_version": 0,
            "overall_validation_status": "validated",
            "reviewer": "test_reviewer",
            "clear_fields": [],  # Empty - no clears
        }

        response = test_client.post("/api/hitl/invoice/validate", json=payload)

        assert response.status_code == 200

        # Verify nothing was cleared
        fetched = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert len(fetched.line_items) == 1  # Preserved
        assert fetched.tax_breakdown is not None  # Preserved
        assert fetched.po_number == "PO-CLEAR-TEST"  # Preserved

    async def test_hitl_validate_clear_fields_not_provided_no_clear(self, test_client, db_session, sample_hitl_invoice):
        """
        Test that when clear_fields is not provided, no clears occur (backward compatible)
        """
        # Seed invoice
        invoice = sample_hitl_invoice
        db_invoice = pydantic_to_db_invoice(invoice)
        db_session.add(db_invoice)
        await db_session.commit()

        # No clear_fields in payload (backward compatible)
        payload = {
            "invoice_id": invoice.id,
            "expected_review_version": 0,
            "overall_validation_status": "validated",
            "reviewer": "test_reviewer",
            # clear_fields not provided
        }

        response = test_client.post("/api/hitl/invoice/validate", json=payload)

        assert response.status_code == 200

        # Verify nothing was cleared (backward compatible)
        fetched = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert len(fetched.line_items) == 1  # Preserved
        assert fetched.tax_breakdown is not None  # Preserved
        assert fetched.po_number == "PO-CLEAR-TEST"  # Preserved

