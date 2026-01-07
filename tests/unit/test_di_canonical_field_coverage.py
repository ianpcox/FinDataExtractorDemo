"""
Comprehensive test coverage for canonical fields extractable by Document Intelligence OCR.

This test suite ensures 75% coverage of canonical fields that can be extracted by DI OCR.
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from types import SimpleNamespace

from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.models.invoice import Invoice, Address


class _Field:
    """Mock Document Intelligence field"""
    def __init__(self, value=None, confidence=1.0):
        self.value = value
        self.confidence = confidence


class _Item:
    """Mock Document Intelligence item"""
    def __init__(self, value, confidence=1.0):
        self.value = value
        self.confidence = confidence


@pytest.mark.unit
class TestDICanonicalFieldCoverage:
    """Test coverage for canonical fields extractable by DI OCR"""
    
    @pytest.fixture
    def mock_di_client(self):
        """Create a mock DI client"""
        from unittest.mock import MagicMock, patch
        with patch("src.extraction.document_intelligence_client.DocumentAnalysisClient"):
            client = DocumentIntelligenceClient(endpoint="https://example.test", api_key="fake")
            return client
    
    @pytest.fixture
    def field_extractor(self):
        """Create a field extractor instance"""
        return FieldExtractor()
    
    def create_di_result(self, fields_dict, items=None):
        """Helper to create a mock DI result"""
        fields = {}
        for key, value in fields_dict.items():
            if isinstance(value, dict) and "value" in value:
                fields[key] = _Field(value["value"], value.get("confidence", 1.0))
            else:
                fields[key] = _Field(value, 1.0)
        
        if items:
            items_field = _Field(
                value=[_Item(item, item.get("confidence", 1.0)) for item in items],
                confidence=0.9
            )
            fields["Items"] = items_field
        
        invoice_doc = SimpleNamespace(fields=fields, confidence=0.95)
        return SimpleNamespace(documents=[invoice_doc])
    
    # ========== HEADER FIELDS (5 fields) ==========
    
    def test_invoice_number_extraction(self, mock_di_client, field_extractor):
        """Test invoice_number extraction"""
        result = self.create_di_result({
            "InvoiceId": {"value": "INV-2024-001", "confidence": 0.98}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.invoice_number == "INV-2024-001"
        assert invoice.field_confidence.get("invoice_number", 0) >= 0.9
    
    def test_invoice_date_extraction(self, mock_di_client, field_extractor):
        """Test invoice_date extraction"""
        result = self.create_di_result({
            "InvoiceDate": {"value": "2024-01-15", "confidence": 0.96}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.invoice_date == date(2024, 1, 15)
    
    def test_due_date_extraction(self, mock_di_client, field_extractor):
        """Test due_date extraction"""
        result = self.create_di_result({
            "DueDate": {"value": "2024-02-15", "confidence": 0.94}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.due_date == date(2024, 2, 15)
    
    def test_invoice_type_extraction(self, mock_di_client, field_extractor):
        """Test invoice_type extraction"""
        result = self.create_di_result({
            "InvoiceType": {"value": "Original", "confidence": 0.92}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.invoice_type == "Original"
    
    def test_reference_number_extraction(self, mock_di_client, field_extractor):
        """Test reference_number extraction"""
        result = self.create_di_result({
            "ReferenceNumber": {"value": "REF-12345", "confidence": 0.91}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.reference_number == "REF-12345"
    
    # ========== VENDOR FIELDS (7 fields) ==========
    
    def test_vendor_name_extraction(self, mock_di_client, field_extractor):
        """Test vendor_name extraction"""
        result = self.create_di_result({
            "VendorName": {"value": "Acme Corporation", "confidence": 0.95}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.vendor_name == "Acme Corporation"
    
    def test_vendor_id_extraction(self, mock_di_client, field_extractor):
        """Test vendor_id extraction"""
        result = self.create_di_result({
            "VendorId": {"value": "VEND-001", "confidence": 0.93}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.vendor_id == "VEND-001"
    
    def test_vendor_phone_extraction(self, mock_di_client, field_extractor):
        """Test vendor_phone extraction"""
        result = self.create_di_result({
            "VendorPhoneNumber": {"value": "(555) 123-4567", "confidence": 0.90}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.vendor_phone == "(555) 123-4567"
    
    def test_vendor_fax_extraction(self, mock_di_client, field_extractor):
        """Test vendor_fax extraction"""
        result = self.create_di_result({
            "VendorFax": {"value": "(555) 123-4568", "confidence": 0.89}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.vendor_fax == "(555) 123-4568"
    
    def test_vendor_email_extraction(self, mock_di_client, field_extractor):
        """Test vendor_email extraction"""
        result = self.create_di_result({
            "VendorEmail": {"value": "contact@acme.com", "confidence": 0.92}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.vendor_email == "contact@acme.com"
    
    def test_vendor_website_extraction(self, mock_di_client, field_extractor):
        """Test vendor_website extraction"""
        result = self.create_di_result({
            "VendorWebsite": {"value": "https://acme.com", "confidence": 0.88}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.vendor_website == "https://acme.com"
    
    def test_vendor_address_extraction(self, mock_di_client, field_extractor):
        """Test vendor_address extraction"""
        result = self.create_di_result({
            "VendorAddress": {
                "value": {
                    "streetAddress": "123 Main St",
                    "city": "Vancouver",
                    "state": "BC",
                    "postalCode": "V6B 1A1",
                    "countryRegion": "CA"
                },
                "confidence": 0.87
            }
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.vendor_address is not None
        assert invoice.vendor_address.street == "123 Main St"
        assert invoice.vendor_address.city == "Vancouver"
        assert invoice.vendor_address.province == "BC"
        assert invoice.vendor_address.postal_code == "V6B 1A1"
        assert invoice.vendor_address.country == "CA"
    
    # ========== VENDOR TAX ID FIELDS (4 fields) ==========
    
    def test_business_number_extraction(self, mock_di_client, field_extractor):
        """Test business_number extraction"""
        result = self.create_di_result({
            "BusinessNumber": {"value": "123456789RC0001", "confidence": 0.94}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.business_number == "123456789RC0001"
    
    def test_gst_number_extraction(self, mock_di_client, field_extractor):
        """Test gst_number extraction"""
        result = self.create_di_result({
            "GSTNumber": {"value": "123456789RT0001", "confidence": 0.93}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.gst_number == "123456789RT0001"
    
    def test_qst_number_extraction(self, mock_di_client, field_extractor):
        """Test qst_number extraction"""
        result = self.create_di_result({
            "QSTNumber": {"value": "123456789TQ0001", "confidence": 0.92}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.qst_number == "123456789TQ0001"
    
    def test_pst_number_extraction(self, mock_di_client, field_extractor):
        """Test pst_number extraction"""
        result = self.create_di_result({
            "PSTNumber": {"value": "PST-123456", "confidence": 0.91}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.pst_number == "PST-123456"
    
    # ========== CUSTOMER FIELDS (6 fields) ==========
    
    def test_customer_name_extraction(self, mock_di_client, field_extractor):
        """Test customer_name extraction"""
        result = self.create_di_result({
            "CustomerName": {"value": "CATSA", "confidence": 0.96}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.customer_name == "CATSA"
    
    def test_customer_id_extraction(self, mock_di_client, field_extractor):
        """Test customer_id extraction"""
        result = self.create_di_result({
            "CustomerId": {"value": "CUST-001", "confidence": 0.94}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.customer_id == "CUST-001"
    
    def test_customer_phone_extraction(self, mock_di_client, field_extractor):
        """Test customer_phone extraction"""
        result = self.create_di_result({
            "CustomerPhone": {"value": "(613) 949-0000", "confidence": 0.90}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.customer_phone == "(613) 949-0000"
    
    def test_customer_email_extraction(self, mock_di_client, field_extractor):
        """Test customer_email extraction"""
        result = self.create_di_result({
            "CustomerEmail": {"value": "info@catsa-acsta.gc.ca", "confidence": 0.92}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.customer_email == "info@catsa-acsta.gc.ca"
    
    def test_customer_fax_extraction(self, mock_di_client, field_extractor):
        """Test customer_fax extraction"""
        result = self.create_di_result({
            "CustomerFax": {"value": "(613) 949-0001", "confidence": 0.89}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.customer_fax == "(613) 949-0001"
    
    def test_bill_to_address_extraction(self, mock_di_client, field_extractor):
        """Test bill_to_address extraction"""
        result = self.create_di_result({
            "BillToAddress": {
                "value": {
                    "streetAddress": "99 Bank Street, 13th Floor",
                    "city": "Ottawa",
                    "state": "ON",
                    "postalCode": "K1P 6B9",
                    "countryRegion": "CA"
                },
                "confidence": 0.88
            }
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.bill_to_address is not None
        assert invoice.bill_to_address.street == "99 Bank Street, 13th Floor"
        assert invoice.bill_to_address.city == "Ottawa"
        assert invoice.bill_to_address.province == "ON"
        assert invoice.bill_to_address.postal_code == "K1P 6B9"
    
    # ========== REMIT-TO FIELDS (2 fields) ==========
    
    def test_remit_to_address_extraction(self, mock_di_client, field_extractor):
        """Test remit_to_address extraction"""
        result = self.create_di_result({
            "RemitToAddress": {
                "value": {
                    "streetAddress": "456 Remit St",
                    "city": "Toronto",
                    "state": "ON",
                    "postalCode": "M5H 2N2",
                    "countryRegion": "CA"
                },
                "confidence": 0.87
            }
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.remit_to_address is not None
        assert invoice.remit_to_address.street == "456 Remit St"
        assert invoice.remit_to_address.city == "Toronto"
    
    def test_remit_to_name_extraction(self, mock_di_client, field_extractor):
        """Test remit_to_name extraction"""
        result = self.create_di_result({
            "RemitToName": {"value": "Accounts Receivable", "confidence": 0.91}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.remit_to_name == "Accounts Receivable"
    
    # ========== CONTRACT FIELDS (4 fields) ==========
    
    def test_entity_extraction(self, mock_di_client, field_extractor):
        """Test entity extraction"""
        result = self.create_di_result({
            "Entity": {"value": "CATSA", "confidence": 0.95}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.entity == "CATSA"
    
    def test_contract_id_extraction(self, mock_di_client, field_extractor):
        """Test contract_id extraction"""
        result = self.create_di_result({
            "ContractId": {"value": "CONTRACT-2024-001", "confidence": 0.93}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.contract_id == "CONTRACT-2024-001"
    
    def test_standing_offer_number_extraction(self, mock_di_client, field_extractor):
        """Test standing_offer_number extraction"""
        result = self.create_di_result({
            "StandingOfferNumber": {"value": "SO-2024-001", "confidence": 0.92}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.standing_offer_number == "SO-2024-001"
    
    def test_po_number_extraction(self, mock_di_client, field_extractor):
        """Test po_number extraction"""
        result = self.create_di_result({
            "PurchaseOrder": {"value": "PO-12345", "confidence": 0.94}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.po_number == "PO-12345"
    
    # ========== DATE FIELDS (4 fields) ==========
    
    def test_period_start_extraction(self, mock_di_client, field_extractor):
        """Test period_start extraction"""
        result = self.create_di_result({
            "ServiceStartDate": {"value": "2024-01-01", "confidence": 0.93}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.period_start == date(2024, 1, 1)
    
    def test_period_end_extraction(self, mock_di_client, field_extractor):
        """Test period_end extraction"""
        result = self.create_di_result({
            "ServiceEndDate": {"value": "2024-01-31", "confidence": 0.93}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.period_end == date(2024, 1, 31)
    
    def test_shipping_date_extraction(self, mock_di_client, field_extractor):
        """Test shipping_date extraction"""
        result = self.create_di_result({
            "ShippingDate": {"value": "2024-01-20", "confidence": 0.92}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.shipping_date == date(2024, 1, 20)
    
    def test_delivery_date_extraction(self, mock_di_client, field_extractor):
        """Test delivery_date extraction"""
        result = self.create_di_result({
            "DeliveryDate": {"value": "2024-01-25", "confidence": 0.92}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.delivery_date == date(2024, 1, 25)
    
    # ========== FINANCIAL FIELDS (5 fields) ==========
    
    def test_subtotal_extraction(self, mock_di_client, field_extractor):
        """Test subtotal extraction"""
        result = self.create_di_result({
            "SubTotal": {"value": 1000.00, "confidence": 0.95}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.subtotal == Decimal("1000.00")
    
    def test_discount_amount_extraction(self, mock_di_client, field_extractor):
        """Test discount_amount extraction"""
        result = self.create_di_result({
            "DiscountAmount": {"value": 50.00, "confidence": 0.90}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.discount_amount == Decimal("50.00")
    
    def test_shipping_amount_extraction(self, mock_di_client, field_extractor):
        """Test shipping_amount extraction"""
        result = self.create_di_result({
            "ShippingAmount": {"value": 25.00, "confidence": 0.91}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.shipping_amount == Decimal("25.00")
    
    def test_handling_fee_extraction(self, mock_di_client, field_extractor):
        """Test handling_fee extraction"""
        result = self.create_di_result({
            "HandlingFee": {"value": 10.00, "confidence": 0.89}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.handling_fee == Decimal("10.00")
    
    def test_deposit_amount_extraction(self, mock_di_client, field_extractor):
        """Test deposit_amount extraction"""
        result = self.create_di_result({
            "DepositAmount": {"value": 200.00, "confidence": 0.92}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.deposit_amount == Decimal("200.00")
    
    # ========== CANADIAN TAX FIELDS (8 fields) ==========
    
    def test_gst_amount_extraction(self, mock_di_client, field_extractor):
        """Test gst_amount extraction"""
        result = self.create_di_result({
            "GSTAmount": {"value": 50.00, "confidence": 0.94}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.gst_amount == Decimal("50.00")
    
    def test_gst_rate_extraction(self, mock_di_client, field_extractor):
        """Test gst_rate extraction"""
        result = self.create_di_result({
            "GSTRate": {"value": 0.05, "confidence": 0.93}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.gst_rate == Decimal("0.05")
    
    def test_hst_amount_extraction(self, mock_di_client, field_extractor):
        """Test hst_amount extraction"""
        result = self.create_di_result({
            "HSTAmount": {"value": 130.00, "confidence": 0.92}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.hst_amount == Decimal("130.00")
    
    def test_hst_rate_extraction(self, mock_di_client, field_extractor):
        """Test hst_rate extraction"""
        result = self.create_di_result({
            "HSTRate": {"value": 0.13, "confidence": 0.93}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.hst_rate == Decimal("0.13")
    
    def test_qst_amount_extraction(self, mock_di_client, field_extractor):
        """Test qst_amount extraction"""
        result = self.create_di_result({
            "QSTAmount": {"value": 99.75, "confidence": 0.91}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.qst_amount == Decimal("99.75")
    
    def test_qst_rate_extraction(self, mock_di_client, field_extractor):
        """Test qst_rate extraction"""
        result = self.create_di_result({
            "QSTRate": {"value": 0.09975, "confidence": 0.93}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.qst_rate == Decimal("0.09975")
    
    def test_pst_amount_extraction(self, mock_di_client, field_extractor):
        """Test pst_amount extraction"""
        result = self.create_di_result({
            "PSTAmount": {"value": 70.00, "confidence": 0.92}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.pst_amount == Decimal("70.00")
    
    def test_pst_rate_extraction(self, mock_di_client, field_extractor):
        """Test pst_rate extraction"""
        result = self.create_di_result({
            "PSTRate": {"value": 0.07, "confidence": 0.93}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.pst_rate == Decimal("0.07")
    
    # ========== TOTAL FIELDS (3 fields) ==========
    
    def test_tax_amount_extraction(self, mock_di_client, field_extractor):
        """Test tax_amount extraction"""
        result = self.create_di_result({
            "TotalTax": {"value": 150.00, "confidence": 0.95}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.tax_amount == Decimal("150.00")
    
    def test_total_amount_extraction(self, mock_di_client, field_extractor):
        """Test total_amount extraction"""
        result = self.create_di_result({
            "InvoiceTotal": {"value": 1150.00, "confidence": 0.96}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.total_amount == Decimal("1150.00")
    
    def test_currency_extraction(self, mock_di_client, field_extractor):
        """Test currency extraction"""
        result = self.create_di_result({
            "CurrencyCode": {"value": "CAD", "confidence": 0.98}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.currency == "CAD"
    
    # ========== PAYMENT FIELDS (5 fields) ==========
    
    def test_payment_terms_extraction(self, mock_di_client, field_extractor):
        """Test payment_terms extraction"""
        result = self.create_di_result({
            "PaymentTerm": {"value": "Net 30", "confidence": 0.94}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.payment_terms == "Net 30"
    
    def test_payment_method_extraction(self, mock_di_client, field_extractor):
        """Test payment_method extraction"""
        result = self.create_di_result({
            "PaymentMethod": {"value": "EFT", "confidence": 0.92}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.payment_method == "EFT"
    
    def test_payment_due_upon_extraction(self, mock_di_client, field_extractor):
        """Test payment_due_upon extraction"""
        result = self.create_di_result({
            "PaymentDueUpon": {"value": "Receipt", "confidence": 0.91}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.payment_due_upon == "Receipt"
    
    def test_tax_registration_number_extraction(self, mock_di_client, field_extractor):
        """Test tax_registration_number extraction"""
        result = self.create_di_result({
            "TaxRegistrationNumber": {"value": "139666721", "confidence": 0.93}
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        assert invoice.tax_registration_number == "139666721"
    
    # ========== COMPREHENSIVE TEST ==========
    
    def test_comprehensive_field_extraction(self, mock_di_client, field_extractor):
        """Test extraction of multiple fields in a single invoice"""
        result = self.create_di_result({
            "InvoiceId": {"value": "INV-2024-001", "confidence": 0.98},
            "InvoiceDate": {"value": "2024-01-15", "confidence": 0.96},
            "DueDate": {"value": "2024-02-15", "confidence": 0.94},
            "VendorName": {"value": "Acme Corporation", "confidence": 0.95},
            "CustomerName": {"value": "CATSA", "confidence": 0.96},
            "SubTotal": {"value": 1000.00, "confidence": 0.95},
            "TotalTax": {"value": 150.00, "confidence": 0.95},
            "InvoiceTotal": {"value": 1150.00, "confidence": 0.96},
            "CurrencyCode": {"value": "CAD", "confidence": 0.98},
            "PaymentTerm": {"value": "Net 30", "confidence": 0.94},
            "PurchaseOrder": {"value": "PO-12345", "confidence": 0.94},
        })
        di_data = mock_di_client._extract_invoice_fields(result)
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path="test.pdf",
            file_name="test.pdf",
            upload_date=datetime.utcnow()
        )
        
        # Verify all fields
        assert invoice.invoice_number == "INV-2024-001"
        assert invoice.invoice_date == date(2024, 1, 15)
        assert invoice.due_date == date(2024, 2, 15)
        assert invoice.vendor_name == "Acme Corporation"
        assert invoice.customer_name == "CATSA"
        assert invoice.subtotal == Decimal("1000.00")
        assert invoice.tax_amount == Decimal("150.00")
        assert invoice.total_amount == Decimal("1150.00")
        assert invoice.currency == "CAD"
        assert invoice.payment_terms == "Net 30"
        assert invoice.po_number == "PO-12345"

