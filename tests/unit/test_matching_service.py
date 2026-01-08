"""Unit tests for MatchingService."""

import pytest
from unittest.mock import AsyncMock, patch

from src.matching.matching_service import MatchingService, MatchStrategy


@pytest.mark.unit
class TestMatchingService:
    @pytest.mark.asyncio
    async def test_match_invoice_to_po_with_po_data(self, sample_invoice, sample_po_data):
        service = MatchingService()
        with patch("src.matching.matching_service.DatabaseService.get_invoice", new=AsyncMock(return_value=sample_invoice)):
            results = await service.match_invoice_to_po(invoice_id=sample_invoice.id, po_data=sample_po_data)

        assert len(results) == 1
        result = results[0]
        assert result.confidence >= service.criteria.min_confidence
        assert result.match_strategy in {MatchStrategy.EXACT, MatchStrategy.HYBRID}
        assert result.match_details["po_number_match"] is True

    def test_match_invoice_po_data_exact_match(self, sample_invoice, sample_po_data):
        service = MatchingService()
        result = service._match_invoice_po_data(sample_invoice, sample_po_data)

        assert result is not None
        assert result.match_strategy == MatchStrategy.EXACT
        assert result.confidence > 0.7
        assert result.match_details["vendor_match"] is True

    def test_match_invoice_po_by_number(self, sample_invoice):
        service = MatchingService()
        result = service._match_invoice_po_by_number(sample_invoice, sample_invoice.po_number)
        assert result is not None
        assert result.match_strategy == MatchStrategy.EXACT
        assert result.confidence == 0.85

        # Mismatch should return None
        assert service._match_invoice_po_by_number(sample_invoice, "PO-OTHER") is None
"""Unit tests for MatchingService"""

import pytest
from datetime import date
from decimal import Decimal

from src.matching.matching_service import MatchingService, MatchStrategy
from src.models.invoice import Invoice


@pytest.mark.unit
class TestMatchingService:
    """Test MatchingService"""
    
    def test_match_invoice_po_by_number(self, sample_invoice):
        """Test matching invoice to PO by PO number"""
        service = MatchingService()
        
        po_data = {
            "id": "po-uuid-123",
            "po_number": "PO-12345",
            "po_date": "2024-01-05",
            "vendor_name": "Acme Corp",
            "vendor_code": "ACME001",
            "total_amount": 1500.00
        }
        
        matches = service._match_invoice_po_data(sample_invoice, po_data)
        
        assert matches is not None
        assert matches.confidence >= 0.70
        assert matches.matched_document_number == "PO-12345"
        assert matches.match_strategy in [MatchStrategy.EXACT, MatchStrategy.HYBRID]
    
    def test_match_invoice_po_exact_match(self, sample_invoice):
        """Test exact PO number match"""
        service = MatchingService()
        
        po_data = {
            "id": "po-uuid-123",
            "po_number": "PO-12345",  # Exact match
            "po_date": "2024-01-05",
            "vendor_name": "Acme Corp",  # Exact match
            "vendor_code": "ACME001",
            "total_amount": 1500.00  # Exact match
        }
        
        matches = service._match_invoice_po_data(sample_invoice, po_data)
        
        assert matches is not None
        assert matches.confidence >= 0.85  # High confidence for exact match
        assert matches.match_strategy == MatchStrategy.EXACT
    
    def test_match_invoice_po_fuzzy_match(self, sample_invoice):
        """Test fuzzy matching when PO number doesn't match"""
        service = MatchingService()
        
        po_data = {
            "id": "po-uuid-123",
            "po_number": "PO-99999",  # Different PO number
            "po_date": "2024-01-05",
            "vendor_name": "Acme Corp",  # Vendor matches
            "vendor_code": "ACME001",
            "total_amount": 1500.00  # Amount matches
        }
        
        matches = service._match_invoice_po_data(sample_invoice, po_data)
        
        # Should still match on vendor and amount
        assert matches is not None
        assert matches.match_strategy == MatchStrategy.FUZZY
    
    def test_match_invoice_po_amount_tolerance(self, sample_invoice):
        """Test amount matching with tolerance"""
        service = MatchingService()
        
        # Amount within 5% tolerance
        po_data = {
            "id": "po-uuid-123",
            "po_number": "PO-12345",
            "po_date": "2024-01-05",
            "vendor_name": "Acme Corp",
            "total_amount": 1520.00  # Within 5% of 1500.00
        }
        
        matches = service._match_invoice_po_data(sample_invoice, po_data)
        
        assert matches is not None
        assert matches.confidence >= 0.70
    
    def test_match_invoice_po_date_validation(self, sample_invoice):
        """Test date matching (invoice date should be after PO date)"""
        service = MatchingService()
        
        po_data = {
            "id": "po-uuid-123",
            "po_number": "PO-12345",
            "po_date": "2024-01-05",  # Before invoice date (2024-01-10)
            "vendor_name": "Acme Corp",
            "total_amount": 1500.00
        }
        
        matches = service._match_invoice_po_data(sample_invoice, po_data)
        
        assert matches is not None
        # Date match should contribute to confidence
        assert "date_diff_days" in matches.match_details

