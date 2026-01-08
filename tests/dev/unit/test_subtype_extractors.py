"""Unit tests for subtype extractors"""

import pytest
from datetime import date
from decimal import Decimal

from src.extraction.subtype_extractors import ShiftServiceExtractor, PerDiemTravelExtractor
from src.models.invoice_subtypes import ShiftServiceExtension, PerDiemTravelExtension


@pytest.mark.unit
class TestShiftServiceExtractor:
    """Test ShiftServiceExtractor"""
    
    def test_extract_shift_service_data(self):
        """Test extraction of shift service data"""
        extractor = ShiftServiceExtractor()
        
        di_data = {
            "content": "Service Location: YVR\nShift Rate: $150.00\nTotal Shifts: 20"
        }
        
        result = extractor.extract(di_data, invoice_text=di_data["content"])
        
        assert result is not None
        assert isinstance(result, ShiftServiceExtension)
        assert result.service_location == "YVR"
        assert result.shift_rate == Decimal("150.00")
        assert result.total_shifts_billed == 20
    
    def test_extract_billing_period(self):
        """Test extraction of billing period"""
        extractor = ShiftServiceExtractor()
        
        text = "Billing Period: 2024-01-01 to 2024-01-31"
        period = extractor._extract_billing_period(text)
        
        assert period is not None
        assert "start" in period
        assert "end" in period
        assert period["start"] == date(2024, 1, 1)
        assert period["end"] == date(2024, 1, 31)


@pytest.mark.unit
class TestPerDiemTravelExtractor:
    """Test PerDiemTravelExtractor"""
    
    def test_extract_per_diem_travel_data(self):
        """Test extraction of per-diem travel data"""
        extractor = PerDiemTravelExtractor()
        
        di_data = {"content": "Travel invoice"}
        line_items = [
            {
                "description": "Traveller: John Doe\nCourse: TRAIN-001\nTravel Days: 5\nDaily Rate: $100.00",
                "amount": 500.00
            }
        ]
        
        results = extractor.extract(di_data, line_items, invoice_text=di_data["content"])
        
        assert len(results) > 0
        assert isinstance(results[0], PerDiemTravelExtension)
        assert results[0].daily_rate == Decimal("100.00")
        assert results[0].travel_days == 5

