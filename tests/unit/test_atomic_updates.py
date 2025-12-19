"""P0 tests: Atomic UPDATE for transition_state() and update_with_review_version()"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.models.invoice import Invoice, InvoiceState
from src.services.db_service import DatabaseService


@pytest.fixture
def sample_invoice_for_atomic_tests() -> Invoice:
    """Create a sample invoice for atomic update testing"""
    return Invoice(
        id="test-atomic-updates",
        file_path="test/path.pdf",
        file_name="test.pdf",
        upload_date=datetime.utcnow(),
        invoice_number="ATOM-001",
        total_amount=Decimal("100.00"),
        processing_state=InvoiceState.PENDING,
        review_version=0,
    )


class TestAtomicUpdates:
    """Test that UPDATE statements are atomic (no race conditions)"""

    @pytest.mark.asyncio
    async def test_transition_state_is_atomic(self, db_session, sample_invoice_for_atomic_tests):
        """
        P0: transition_state must use atomic UPDATE (not SELECT-then-UPDATE)
        to prevent race conditions.
        """
        invoice = sample_invoice_for_atomic_tests
        await DatabaseService.save_invoice(invoice, db=db_session)

        # First transition: PENDING -> PROCESSING (should succeed)
        success1 = await DatabaseService.transition_state(
            invoice.id,
            {InvoiceState.PENDING},
            InvoiceState.PROCESSING,
            db=db_session
        )
        assert success1 is True

        # Second transition: PENDING -> PROCESSING (should fail, already PROCESSING)
        success2 = await DatabaseService.transition_state(
            invoice.id,
            {InvoiceState.PENDING},
            InvoiceState.EXTRACTED,
            error_on_invalid=False,
            db=db_session
        )
        assert success2 is False  # Should not transition from wrong state

        # Verify state is still PROCESSING
        current_invoice = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert current_invoice.processing_state == InvoiceState.PROCESSING

    @pytest.mark.asyncio
    async def test_update_with_review_version_is_atomic(self, db_session, sample_invoice_for_atomic_tests):
        """
        P0: update_with_review_version must use atomic UPDATE (not SELECT-then-UPDATE)
        to prevent race conditions.
        """
        invoice = sample_invoice_for_atomic_tests
        await DatabaseService.save_invoice(invoice, db=db_session)

        # First update with version=0 (should succeed)
        patch1 = {"vendor_name": "Vendor A"}
        success1 = await DatabaseService.update_with_review_version(
            invoice.id,
            patch1,
            expected_review_version=0,
            db=db_session
        )
        assert success1 is True

        # Second update with stale version=0 (should fail)
        patch2 = {"vendor_name": "Vendor B"}
        success2 = await DatabaseService.update_with_review_version(
            invoice.id,
            patch2,
            expected_review_version=0,  # Stale version
            db=db_session
        )
        assert success2 is False  # Should not update with stale version

        # Verify only first update was applied
        current_invoice = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert current_invoice.vendor_name == "Vendor A"
        assert current_invoice.review_version == 1

    @pytest.mark.asyncio
    async def test_concurrent_review_version_updates_one_wins(self, db_session, sample_invoice_for_atomic_tests):
        """
        Simulate concurrent updates: only one should succeed, others get stale version
        """
        invoice = sample_invoice_for_atomic_tests
        await DatabaseService.save_invoice(invoice, db=db_session)

        # Simulate two reviewers trying to update simultaneously with same expected version
        patch_reviewer_1 = {"vendor_name": "Reviewer 1 Update"}
        patch_reviewer_2 = {"vendor_name": "Reviewer 2 Update"}

        # Both read version=0 and try to update
        success1 = await DatabaseService.update_with_review_version(
            invoice.id, patch_reviewer_1, expected_review_version=0, db=db_session
        )
        success2 = await DatabaseService.update_with_review_version(
            invoice.id, patch_reviewer_2, expected_review_version=0, db=db_session
        )

        # Only one should succeed
        assert (success1 and not success2) or (not success1 and success2)

        # Verify version incremented only once
        current_invoice = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert current_invoice.review_version == 1

    @pytest.mark.asyncio
    async def test_transition_state_prevents_invalid_transitions(self, db_session, sample_invoice_for_atomic_tests):
        """
        Verify that atomic transition_state prevents invalid state transitions
        """
        invoice = sample_invoice_for_atomic_tests
        invoice.processing_state = InvoiceState.EXTRACTED
        await DatabaseService.save_invoice(invoice, db=db_session)

        # Try to transition from PENDING (but invoice is EXTRACTED)
        with pytest.raises(ValueError, match="Invalid state transition"):
            await DatabaseService.transition_state(
                invoice.id,
                {InvoiceState.PENDING},
                InvoiceState.PROCESSING,
                error_on_invalid=True,
                db=db_session
            )

        # Verify state unchanged
        current_invoice = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert current_invoice.processing_state == InvoiceState.EXTRACTED

    @pytest.mark.asyncio
    async def test_update_with_review_version_increments_correctly(self, db_session, sample_invoice_for_atomic_tests):
        """
        Verify that review_version increments correctly across multiple updates
        """
        invoice = sample_invoice_for_atomic_tests
        await DatabaseService.save_invoice(invoice, db=db_session)

        # Series of updates with correct versions
        for i in range(5):
            patch = {"vendor_name": f"Vendor Update {i}"}
            success = await DatabaseService.update_with_review_version(
                invoice.id,
                patch,
                expected_review_version=i,
                db=db_session
            )
            assert success is True

        # Final version should be 5
        final_invoice = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert final_invoice.review_version == 5
        assert final_invoice.vendor_name == "Vendor Update 4"

    @pytest.mark.asyncio
    async def test_transition_state_with_multiple_valid_from_states(self, db_session, sample_invoice_for_atomic_tests):
        """
        Test transition_state with multiple valid from_states
        """
        invoice = sample_invoice_for_atomic_tests
        invoice.processing_state = InvoiceState.FAILED
        await DatabaseService.save_invoice(invoice, db=db_session)

        # Transition from either PENDING or FAILED to PROCESSING
        success = await DatabaseService.transition_state(
            invoice.id,
            {InvoiceState.PENDING, InvoiceState.FAILED},
            InvoiceState.PROCESSING,
            db=db_session
        )
        assert success is True

        current_invoice = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert current_invoice.processing_state == InvoiceState.PROCESSING

    @pytest.mark.asyncio
    async def test_update_with_review_version_handles_complex_patch(self, db_session, sample_invoice_for_atomic_tests):
        """
        Test that update_with_review_version handles complex patches correctly
        and correctly excludes protected fields (id, created_at, review_version, processing_state)
        """
        invoice = sample_invoice_for_atomic_tests
        await DatabaseService.save_invoice(invoice, db=db_session)

        # Complex patch with multiple fields, including protected fields that should be ignored
        patch = {
            "vendor_name": "New Vendor",
            "total_amount": Decimal("200.50"),
            "status": "validated",
            "processing_state": InvoiceState.VALIDATED,  # Should be ignored
            "id": "should-not-change",  # Should be ignored
            "created_at": datetime(2020, 1, 1),  # Should be ignored
            "review_version": 999,  # Should be ignored
        }

        success = await DatabaseService.update_with_review_version(
            invoice.id,
            patch,
            expected_review_version=0,
            db=db_session
        )
        assert success is True

        current_invoice = await DatabaseService.get_invoice(invoice.id, db=db_session)
        # Verify allowed fields were updated
        assert current_invoice.vendor_name == "New Vendor"
        assert current_invoice.total_amount == Decimal("200.50")
        assert current_invoice.status == "validated"
        
        # Verify protected fields were NOT updated
        assert current_invoice.id == invoice.id  # ID unchanged
        assert current_invoice.processing_state == InvoiceState.PENDING  # Processing state unchanged
        assert current_invoice.review_version == 1  # Review version incremented by method, not set from patch

    @pytest.mark.asyncio
    async def test_atomic_update_no_lost_updates(self, db_session, sample_invoice_for_atomic_tests):
        """
        P0 regression test: Ensure no lost updates due to race conditions
        """
        invoice = sample_invoice_for_atomic_tests
        await DatabaseService.save_invoice(invoice, db=db_session)

        # Initial values
        initial = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert initial.review_version == 0

        # Update 1: Set vendor_name
        success1 = await DatabaseService.update_with_review_version(
            invoice.id,
            {"vendor_name": "First Update"},
            expected_review_version=0,
            db=db_session
        )
        assert success1 is True

        # Attempt Update 2 with stale version (should fail)
        success2 = await DatabaseService.update_with_review_version(
            invoice.id,
            {"vendor_name": "Stale Update"},
            expected_review_version=0,  # Stale!
            db=db_session
        )
        assert success2 is False

        # Correct Update 3 with current version (should succeed)
        success3 = await DatabaseService.update_with_review_version(
            invoice.id,
            {"vendor_name": "Second Update"},
            expected_review_version=1,  # Correct current version
            db=db_session
        )
        assert success3 is True

        # Verify final state
        final = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert final.vendor_name == "Second Update"
        assert final.review_version == 2  # Incremented twice

