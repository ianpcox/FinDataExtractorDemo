import pytest
from datetime import datetime
from decimal import Decimal

from src.services.db_service import DatabaseService
from src.models.invoice import Invoice, LineItem, InvoiceState


def _sample_invoice(inv_id: str = "c-inv-1") -> Invoice:
    return Invoice(
        id=inv_id,
        file_path="p.pdf",
        file_name="p.pdf",
        upload_date=datetime.utcnow(),
        status="extracted",
        invoice_number="INV-1",
        total_amount=Decimal("10.00"),
        line_items=[
            LineItem(
                line_number=1,
                description="A",
                quantity=Decimal("1"),
                unit_price=Decimal("10.00"),
                amount=Decimal("10.00"),
                confidence=0.8,
            )
        ],
    )


@pytest.mark.asyncio
async def test_review_version_optimistic_lock(db_session):
    inv = _sample_invoice("c-lock-1")
    await DatabaseService.save_invoice(inv, db=db_session)

    # first update with expected version 0
    success = await DatabaseService.update_with_review_version(
        invoice_id=inv.id,
        patch={"status": "validated"},
        expected_review_version=0,
        db=db_session,
    )
    assert success is True

    # stale update with old version should fail
    success2 = await DatabaseService.update_with_review_version(
        invoice_id=inv.id,
        patch={"status": "validated"},
        expected_review_version=0,
        db=db_session,
    )
    assert success2 is False


@pytest.mark.asyncio
async def test_claim_for_extraction(db_session):
    inv = _sample_invoice("c-claim-1")
    await DatabaseService.save_invoice(inv, db=db_session)

    first = await DatabaseService.claim_for_extraction(inv.id, db=db_session)
    second = await DatabaseService.claim_for_extraction(inv.id, db=db_session)

    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_set_extraction_result_requires_processing_state(db_session):
    inv = _sample_invoice("c-process-1")
    await DatabaseService.save_invoice(inv, db=db_session)

    # Without claiming, should fail
    ok = await DatabaseService.set_extraction_result(
        invoice_id=inv.id,
        patch={"status": "extracted"},
        expected_processing_state="PROCESSING",
        db=db_session,
    )
    assert ok is False

    # Claim, then succeed
    claimed = await DatabaseService.claim_for_extraction(inv.id, db=db_session)
    assert claimed is True
    ok2 = await DatabaseService.set_extraction_result(
        invoice_id=inv.id,
        patch={"status": "extracted"},
        expected_processing_state="PROCESSING",
        db=db_session,
    )
    assert ok2 is True


@pytest.mark.asyncio
async def test_invalid_transition_processing_to_validated(db_session):
    inv = _sample_invoice("c-state-1")
    await DatabaseService.save_invoice(inv, db=db_session)
    claimed = await DatabaseService.claim_for_extraction(inv.id, db=db_session)
    assert claimed is True

    # Attempt invalid transition directly
    success = await DatabaseService.transition_state(
        invoice_id=inv.id,
        from_states={InvoiceState.EXTRACTED.value},
        to_state=InvoiceState.VALIDATED.value,
        error_on_invalid=False,
        db=db_session,
    )
    assert success is False

