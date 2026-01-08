"""Unit tests for ERP staging service"""

import pytest
from datetime import datetime, date
from decimal import Decimal

from src.erp.staging_service import (
    ERPPayloadGenerator,
    ERPStagingService,
    ERPPayloadFormat
)
from src.models.invoice import Invoice, LineItem


@pytest.mark.unit
class TestERPPayloadGenerator:
    """Test ERPPayloadGenerator"""
    
    def test_generate_payload_json(self, sample_invoice):
        """Test JSON payload generation"""
        generator = ERPPayloadGenerator(erp_format=ERPPayloadFormat.JSON)
        
        result = generator.generate_payload(sample_invoice)
        
        assert result["format"] == "json"
        assert "payload" in result
        assert result["invoice_id"] == sample_invoice.id
        assert result["total_amount"] == sample_invoice.total_amount
        
        # Parse JSON to verify structure
        import json
        payload_data = json.loads(result["payload"])
        assert payload_data["voucher_type"] == "AP"
        assert payload_data["vendor_name"] == sample_invoice.vendor_name
        assert len(payload_data["line_items"]) == 2
    
    def test_generate_payload_xml(self, sample_invoice):
        """Test XML payload generation"""
        generator = ERPPayloadGenerator(erp_format=ERPPayloadFormat.XML)
        
        result = generator.generate_payload(sample_invoice)
        
        assert result["format"] == "xml"
        assert "payload" in result
        assert "<?xml" in result["payload"] or "<Voucher" in result["payload"]
    
    def test_generate_payload_csv(self, sample_invoice):
        """Test CSV payload generation"""
        generator = ERPPayloadGenerator(erp_format=ERPPayloadFormat.CSV)
        
        result = generator.generate_payload(sample_invoice)
        
        assert result["format"] == "csv"
        assert "payload" in result
        assert "Voucher Type" in result["payload"]
        assert "Invoice Number" in result["payload"]
    
    def test_generate_payload_dynamics_gp(self, sample_invoice):
        """Test Dynamics GP payload generation"""
        generator = ERPPayloadGenerator(erp_format=ERPPayloadFormat.DYNAMICS_GP)
        
        result = generator.generate_payload(sample_invoice)
        
        assert result["format"] == "dynamics_gp"
        assert "payload" in result
        # Dynamics GP uses XML format
        assert "<Voucher" in result["payload"] or "<?xml" in result["payload"]
    
    def test_payload_includes_approvals(self, sample_invoice):
        """Test that payload includes approval information"""
        sample_invoice.bv_approver = "john.doe"
        sample_invoice.bv_approval_date = datetime(2024, 1, 16, 10, 0, 0)
        sample_invoice.fa_approver = "jane.smith"
        sample_invoice.fa_approval_date = datetime(2024, 1, 17, 14, 0, 0)
        
        generator = ERPPayloadGenerator(erp_format=ERPPayloadFormat.JSON)
        result = generator.generate_payload(sample_invoice)
        
        import json
        payload_data = json.loads(result["payload"])
        assert "approved_by" in payload_data
        assert payload_data["approved_by"]["business_verifier"] == "john.doe"
        assert payload_data["approved_by"]["financial_authorizer"] == "jane.smith"
    
    def test_payload_includes_tax_breakdown(self, sample_invoice):
        """Test that payload includes tax breakdown"""
        generator = ERPPayloadGenerator(erp_format=ERPPayloadFormat.JSON)
        result = generator.generate_payload(sample_invoice)
        
        import json
        payload_data = json.loads(result["payload"])
        assert "tax_breakdown" in payload_data
        assert len(payload_data["tax_breakdown"]) > 0
        assert "tax_type" in payload_data["tax_breakdown"][0]
        assert "recoverable_amount" in payload_data["tax_breakdown"][0]

