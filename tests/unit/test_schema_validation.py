import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"


def _load_validator(schema_file: str) -> Draft202012Validator:
    schema_path = SCHEMA_DIR / schema_file
    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    return Draft202012Validator(schema)


def _assert_valid(validator: Draft202012Validator, payload: dict):
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    assert not errors, "\n".join([f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors])


@pytest.mark.unit
def test_canonical_invoice_schema(sample_invoice):
    validator = _load_validator("invoice.canonical.v1.schema.json")
    payload = sample_invoice.model_dump(mode="json")
    _assert_valid(validator, payload)


@pytest.mark.unit
def test_hitl_view_schema():
    validator = _load_validator("invoice.hitl_view.v1.schema.json")
    payload = {
        "invoice_id": "inv-1",
        "file_name": "sample.pdf",
        "upload_date": "2024-01-01T10:00:00Z",
        "status": "extracted",
        "invoice_subtype": "STANDARD_INVOICE",
        "extraction_confidence": 0.9,
        "low_confidence_triggered": True,
        "low_confidence_fields": ["invoice_number", "total_amount"],
        "fields": {
            "invoice_number": {"value": "INV-1", "confidence": 0.8, "source": "DI"},
            "total_amount": {"value": "123.45", "confidence": 0.6, "source": "LLM"},
        },
        "addresses": {
            "vendor_address": {
                "value": {
                    "street": "123 Main St",
                    "city": "Ottawa",
                    "province": "ON",
                    "postal_code": "K1A0B1",
                    "country": "CA",
                },
                "confidence": 0.7,
                "source": "DI",
            },
            "bill_to_address": None,
            "remit_to_address": None,
        },
        "line_items": [
            {
                "line_number": 1,
                "description": "Item A",
                "quantity": "1",
                "unit_price": "100.00",
                "amount": "100.00",
                "confidence": 0.8,
            }
        ],
        "extensions": None,
        "field_locations": {
            "invoice_number": [
                {"page_index": 0, "polygon": [0, 0, 1, 0, 1, 1, 0, 1], "coordinate_space": "normalized"}
            ]
        },
    }
    _assert_valid(validator, payload)

