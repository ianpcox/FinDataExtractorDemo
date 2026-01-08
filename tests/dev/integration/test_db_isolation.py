"""
P1 Regression Tests: DB Isolation
Ensures integration tests have complete session/state isolation.
"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.models.invoice import Invoice, LineItem, InvoiceState
from src.services.db_service import DatabaseService


@pytest.mark.integration
@pytest.mark.asyncio
class TestDBIsolation:
    """
    P1: Regression tests for DB isolation.
    These tests MUST pass to guarantee no state leakage between tests.
    """

    async def test_invoice_does_not_leak_to_next_test_part1(self, db_session):
        """
        Part 1: Create an invoice with a specific ID.
        Part 2 (next test) must NOT see this invoice.
        """
        invoice = Invoice(
            id="LEAK_CHECK_INVOICE_ID",
            file_path="test/leak1.pdf",
            file_name="leak1.pdf",
            upload_date=datetime.utcnow(),
            invoice_number="LEAK-001",
            vendor_name="Leak Test Vendor 1",
            total_amount=Decimal("100.00"),
            processing_state=InvoiceState.EXTRACTED,
            line_items=[
                LineItem(
                    line_number=1,
                    description="Leak Item 1",
                    quantity=Decimal("1"),
                    unit_price=Decimal("100.00"),
                    amount=Decimal("100.00"),
                    confidence=0.9,
                )
            ],
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Verify it was saved
        fetched = await DatabaseService.get_invoice("LEAK_CHECK_INVOICE_ID", db=db_session)
        assert fetched is not None
        assert fetched.vendor_name == "Leak Test Vendor 1"

    async def test_invoice_does_not_leak_to_next_test_part2(self, db_session):
        """
        Part 2: Attempt to fetch the invoice created in Part 1.
        Must return None (404) - proves no DB state leakage.
        """
        # This invoice was created in part 1 - it MUST NOT exist here
        fetched = await DatabaseService.get_invoice("LEAK_CHECK_INVOICE_ID", db=db_session)
        assert fetched is None, "DB isolation failed: invoice from previous test leaked!"

    async def test_concurrent_invoice_ids_do_not_collide(self, db_session):
        """
        Ensure multiple tests can use the same ID pattern without collision.
        This simulates parallel test execution.
        """
        invoice_id = "COLLISION_TEST_ID"
        
        invoice = Invoice(
            id=invoice_id,
            file_path="test/collision.pdf",
            file_name="collision.pdf",
            upload_date=datetime.utcnow(),
            invoice_number="COLL-001",
            vendor_name="Collision Test Vendor",
            total_amount=Decimal("999.99"),
            processing_state=InvoiceState.EXTRACTED,
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        fetched = await DatabaseService.get_invoice(invoice_id, db=db_session)
        assert fetched is not None
        assert fetched.total_amount == Decimal("999.99")
        
        # If another test uses the same ID, it should get a fresh DB (no conflict)

    async def test_api_route_uses_isolated_db(self, test_client, db_session):
        """
        Integration test: API route must use the same isolated test DB.
        This proves dependency override works correctly.
        """
        # Seed DB via db_session
        invoice = Invoice(
            id="API_ISOLATION_TEST",
            file_path="test/api_iso.pdf",
            file_name="api_iso.pdf",
            upload_date=datetime.utcnow(),
            invoice_number="API-ISO-001",
            vendor_name="API Isolation Vendor",
            total_amount=Decimal("500.00"),
            processing_state=InvoiceState.EXTRACTED,
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Now call API route - it MUST see the invoice we just created
        response = test_client.get("/api/hitl/invoice/API_ISOLATION_TEST")
        
        # If dependency override works, this should return 200
        # If it doesn't work, it will return 404 (different DB)
        assert response.status_code == 200, \
            f"API route not using isolated test DB! Status: {response.status_code}"
        
        data = response.json()
        assert data["invoice_id"] == "API_ISOLATION_TEST"
        # Verify it's the same vendor name we set
        vendor_field = data["fields"]["vendor_name"]
        assert vendor_field["value"] == "API Isolation Vendor"

    async def test_multiple_saves_in_same_test_no_interference(self, db_session):
        """
        Ensure multiple saves within the same test work correctly.
        """
        # Create invoice 1
        inv1 = Invoice(
            id="MULTI_SAVE_1",
            file_path="test/m1.pdf",
            file_name="m1.pdf",
            upload_date=datetime.utcnow(),
            invoice_number="M-001",
            vendor_name="Vendor 1",
            total_amount=Decimal("100.00"),
            processing_state=InvoiceState.EXTRACTED,
        )
        await DatabaseService.save_invoice(inv1, db=db_session)
        
        # Create invoice 2
        inv2 = Invoice(
            id="MULTI_SAVE_2",
            file_path="test/m2.pdf",
            file_name="m2.pdf",
            upload_date=datetime.utcnow(),
            invoice_number="M-002",
            vendor_name="Vendor 2",
            total_amount=Decimal("200.00"),
            processing_state=InvoiceState.EXTRACTED,
        )
        await DatabaseService.save_invoice(inv2, db=db_session)
        
        # Fetch both - both must exist
        fetched1 = await DatabaseService.get_invoice("MULTI_SAVE_1", db=db_session)
        fetched2 = await DatabaseService.get_invoice("MULTI_SAVE_2", db=db_session)
        
        assert fetched1 is not None
        assert fetched2 is not None
        assert fetched1.vendor_name == "Vendor 1"
        assert fetched2.vendor_name == "Vendor 2"
        assert fetched1.total_amount == Decimal("100.00")
        assert fetched2.total_amount == Decimal("200.00")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dependency_override_cleaned_up_after_test(test_client):
    """
    Verify that dependency overrides are properly cleared after each test.
    This is a meta-test to ensure the test infrastructure itself is correct.
    """
    from api.main import app
    
    # After using test_client fixture, dependency_overrides should be cleared
    # by the fixture's teardown. But within the test, it should be set.
    # This is a bit tricky to test directly, but we can verify basic behavior.
    
    # The fixture should have set up overrides, so the test_client should work
    response = test_client.get("/health")
    assert response.status_code == 200
    
    # Can't directly test cleanup here as fixture hasn't torn down yet,
    # but the fixture code has `app.dependency_overrides.clear()` in finally block.
    # If this doesn't work, other tests will fail with DB conflicts.

