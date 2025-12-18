"""
P0/P1 Integration Test: Concurrent Extraction Safety

This test proves that concurrent extraction requests are safe and deterministic:
1. Exactly ONE request successfully claims/processes the invoice
2. All other concurrent requests return 409 conflict
3. Final DB state is EXTRACTED (never stuck in PROCESSING)
"""

import pytest
import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from src.models.invoice import Invoice, InvoiceState, LineItem
from src.models.db_models import Invoice as InvoiceDB
from src.services.db_service import DatabaseService


class StubExtractionService:
    """
    Stub extraction service for deterministic concurrent testing.
    
    This stub:
    - Sleeps briefly to widen the race window
    - Calls actual claim logic (DatabaseService.claim_for_extraction)
    - Returns conflict if claim fails
    - Returns extracted invoice if claim succeeds
    """
    
    async def extract_invoice(self, invoice_id: str, file_identifier: str, file_name: str, upload_date: datetime, db=None):
        """Stub extraction that exercises claim atomicity"""
        # Sleep to create race window (concurrent requests overlap)
        await asyncio.sleep(0.1)
        
        # Attempt to claim the invoice (uses atomic UPDATE)
        claimed = await DatabaseService.claim_for_extraction(invoice_id, db=db)
        
        if not claimed:
            # Another request already claimed it
            return {
                "status": "conflict",
                "invoice_id": invoice_id,
                "errors": ["Invoice is already processing"],
            }
        
        # Successfully claimed - simulate extraction
        await asyncio.sleep(0.05)  # Simulate processing time
        
        # Create minimal extracted invoice
        invoice = Invoice(
            id=invoice_id,
            file_path=file_identifier,
            file_name=file_name,
            upload_date=upload_date,
            invoice_number="INV-STUB-001",
            vendor_name="Stub Vendor",
            total_amount=Decimal("100.00"),
            processing_state=InvoiceState.EXTRACTED,
            status="extracted",
            extraction_confidence=0.95,
            line_items=[
                LineItem(
                    line_number=1,
                    description="Stub Item",
                    quantity=Decimal("1"),
                    unit_price=Decimal("100.00"),
                    amount=Decimal("100.00"),
                    confidence=0.9,
                )
            ],
        )
        
        # Mark as extracted (uses atomic UPDATE)
        success = await DatabaseService.set_extraction_result(
            invoice_id=invoice_id,
            invoice_dict=invoice.model_dump(mode="json"),
            confidence=0.95,
            field_confidence={"total_amount": 0.95},
            low_confidence_fields=[],
            expected_processing_state="PROCESSING",
            db=db,
        )
        
        if not success:
            return {
                "status": "conflict",
                "invoice_id": invoice_id,
                "errors": ["State transition failed"],
            }
        
        return {
            "status": "extracted",
            "invoice_id": invoice_id,
            "invoice": invoice,
            "confidence": 0.95,
            "field_confidence": {"total_amount": 0.95},
            "low_confidence_fields": [],
            "low_confidence_triggered": False,
            "extraction_timestamp": datetime.utcnow(),
        }


