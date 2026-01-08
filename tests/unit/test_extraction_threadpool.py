import pytest
from datetime import datetime
from decimal import Decimal

from src.extraction.extraction_service import ExtractionService
from src.models.invoice import Invoice
from src.services import db_service


class FakeFileHandler:
    def __init__(self):
        self.called = False

    def download_file(self, file_identifier):
        self.called = True
        return b"pdf-bytes"

    def get_file_path(self, file_identifier):
        return f"/tmp/{file_identifier}"


class FakeDocClient:
    def __init__(self):
        self.called = False

    def analyze_invoice(self, file_content: bytes):
        self.called = True
        return {
            "confidence": 0.5,
            "invoice_id": "INV-1",
            "invoice_date": "2024-01-01",
            "due_date": "2024-02-01",
            "vendor_name": "Vendor",
            "invoice_total": "100.00",
            "items": [],
            "field_confidence": {"invoice_number": 0.5},
        }


class FakeFieldExtractor:
    def extract_invoice(
        self,
        doc_intelligence_data,
        file_path,
        file_name,
        upload_date,
        invoice_text=None,
    ):
        return Invoice(
            id="inv-1",
            file_path=file_path,
            file_name=file_name,
            upload_date=upload_date,
            status="extracted",
            invoice_number="INV-1",
            invoice_date=datetime(2024, 1, 1),
            due_date=datetime(2024, 2, 1),
            vendor_name="Vendor",
            total_amount=Decimal("100.00"),
            field_confidence={"invoice_number": 0.5},
        )


@pytest.mark.asyncio
async def test_extract_invoice_offloads_blocking(monkeypatch):
    calls = []

    async def fake_run_in_threadpool(fn, *args, **kwargs):
        calls.append(fn.__name__)
        if fn.__name__ == "download_file":
            return fn(*args, **kwargs)
        if fn.__name__ == "analyze_invoice":
            return fn(*args, **kwargs)
        if fn.__name__ == "_run_low_confidence_fallback":
            return None
        return fn(*args, **kwargs)

    monkeypatch.setattr(
        "src.extraction.extraction_service.run_in_threadpool",
        fake_run_in_threadpool,
    )

    # Avoid real DB writes
    async def fake_save_invoice(invoice, db=None):
        return None

    monkeypatch.setattr(db_service.DatabaseService, "save_invoice", fake_save_invoice)

    svc = ExtractionService(
        doc_intelligence_client=FakeDocClient(),
        file_handler=FakeFileHandler(),
        field_extractor=FakeFieldExtractor(),
    )

    result = await svc.extract_invoice(
        invoice_id="inv-1",
        file_identifier="f.pdf",
        file_name="f.pdf",
        upload_date=datetime.utcnow(),
        db=None,
    )

    assert result["status"] == "extracted"
    assert "download_file" in calls
    assert "analyze_invoice" in calls
    assert "_run_low_confidence_fallback" in calls

