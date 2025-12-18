import pytest
from datetime import datetime, date
from decimal import Decimal

from src.models.invoice import Invoice, Address, LineItem
from src.services.db_service import DatabaseService
from src.models.db_utils import pydantic_to_db_invoice, db_to_pydantic_invoice


def _sample_invoice():
    return Invoice(
        id="inv-1",
        file_path="storage/raw/test.pdf",
        file_name="test.pdf",
        upload_date=datetime(2024, 1, 1, 10, 0, 0),
        status="extracted",
        invoice_number="INV-123",
        invoice_date=date(2024, 1, 2),
        due_date=date(2024, 2, 2),
        vendor_name="Acme",
        vendor_id="V001",
        vendor_phone="555-1111",
        vendor_address=Address(
            street="1 Main",
            city="Metropolis",
            province="BC",
            postal_code="V1V1V1",
            country="CA",
        ),
        customer_name="CATSA",
        customer_id="C001",
        entity="EntityA",
        bill_to_address=Address(
            street="2 Center",
            city="Vancouver",
            province="BC",
            postal_code="V2V2V2",
            country="CA",
        ),
        remit_to_address=Address(
            street="3 Pay",
            city="Calgary",
            province="AB",
            postal_code="T2T2T2",
            country="CA",
        ),
        remit_to_name="Remit Name",
        contract_id="C-9",
        standing_offer_number="SO-77",
        po_number="PO-55",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        subtotal=Decimal("100.00"),
        tax_breakdown={"GST": "5.00"},
        tax_amount=Decimal("5.00"),
        total_amount=Decimal("105.00"),
        currency="CAD",
        acceptance_percentage=Decimal("12.5"),
        tax_registration_number="TX-123",
        payment_terms="Net 30",
        field_confidence={"total_amount": 0.8, "vendor_name": 0.9, "tax_amount": 0.75},
        created_at=datetime(2024, 1, 1, 10, 0, 0),
        updated_at=datetime(2024, 1, 1, 10, 0, 0),
    )


def test_db_utils_roundtrip_preserves_fields():
    inv = _sample_invoice()
    db_model = pydantic_to_db_invoice(inv)
    back = db_to_pydantic_invoice(db_model)

    assert back.vendor_id == inv.vendor_id
    assert back.vendor_phone == inv.vendor_phone
    assert back.bill_to_address.city == inv.bill_to_address.city
    assert back.remit_to_address.city == inv.remit_to_address.city
    assert back.standing_offer_number == inv.standing_offer_number
    assert back.acceptance_percentage == inv.acceptance_percentage
    assert back.tax_registration_number == inv.tax_registration_number
    assert back.field_confidence == inv.field_confidence


@pytest.mark.asyncio
async def test_db_service_save_invoice_patch_semantics(db_session):
    inv = _sample_invoice()
    saved = await DatabaseService.save_invoice(inv, db=db_session)
    created_at = saved.created_at

    # update with some fields None (should not overwrite) and some updated
    inv_updated = _sample_invoice()
    inv_updated.vendor_name = None  # should remain "Acme"
    inv_updated.total_amount = Decimal("125.00")  # should update
    inv_updated.field_confidence = {"total_amount": 0.6}

    saved2 = await DatabaseService.save_invoice(inv_updated, db=db_session)
    assert saved2.vendor_name == "Acme"
    assert saved2.total_amount == Decimal("125.00")
    assert saved2.created_at == created_at
    assert saved2.updated_at >= created_at


@pytest.mark.asyncio
async def test_save_invoice_does_not_clobber_unset_fields(db_session):
    inv = _sample_invoice()
    # Add line items and save initial record
    inv.line_items = [
        LineItem(
            line_number=1,
            description="Initial A",
            quantity=Decimal("1"),
            unit_price=Decimal("10.00"),
            amount=Decimal("10.00"),
            confidence=0.8,
        )
    ]
    await DatabaseService.save_invoice(inv, db=db_session)

    # Patch only vendor_name; omit line_items and addresses
    inv_patch = Invoice(
        id=inv.id,
        file_path=inv.file_path,
        file_name=inv.file_name,
        upload_date=inv.upload_date,
        status=inv.status,
        vendor_name="Updated Vendor",
    )
    await DatabaseService.save_invoice(inv_patch, db=db_session)

    fetched = await DatabaseService.get_invoice(inv.id, db=db_session)
    assert fetched.vendor_name == "Updated Vendor"
    assert len(fetched.line_items) == len(inv.line_items)
    assert fetched.vendor_address.city == inv.vendor_address.city


@pytest.mark.asyncio
async def test_save_invoice_updates_line_items_when_set(db_session):
    inv = _sample_invoice()
    inv.line_items = [
        LineItem(
            line_number=1,
            description="Initial A",
            quantity=Decimal("1"),
            unit_price=Decimal("10.00"),
            amount=Decimal("10.00"),
            confidence=0.8,
        )
    ]
    await DatabaseService.save_invoice(inv, db=db_session)

    new_items = [
        LineItem(
            line_number=1,
            description="Replacement Item",
            quantity=Decimal("2"),
            unit_price=Decimal("50.00"),
            amount=Decimal("100.00"),
            confidence=0.9,
        )
    ]
    inv_patch = Invoice(
        id=inv.id,
        file_path=inv.file_path,
        file_name=inv.file_name,
        upload_date=inv.upload_date,
        status=inv.status,
        line_items=new_items,
    )
    await DatabaseService.save_invoice(inv_patch, db=db_session)

    fetched = await DatabaseService.get_invoice(inv.id, db=db_session)
    assert len(fetched.line_items) == 1
    assert fetched.line_items[0].description == "Replacement Item"
    assert fetched.vendor_address.city == inv.vendor_address.city

