"""P0 regression tests: prevent line_items data clobbering"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.models.invoice import Invoice, LineItem, Address
from src.models.db_utils import line_items_to_json, pydantic_to_db_invoice
from src.services.db_service import DatabaseService


class TestLineItemsClobberingPrevention:
    """Test that line_items cannot be accidentally wiped by partial saves"""

    def test_line_items_to_json_distinguishes_none_vs_empty(self):
        """line_items_to_json must distinguish None (unset) from [] (explicit empty)"""
        # None → None (unset)
        assert line_items_to_json(None) is None
        
        # Empty list → [] (explicit empty, but treated conservatively)
        assert line_items_to_json([]) == []
        
        # Items → JSON list
        items = [
            LineItem(
                line_number=1,
                description="Item 1",
                quantity=Decimal("1"),
                unit_price=Decimal("10.00"),
                amount=Decimal("10.00"),
                confidence=0.9,
            )
        ]
        result = line_items_to_json(items)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["description"] == "Item 1"

    @pytest.mark.asyncio
    async def test_unset_line_items_does_not_wipe(self, db_session):
        """P0: Unset line_items must NOT overwrite existing line items in DB"""
        # Seed DB with invoice containing line items
        initial_items = [
            LineItem(
                line_number=1,
                description="Initial Item 1",
                quantity=Decimal("2"),
                unit_price=Decimal("50.00"),
                amount=Decimal("100.00"),
                confidence=0.85,
            ),
            LineItem(
                line_number=2,
                description="Initial Item 2",
                quantity=Decimal("1"),
                unit_price=Decimal("30.00"),
                amount=Decimal("30.00"),
                confidence=0.90,
            ),
        ]
        
        invoice_initial = Invoice(
            id="test-unset-line-items",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Initial Vendor",
            total_amount=Decimal("130.00"),
            line_items=initial_items,
        )
        
        await DatabaseService.save_invoice(invoice_initial, db=db_session)
        
        # Partial update: change vendor_name, do NOT provide line_items
        invoice_update = Invoice(
            id="test-unset-line-items",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Updated Vendor",
            # line_items NOT provided (unset)
        )
        
        await DatabaseService.save_invoice(invoice_update, db=db_session)
        
        # Verify line items were NOT wiped
        loaded = await DatabaseService.get_invoice("test-unset-line-items", db=db_session)
        assert loaded is not None
        assert loaded.vendor_name == "Updated Vendor"
        assert len(loaded.line_items) == 2
        assert loaded.line_items[0].description == "Initial Item 1"
        assert loaded.line_items[1].description == "Initial Item 2"

    @pytest.mark.asyncio
    async def test_explicit_empty_list_does_not_wipe_conservative(self, db_session):
        """P0: Explicit empty list [] must NOT wipe existing line items (conservative behavior)"""
        # Seed DB with invoice containing line items
        initial_items = [
            LineItem(
                line_number=1,
                description="Item to preserve",
                quantity=Decimal("1"),
                unit_price=Decimal("100.00"),
                amount=Decimal("100.00"),
                confidence=0.8,
            ),
        ]
        
        invoice_initial = Invoice(
            id="test-explicit-empty",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Vendor A",
            line_items=initial_items,
        )
        
        await DatabaseService.save_invoice(invoice_initial, db=db_session)
        
        # Update with explicitly empty line_items list
        invoice_update = Invoice(
            id="test-explicit-empty",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Vendor B",
            line_items=[],  # Explicitly provided empty list
        )
        
        await DatabaseService.save_invoice(invoice_update, db=db_session)
        
        # Verify line items were NOT wiped (conservative behavior)
        loaded = await DatabaseService.get_invoice("test-explicit-empty", db=db_session)
        assert loaded is not None
        assert loaded.vendor_name == "Vendor B"
        assert len(loaded.line_items) == 1  # Still has the original item
        assert loaded.line_items[0].description == "Item to preserve"

    @pytest.mark.asyncio
    async def test_explicit_non_empty_list_replaces(self, db_session):
        """Explicit non-empty list must replace existing line items"""
        # Seed DB with invoice containing line items
        initial_items = [
            LineItem(
                line_number=1,
                description="Old Item",
                quantity=Decimal("1"),
                unit_price=Decimal("50.00"),
                amount=Decimal("50.00"),
                confidence=0.7,
            ),
        ]
        
        invoice_initial = Invoice(
            id="test-replace-items",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Vendor X",
            line_items=initial_items,
        )
        
        await DatabaseService.save_invoice(invoice_initial, db=db_session)
        
        # Update with new line items
        new_items = [
            LineItem(
                line_number=1,
                description="New Item A",
                quantity=Decimal("3"),
                unit_price=Decimal("25.00"),
                amount=Decimal("75.00"),
                confidence=0.95,
            ),
            LineItem(
                line_number=2,
                description="New Item B",
                quantity=Decimal("1"),
                unit_price=Decimal("10.00"),
                amount=Decimal("10.00"),
                confidence=0.92,
            ),
        ]
        
        invoice_update = Invoice(
            id="test-replace-items",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Vendor Y",
            line_items=new_items,  # Explicitly provided new items
        )
        
        await DatabaseService.save_invoice(invoice_update, db=db_session)
        
        # Verify line items were replaced
        loaded = await DatabaseService.get_invoice("test-replace-items", db=db_session)
        assert loaded is not None
        assert loaded.vendor_name == "Vendor Y"
        assert len(loaded.line_items) == 2
        assert loaded.line_items[0].description == "New Item A"
        assert loaded.line_items[1].description == "New Item B"

    @pytest.mark.asyncio
    async def test_multiple_partial_updates_preserve_line_items(self, db_session):
        """Multiple partial updates must not accidentally wipe line items"""
        # Initial save with line items
        invoice = Invoice(
            id="test-multiple-updates",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Vendor 1",
            total_amount=Decimal("200.00"),
            line_items=[
                LineItem(
                    line_number=1,
                    description="Persistent Item",
                    quantity=Decimal("2"),
                    unit_price=Decimal("100.00"),
                    amount=Decimal("200.00"),
                    confidence=0.88,
                ),
            ],
        )
        
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Update 1: change vendor_name
        update1 = Invoice(
            id="test-multiple-updates",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Vendor 2",
        )
        await DatabaseService.save_invoice(update1, db=db_session)
        
        # Update 2: change total_amount
        update2 = Invoice(
            id="test-multiple-updates",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            total_amount=Decimal("250.00"),
        )
        await DatabaseService.save_invoice(update2, db=db_session)
        
        # Update 3: change status
        update3 = Invoice(
            id="test-multiple-updates",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            status="validated",
        )
        await DatabaseService.save_invoice(update3, db=db_session)
        
        # Verify line items survived all updates
        loaded = await DatabaseService.get_invoice("test-multiple-updates", db=db_session)
        assert loaded is not None
        assert loaded.vendor_name == "Vendor 2"
        assert loaded.total_amount == Decimal("250.00")
        assert loaded.status == "validated"
        assert len(loaded.line_items) == 1
        assert loaded.line_items[0].description == "Persistent Item"

    @pytest.mark.asyncio
    async def test_retry_scenario_preserves_line_items(self, db_session):
        """Simulated retry scenario: partial save after extraction must not wipe line items"""
        # Simulate initial extraction with full data
        invoice_extracted = Invoice(
            id="test-retry-scenario",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Extracted Vendor",
            invoice_number="INV-001",
            total_amount=Decimal("500.00"),
            line_items=[
                LineItem(
                    line_number=1,
                    description="Extracted Item 1",
                    quantity=Decimal("5"),
                    unit_price=Decimal("100.00"),
                    amount=Decimal("500.00"),
                    confidence=0.75,
                ),
            ],
        )
        
        await DatabaseService.save_invoice(invoice_extracted, db=db_session)
        
        # Simulate retry or partial update (e.g., only updating status or metadata)
        invoice_retry = Invoice(
            id="test-retry-scenario",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            status="processing",  # Only updating status
        )
        
        await DatabaseService.save_invoice(invoice_retry, db=db_session)
        
        # Verify line items are intact
        loaded = await DatabaseService.get_invoice("test-retry-scenario", db=db_session)
        assert loaded is not None
        assert loaded.status == "processing"
        assert len(loaded.line_items) == 1
        assert loaded.line_items[0].description == "Extracted Item 1"

    @pytest.mark.asyncio
    async def test_line_items_with_addresses_independent(self, db_session):
        """line_items and addresses must be independently updatable without affecting each other"""
        # Initial invoice with both line items and addresses
        invoice = Invoice(
            id="test-independent-updates",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Vendor",
            line_items=[
                LineItem(
                    line_number=1,
                    description="Item A",
                    quantity=Decimal("1"),
                    unit_price=Decimal("50.00"),
                    amount=Decimal("50.00"),
                    confidence=0.8,
                ),
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
        
        # Update only address
        invoice_update_address = Invoice(
            id="test-independent-updates",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Vendor",
            vendor_address=Address(
                street="456 Oak Ave",
                city="Vancouver",
                province="BC",
                postal_code="V2V2V2",
                country="CA",
            ),
        )
        
        await DatabaseService.save_invoice(invoice_update_address, db=db_session)
        
        # Verify line items intact, address updated
        loaded = await DatabaseService.get_invoice("test-independent-updates", db=db_session)
        assert loaded is not None
        assert len(loaded.line_items) == 1
        assert loaded.line_items[0].description == "Item A"
        assert loaded.vendor_address.street == "456 Oak Ave"

    def test_pydantic_to_db_converter_preserves_line_items_intent(self):
        """Converter must preserve intent: None, [], or [items]"""
        # Test with items
        invoice_with_items = Invoice(
            id="test-conv-1",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            line_items=[
                LineItem(
                    line_number=1,
                    description="Item",
                    quantity=Decimal("1"),
                    unit_price=Decimal("10.00"),
                    amount=Decimal("10.00"),
                    confidence=0.9,
                ),
            ],
        )
        
        db_invoice = pydantic_to_db_invoice(invoice_with_items)
        assert db_invoice.line_items is not None
        assert isinstance(db_invoice.line_items, list)
        assert len(db_invoice.line_items) == 1
        
        # Test with explicit empty (will be [] in DB representation)
        invoice_empty = Invoice(
            id="test-conv-2",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            line_items=[],
        )
        
        db_invoice_empty = pydantic_to_db_invoice(invoice_empty)
        # Converter calls line_items_to_json([]) which now returns []
        assert db_invoice_empty.line_items == []

