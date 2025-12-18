"""Integration tests for HITL optimistic locking"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.services.db_service import DatabaseService
from src.models.invoice import Invoice, InvoiceState, LineItem, Address


@pytest.mark.integration
@pytest.mark.asyncio
class TestHITLOptimisticLocking:
    """Test HITL validation optimistic locking"""

    @pytest.fixture
    async def test_invoice(self, db_session):
        """Create a test invoice for validation"""
        invoice = Invoice(
            id="test-hitl-lock-001",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            status="extracted",
            processing_state=InvoiceState.EXTRACTED,
            review_version=0,
            invoice_number="INV-001",
            invoice_date=datetime(2024, 1, 1).date(),
            vendor_name="Test Vendor",
            total_amount=Decimal("100.00"),
            line_items=[
                LineItem(
                    line_number=1,
                    description="Test Item",
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
        await DatabaseService.save_invoice(invoice, db=db_session)
        return invoice

    async def test_hitl_validation_optimistic_lock_success(self, test_client, test_invoice, db_session):
        """Test successful validation with correct review_version"""
        validation_request = {
            "invoice_id": test_invoice.id,
            "expected_review_version": 0,
            "field_validations": [
                {
                    "field_name": "vendor_name",
                    "value": "Test Vendor",
                    "confidence": 0.9,
                    "validated": True,
                    "corrected_value": "Corrected Vendor",
                }
            ],
            "overall_validation_status": "validated",
            "reviewer": "test_reviewer",
        }

        response = test_client.post("/api/hitl/invoice/validate", json=validation_request)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["invoice_id"] == test_invoice.id

        # Verify review_version was incremented
        updated_invoice = await DatabaseService.get_invoice(test_invoice.id, db=db_session)
        assert updated_invoice.review_version == 1
        assert updated_invoice.vendor_name == "Corrected Vendor"

    async def test_hitl_validation_stale_write_returns_409(self, test_client, test_invoice, db_session):
        """Test that stale write (old review_version) returns 409 Conflict"""
        # First update: increment review_version to 1
        first_request = {
            "invoice_id": test_invoice.id,
            "expected_review_version": 0,
            "field_validations": [
                {
                    "field_name": "vendor_name",
                    "value": "Test Vendor",
                    "confidence": 0.9,
                    "validated": True,
                    "corrected_value": "First Update",
                }
            ],
            "overall_validation_status": "validated",
            "reviewer": "reviewer_1",
        }
        response1 = test_client.post("/api/hitl/invoice/validate", json=first_request)
        assert response1.status_code == 200

        # Second update: use stale review_version=0 (should be 1 now)
        second_request = {
            "invoice_id": test_invoice.id,
            "expected_review_version": 0,  # ← Stale version
            "field_validations": [
                {
                    "field_name": "vendor_name",
                    "value": "First Update",
                    "confidence": 0.9,
                    "validated": True,
                    "corrected_value": "Second Update (should fail)",
                }
            ],
            "overall_validation_status": "validated",
            "reviewer": "reviewer_2",
        }
        response2 = test_client.post("/api/hitl/invoice/validate", json=second_request)

        # Assert 409 Conflict
        assert response2.status_code == 409
        error_detail = response2.json()["detail"]
        assert error_detail["error_code"] == "STALE_WRITE"
        assert error_detail["message"] == "Invoice was updated by someone else."
        assert error_detail["current_review_version"] == 1
        assert error_detail["invoice_id"] == test_invoice.id
        assert error_detail["retryable"] is False

        # Verify invoice was NOT updated by second request
        final_invoice = await DatabaseService.get_invoice(test_invoice.id, db=db_session)
        assert final_invoice.review_version == 1
        assert final_invoice.vendor_name == "First Update"  # Not "Second Update"

    async def test_hitl_validation_correct_version_after_increment(self, test_client, test_invoice, db_session):
        """Test that using correct (incremented) review_version succeeds"""
        # First update
        first_request = {
            "invoice_id": test_invoice.id,
            "expected_review_version": 0,
            "field_validations": [
                {
                    "field_name": "vendor_name",
                    "value": "Test Vendor",
                    "confidence": 0.9,
                    "validated": True,
                    "corrected_value": "First Update",
                }
            ],
            "overall_validation_status": "validated",
            "reviewer": "reviewer_1",
        }
        response1 = test_client.post("/api/hitl/invoice/validate", json=first_request)
        assert response1.status_code == 200

        # Second update with CORRECT version (now 1)
        second_request = {
            "invoice_id": test_invoice.id,
            "expected_review_version": 1,  # ← Correct version
            "field_validations": [
                {
                    "field_name": "vendor_name",
                    "value": "First Update",
                    "confidence": 0.9,
                    "validated": True,
                    "corrected_value": "Second Update (should succeed)",
                }
            ],
            "overall_validation_status": "validated",
            "reviewer": "reviewer_2",
        }
        response2 = test_client.post("/api/hitl/invoice/validate", json=second_request)

        # Assert success
        assert response2.status_code == 200
        assert response2.json()["success"] is True

        # Verify invoice was updated
        final_invoice = await DatabaseService.get_invoice(test_invoice.id, db=db_session)
        assert final_invoice.review_version == 2
        assert final_invoice.vendor_name == "Second Update (should succeed)"

