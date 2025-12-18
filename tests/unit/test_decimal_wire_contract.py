"""P1 contract stability tests: Decimal wire representation (string, not float)"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.models.invoice import Invoice, LineItem
from src.models.db_utils import line_items_to_json, json_to_line_items, _sanitize_tax_breakdown
from src.models.decimal_wire import decimal_to_wire, wire_to_decimal
from src.services.db_service import DatabaseService


class TestDecimalWireContract:
    """Test that Decimal values are represented as strings (not floats) on the wire"""

    def test_decimal_to_wire_basic(self):
        """decimal_to_wire must convert Decimals to non-exponent strings"""
        assert decimal_to_wire(Decimal("123.45")) == "123.45"
        assert decimal_to_wire(Decimal("0.1")) == "0.1"
        assert decimal_to_wire(Decimal("0.0000001")) == "0.0000001"
        assert decimal_to_wire(None) is None
        
        # No scientific notation
        result = decimal_to_wire(Decimal("1E+10"))
        assert "E" not in result and "e" not in result
        assert result == "10000000000"

    def test_wire_to_decimal_basic(self):
        """wire_to_decimal must parse strings to Decimal safely"""
        assert wire_to_decimal("123.45") == Decimal("123.45")
        assert wire_to_decimal("0.1") == Decimal("0.1")
        assert wire_to_decimal(None) is None
        assert wire_to_decimal("") is None
        
        # Parse from various types
        assert wire_to_decimal(123) == Decimal("123")
        assert wire_to_decimal(Decimal("456.78")) == Decimal("456.78")

    def test_line_items_to_json_uses_decimal_strings_not_floats(self):
        """P1: line_items_to_json must serialize Decimals as strings"""
        items = [
            LineItem(
                line_number=1,
                description="Test Item",
                quantity=Decimal("0.1"),
                unit_price=Decimal("0.2"),
                amount=Decimal("0.02"),  # 0.1 * 0.2
                tax_rate=Decimal("0.05"),
                tax_amount=Decimal("0.001"),
                gst_amount=Decimal("0.001"),
                pst_amount=Decimal("0.0"),
                combined_tax=Decimal("0.001"),
                confidence=0.9,
            )
        ]
        
        json_result = line_items_to_json(items)
        
        assert isinstance(json_result, list)
        assert len(json_result) == 1
        
        item_json = json_result[0]
        
        # All decimal fields must be strings, not floats
        assert isinstance(item_json["quantity"], str)
        assert item_json["quantity"] == "0.1"
        
        assert isinstance(item_json["unit_price"], str)
        assert item_json["unit_price"] == "0.2"
        
        assert isinstance(item_json["amount"], str)
        assert item_json["amount"] == "0.02"
        
        assert isinstance(item_json["tax_rate"], str)
        assert item_json["tax_rate"] == "0.05"
        
        assert isinstance(item_json["tax_amount"], str)
        assert item_json["tax_amount"] == "0.001"
        
        assert isinstance(item_json["gst_amount"], str)
        assert item_json["gst_amount"] == "0.001"
        
        assert isinstance(item_json["pst_amount"], str)
        assert item_json["pst_amount"] == "0"
        
        assert isinstance(item_json["combined_tax"], str)
        assert item_json["combined_tax"] == "0.001"

    def test_line_items_roundtrip_preserves_precision(self):
        """P1: Round-trip through JSON must preserve Decimal precision"""
        original_items = [
            LineItem(
                line_number=1,
                description="Precision Test",
                quantity=Decimal("1.23456789"),
                unit_price=Decimal("10.98765432"),
                amount=Decimal("13.55670370"),
                tax_rate=Decimal("0.13"),
                tax_amount=Decimal("1.76237148"),
                confidence=0.85,
            ),
            LineItem(
                line_number=2,
                description="Float Problem Test",
                quantity=Decimal("0.1"),  # Classic float problem: 0.1 can't be exactly represented
                unit_price=Decimal("0.2"),
                amount=Decimal("0.02"),
                confidence=0.90,
            ),
        ]
        
        # Serialize to JSON
        json_data = line_items_to_json(original_items)
        
        # Deserialize back
        restored_items = json_to_line_items(json_data)
        
        # Must preserve exact Decimal values
        assert len(restored_items) == 2
        
        assert restored_items[0].quantity == Decimal("1.23456789")
        assert restored_items[0].unit_price == Decimal("10.98765432")
        assert restored_items[0].amount == Decimal("13.55670370")
        assert restored_items[0].tax_rate == Decimal("0.13")
        assert restored_items[0].tax_amount == Decimal("1.76237148")
        
        # This would fail with float: float(0.1) * float(0.2) != 0.02
        assert restored_items[1].quantity == Decimal("0.1")
        assert restored_items[1].unit_price == Decimal("0.2")
        assert restored_items[1].amount == Decimal("0.02")

    def test_tax_breakdown_uses_decimal_strings(self):
        """P1: _sanitize_tax_breakdown must serialize Decimals as strings"""
        tax_breakdown = {
            "GST": Decimal("5.00"),
            "PST": Decimal("7.00"),
            "HST": Decimal("13.00"),
            "QST": Decimal("9.975"),
        }
        
        sanitized = _sanitize_tax_breakdown(tax_breakdown)
        
        # All values must be strings
        assert isinstance(sanitized["GST"], str)
        assert sanitized["GST"] == "5"
        
        assert isinstance(sanitized["PST"], str)
        assert sanitized["PST"] == "7"
        
        assert isinstance(sanitized["HST"], str)
        assert sanitized["HST"] == "13"
        
        assert isinstance(sanitized["QST"], str)
        assert sanitized["QST"] == "9.975"

    @pytest.mark.asyncio
    async def test_db_roundtrip_preserves_decimal_precision(self, db_session):
        """P1: Database round-trip must preserve Decimal precision for line items"""
        invoice = Invoice(
            id="test-decimal-precision",
            file_path="test/path.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow(),
            vendor_name="Precision Vendor",
            subtotal=Decimal("100.33"),
            tax_amount=Decimal("13.04"),
            total_amount=Decimal("113.37"),
            tax_breakdown={
                "GST": Decimal("5.02"),
                "PST": Decimal("8.02"),
            },
            line_items=[
                LineItem(
                    line_number=1,
                    description="Item with problematic decimals",
                    quantity=Decimal("0.1"),
                    unit_price=Decimal("0.3"),
                    amount=Decimal("0.03"),
                    tax_rate=Decimal("0.13"),
                    tax_amount=Decimal("0.0039"),
                    gst_amount=Decimal("0.0015"),
                    pst_amount=Decimal("0.0024"),
                    confidence=0.8,
                ),
            ],
        )
        
        # Save to DB
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Load from DB
        loaded = await DatabaseService.get_invoice("test-decimal-precision", db=db_session)
        
        # Header decimals must be preserved
        assert loaded.subtotal == Decimal("100.33")
        assert loaded.tax_amount == Decimal("13.04")
        assert loaded.total_amount == Decimal("113.37")
        
        # Tax breakdown decimals must be preserved
        assert loaded.tax_breakdown["GST"] == Decimal("5.02")
        assert loaded.tax_breakdown["PST"] == Decimal("8.02")
        
        # Line item decimals must be preserved
        assert len(loaded.line_items) == 1
        item = loaded.line_items[0]
        assert item.quantity == Decimal("0.1")
        assert item.unit_price == Decimal("0.3")
        assert item.amount == Decimal("0.03")
        assert item.tax_rate == Decimal("0.13")
        assert item.tax_amount == Decimal("0.0039")
        assert item.gst_amount == Decimal("0.0015")
        assert item.pst_amount == Decimal("0.0024")

    def test_no_float_artifacts(self):
        """Ensure no float precision artifacts like 0.30000000000000004"""
        # Classic float problem
        float_result = 0.1 + 0.2  # = 0.30000000000000004 in float
        decimal_result = Decimal("0.1") + Decimal("0.2")  # = exactly 0.3
        
        # Our wire format should use Decimal
        assert decimal_result == Decimal("0.3")
        
        # Serialize and deserialize
        wire_str = decimal_to_wire(decimal_result)
        assert wire_str == "0.3"  # No artifacts
        
        restored = wire_to_decimal(wire_str)
        assert restored == Decimal("0.3")

    def test_decimal_wire_handles_edge_cases(self):
        """Test edge cases for decimal wire conversion"""
        # Zero
        assert decimal_to_wire(Decimal("0")) == "0"
        assert decimal_to_wire(Decimal("0.0")) == "0"
        
        # Negative
        assert decimal_to_wire(Decimal("-123.45")) == "-123.45"
        
        # Very small
        assert decimal_to_wire(Decimal("0.00000001")) == "0.00000001"
        
        # Very large
        large = Decimal("999999999999.99")
        result = decimal_to_wire(large)
        assert "E" not in result and "e" not in result
        assert result == "999999999999.99"

    def test_line_items_none_values_preserved(self):
        """None values in line items must remain None, not become 0 or empty string"""
        items = [
            LineItem(
                line_number=1,
                description="Optional fields test",
                quantity=Decimal("1"),
                unit_price=Decimal("10.00"),
                amount=Decimal("10.00"),
                tax_rate=None,  # Optional
                tax_amount=None,  # Optional
                gst_amount=None,
                pst_amount=None,
                qst_amount=None,
                combined_tax=None,
                confidence=0.9,
            )
        ]
        
        json_data = line_items_to_json(items)
        item_json = json_data[0]
        
        # None values must be preserved as None, not "null" string or 0
        assert item_json["tax_rate"] is None
        assert item_json["tax_amount"] is None
        assert item_json["gst_amount"] is None
        assert item_json["pst_amount"] is None
        assert item_json["qst_amount"] is None
        assert item_json["combined_tax"] is None
        
        # Round-trip must preserve None
        restored = json_to_line_items(json_data)
        assert restored[0].tax_rate is None
        assert restored[0].tax_amount is None

