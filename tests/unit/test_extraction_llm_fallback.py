import json
from datetime import datetime
from decimal import Decimal
import types
import pytest

from src.extraction.extraction_service import ExtractionService
from src.extraction.field_extractor import FieldExtractor
from src.config import settings


class FakeChoices:
    def __init__(self, content: str):
        self.message = types.SimpleNamespace(content=content)


class FakeCompletions:
    def __init__(self, content: str):
        self._content = content

    def create(self, **kwargs):
        return types.SimpleNamespace(choices=[FakeChoices(self._content)])


class FakeChat:
    def __init__(self, content: str):
        self.completions = FakeCompletions(content)


class FakeAzureOpenAI:
    def __init__(self, **kwargs):
        pass

    @property
    def chat(self):
        return FakeChat(json.dumps({"vendor_name": "LLM Vendor", "invoice_total": 234.56}))


class FakeFileHandler:
    def download_file(self, file_identifier):
        return b"%PDF-1.4"

    def get_file_path(self, file_identifier):
        return "storage/raw/test.pdf"


class FakeDIClient:
    def analyze_invoice(self, file_content: bytes):
        return {
            "invoice_id": "INV-1",
            "invoice_date": "2024-01-01",
            "due_date": "2024-02-01",
            "invoice_total": "100.00",
            "vendor_name": "Old Vendor",
            "field_confidence": {
                "InvoiceTotal": 0.5,
                "VendorName": 0.4,
            },
        }


@pytest.mark.asyncio
async def test_llm_fallback_applies_and_persists(monkeypatch):
    # Enable fallback
    monkeypatch.setattr(settings, "USE_LLM_FALLBACK", True, raising=False)
    monkeypatch.setattr(settings, "AOAI_ENDPOINT", "https://aoai.example.com", raising=False)
    monkeypatch.setattr(settings, "AOAI_API_KEY", "k", raising=False)
    monkeypatch.setattr(settings, "AOAI_DEPLOYMENT_NAME", "dep", raising=False)
    monkeypatch.setattr(settings, "AOAI_API_VERSION", "2024-12-01-preview", raising=False)

    # Fake Azure client
    monkeypatch.setattr("src.extraction.extraction_service.AzureOpenAI", FakeAzureOpenAI)

    # Capture persisted invoice
    captured = {}

    async def fake_save(inv, db=None):
        captured["invoice"] = inv
        return inv

    monkeypatch.setattr("src.extraction.extraction_service.DatabaseService.save_invoice", fake_save)

    service = ExtractionService(
        doc_intelligence_client=FakeDIClient(),
        file_handler=FakeFileHandler(),
        field_extractor=FieldExtractor(),
    )

    result = await service.extract_invoice(
        invoice_id="inv-1",
        file_identifier="storage/raw/test.pdf",
        file_name="test.pdf",
        upload_date=datetime.utcnow(),
    )

    inv = captured["invoice"]
    assert inv.vendor_name == "LLM Vendor"
    assert inv.total_amount == Decimal("234.56")
    assert inv.field_confidence.get("total_amount") == 0.9
    assert result["status"] == "extracted"

