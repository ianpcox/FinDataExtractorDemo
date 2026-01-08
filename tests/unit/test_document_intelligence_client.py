"""Unit tests for DocumentIntelligenceClient field extraction helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.extraction.document_intelligence_client import DocumentIntelligenceClient


class _Field:
    def __init__(self, value=None, confidence=1.0):
        self.value = value
        self.confidence = confidence


class _Item:
    def __init__(self, value, confidence=1.0):
        self.value = value
        self.confidence = confidence


@pytest.mark.unit
class TestDocumentIntelligenceClient:
    @patch("src.extraction.document_intelligence_client.DocumentAnalysisClient")
    def test_extract_invoice_fields_and_items(self, mock_client_cls):
        mock_client_cls.return_value = MagicMock()

        client = DocumentIntelligenceClient(endpoint="https://example.test", api_key="fake")

        items_field = _Field(
            value=[
                _Item(
                    value={
                        "Description": _Field("Service A", 0.91),
                        "Quantity": _Field(2, 0.88),
                        "UnitPrice": _Field(10.0, 0.77),
                        "Amount": _Field(20.0, 0.95),
                    },
                    confidence=0.85,
                )
            ],
            confidence=0.8,
        )

        fields = {
            "InvoiceId": _Field("INV-001", 0.99),
            "VendorName": _Field("Acme", 0.9),
            "VendorAddress": _Field(
                {
                    "streetAddress": "1 Main St",
                    "city": "Ottawa",
                    "state": "ON",
                    "postalCode": "K1A0B1",
                    "countryRegion": "CA",
                },
                0.87,
            ),
            "Items": items_field,
        }

        invoice_doc = SimpleNamespace(fields=fields, confidence=0.77)
        result = SimpleNamespace(documents=[invoice_doc])

        data = client._extract_invoice_fields(result)

        assert data["confidence"] == 0.77
        assert data["invoice_id"] == "INV-001"
        assert data["vendor_name"] == "Acme"
        assert data["vendor_address"]["city"] == "Ottawa"
        assert data["items"][0]["description"] == "Service A"
        assert data["items"][0]["quantity"] == 2
        assert data["items"][0]["unit_price"] == 10.0
        assert data["items"][0]["amount"] == 20.0
        assert data["items"][0]["confidence"] == 0.85
        assert data["field_confidence"]["InvoiceId"] == 0.99

    @patch("src.extraction.document_intelligence_client.DocumentAnalysisClient")
    def test_extract_invoice_fields_no_documents(self, mock_client_cls):
        mock_client_cls.return_value = MagicMock()
        client = DocumentIntelligenceClient(endpoint="https://example.test", api_key="fake")

        result = SimpleNamespace(documents=[])
        data = client._extract_invoice_fields(result)

        assert data["confidence"] == 0.0
        assert "error" in data