@pytest.mark.integration
@pytest.mark.asyncio
class TestConcurrentExtraction:
    """
    P0 Concurrency Test: Prove extraction claim atomicity
    """
    
    async def test_concurrent_extraction_claims_once(self, async_client, db_session, db_engine):
        """
        Test that concurrent extraction requests are handled safely:
        - Exactly one request succeeds
        - Others return 409 conflict
        - Final state is EXTRACTED (not stuck in PROCESSING)
        """
        invoice_id = "INV-CONCURRENT-TEST-001"
        file_identifier = "test/path/invoice.pdf"
        file_name = "invoice.pdf"
        
        # Seed invoice in PENDING state
        from src.models.db_utils import pydantic_to_db_invoice
        pending_invoice = Invoice(
            id=invoice_id,
            file_path=file_identifier,
            file_name=file_name,
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            status="pending",
            review_version=0,
        )
        db_invoice = pydantic_to_db_invoice(pending_invoice)
        db_session.add(db_invoice)
        await db_session.commit()
        
        # Override extraction service dependency with stub
        from api.main import app
        from api.routes.extraction import get_extraction_service
        
        def get_stub_extraction_service():
            return StubExtractionService()
        
        app.dependency_overrides[get_extraction_service] = get_stub_extraction_service
        
        # CRITICAL: Override the AsyncSessionLocal that DatabaseService uses
        # so the stub's DB calls use the test DB
        from src.models import database as db_module
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession as SA_AsyncSession
        
        TestingSessionLocal = async_sessionmaker(
            db_engine,
            class_=SA_AsyncSession,
            expire_on_commit=False
        )
        
        original_session_local = db_module.AsyncSessionLocal
        db_module.AsyncSessionLocal = TestingSessionLocal
        
        try:
            # Fire N concurrent extraction requests
            N = 5
            tasks = [
                async_client.post(
                    f"/api/extraction/extract/{invoice_id}",
                    params={
                        "file_identifier": file_identifier,
                        "file_name": file_name,
                    }
                )
                for _ in range(N)
            ]
            
            # Execute concurrently
            responses = await asyncio.gather(*tasks)
            
            # Analyze results
            success_responses = [r for r in responses if r.status_code == 200]
            conflict_responses = [r for r in responses if r.status_code == 409]
            
            # ✅ Assertion 1: Exactly one success
            assert len(success_responses) == 1, (
                f"Expected exactly 1 success, got {len(success_responses)}. "
                f"Responses: {[(r.status_code, r.text[:100]) for r in responses]}"
            )
            
            # ✅ Assertion 2: All others are conflict
            assert len(conflict_responses) == N - 1, (
                f"Expected {N-1} conflicts, got {len(conflict_responses)}. "
                f"Responses: {[(r.status_code, r.text[:100]) for r in responses]}"
            )
            
            # Verify conflict messages
            for resp in conflict_responses:
                data = resp.json()
                assert "detail" in data or "message" in data
                message = data.get("detail", {}).get("message", "") or data.get("message", "")
                assert "already processing" in message.lower(), f"Unexpected conflict message: {message}"
            
            # ✅ Assertion 3: Final DB state is EXTRACTED
            await db_session.expire_all()
            result = await db_session.execute(
                f"SELECT * FROM invoices WHERE id = '{invoice_id}'"
            )
            final_invoice = result.fetchone()
            
            assert final_invoice is not None, "Invoice not found in DB"
            # Get processing_state column (adjust index if needed)
            # Assuming processing_state is in the row
            final_state = final_invoice.processing_state if hasattr(final_invoice, 'processing_state') else None
            
            # Alternative: use ORM
            final_invoice_orm = await db_session.get(InvoiceDB, invoice_id)
            assert final_invoice_orm is not None, "Invoice not found in DB"
            assert final_invoice_orm.processing_state == "EXTRACTED", (
                f"Expected final state EXTRACTED, got {final_invoice_orm.processing_state}"
            )
            assert final_invoice_orm.processing_state != "PROCESSING", (
                "Invoice stuck in PROCESSING state"
            )
            
            # Verify extracted data was persisted
            assert final_invoice_orm.invoice_number == "INV-STUB-001"
            assert final_invoice_orm.vendor_name == "Stub Vendor"
            
        finally:
            # Cleanup: clear dependency override and restore original AsyncSessionLocal
            app.dependency_overrides.pop(get_extraction_service, None)
            db_module.AsyncSessionLocal = original_session_local
    
    async def test_concurrent_extraction_repeatability(self, async_client, db_session, db_engine):
        """
        Test that concurrent extraction is repeatable (not flaky).
        Run the same test multiple times to ensure stability.
        """
        for run_number in range(3):
            invoice_id = f"INV-CONCURRENT-REPEAT-{run_number}"
            file_identifier = f"test/path/invoice_{run_number}.pdf"
            file_name = f"invoice_{run_number}.pdf"
            
            # Seed invoice
            from src.models.db_utils import pydantic_to_db_invoice
            pending_invoice = Invoice(
                id=invoice_id,
                file_path=file_identifier,
                file_name=file_name,
                upload_date=datetime.utcnow(),
                processing_state=InvoiceState.PENDING,
                status="pending",
                review_version=0,
            )
            db_invoice = pydantic_to_db_invoice(pending_invoice)
            db_session.add(db_invoice)
            await db_session.commit()
            
            # Override extraction service
            from api.main import app
            from api.routes.extraction import get_extraction_service
            
            def get_stub_extraction_service():
                return StubExtractionService()
            
            app.dependency_overrides[get_extraction_service] = get_stub_extraction_service
            
            # Override AsyncSessionLocal for DatabaseService
            from src.models import database as db_module
            from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession as SA_AsyncSession
            
            TestingSessionLocal = async_sessionmaker(
                db_engine,
                class_=SA_AsyncSession,
                expire_on_commit=False
            )
            
            original_session_local = db_module.AsyncSessionLocal
            db_module.AsyncSessionLocal = TestingSessionLocal
            
            try:
                # Fire concurrent requests
                N = 3
                responses = await asyncio.gather(*[
                    async_client.post(
                        f"/api/extraction/extract/{invoice_id}",
                        params={"file_identifier": file_identifier, "file_name": file_name}
                    )
                    for _ in range(N)
                ])
                
                # Verify results
                success = [r for r in responses if r.status_code == 200]
                conflicts = [r for r in responses if r.status_code == 409]
                
                assert len(success) == 1, f"Run {run_number}: Expected 1 success, got {len(success)}"
                assert len(conflicts) == N - 1, f"Run {run_number}: Expected {N-1} conflicts, got {len(conflicts)}"
                
                # Verify final state
                final_invoice = await db_session.get(InvoiceDB, invoice_id)
                assert final_invoice.processing_state == "EXTRACTED", (
                    f"Run {run_number}: Expected EXTRACTED, got {final_invoice.processing_state}"
                )
                
            finally:
                app.dependency_overrides.pop(get_extraction_service, None)
                db_module.AsyncSessionLocal = original_session_local

