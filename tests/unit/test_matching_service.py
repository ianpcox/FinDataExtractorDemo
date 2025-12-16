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

