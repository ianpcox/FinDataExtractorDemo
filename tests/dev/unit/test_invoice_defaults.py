from datetime import datetime
from decimal import Decimal

from src.models.invoice import Invoice, LineItem


def _fields_set(model) -> set:
    if hasattr(model, "model_fields_set"):
        return set(model.model_fields_set)
    return set(getattr(model, "__fields_set__", set()))


def test_line_items_default_not_set():
    inv = Invoice(
        id="t-1",
        file_path="p.pdf",
        file_name="p.pdf",
        upload_date=datetime.utcnow(),
        status="extracted",
        invoice_number="INV-1",
        total_amount=Decimal("1.00"),
    )
    assert inv.line_items == []
    assert "line_items" not in _fields_set(inv)


def test_line_items_explicit_empty_is_set():
    inv = Invoice(
        id="t-2",
        file_path="p.pdf",
        file_name="p.pdf",
        upload_date=datetime.utcnow(),
        status="extracted",
        invoice_number="INV-2",
        total_amount=Decimal("2.00"),
        line_items=[],
    )
    assert inv.line_items == []
    assert "line_items" in _fields_set(inv)


def test_line_items_explicit_values_set():
    inv = Invoice(
        id="t-3",
        file_path="p.pdf",
        file_name="p.pdf",
        upload_date=datetime.utcnow(),
        status="extracted",
        invoice_number="INV-3",
        total_amount=Decimal("3.00"),
        line_items=[
            LineItem(
                line_number=1,
                description="A",
                quantity=Decimal("1"),
                unit_price=Decimal("3.00"),
                amount=Decimal("3.00"),
                confidence=0.8,
            )
        ],
    )
    assert len(inv.line_items) == 1
    assert "line_items" in _fields_set(inv)

