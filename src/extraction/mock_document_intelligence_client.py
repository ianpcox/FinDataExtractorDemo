"""Mock Azure Document Intelligence client for demo mode - returns realistic sample data"""

from typing import Optional, Dict, Any
import logging
from datetime import datetime, date
from decimal import Decimal
import random

logger = logging.getLogger(__name__)


class MockDocumentIntelligenceClient:
    """Mock client that returns realistic sample invoice data for demos"""
    
    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize mock client (endpoint and api_key are ignored in demo mode)
        
        Args:
            endpoint: Ignored in demo mode
            api_key: Ignored in demo mode
        """
        logger.info("Mock Document Intelligence client initialized (DEMO MODE)")
        self._sample_invoices = self._generate_sample_responses()
    
    def analyze_invoice(self, file_content: bytes) -> Dict[str, Any]:
        """
        Analyze invoice PDF - returns realistic sample data
        
        Args:
            file_content: PDF file content (ignored in demo mode)
            
        Returns:
            Dictionary with realistic extracted invoice data
        """
        # Select a random sample invoice or use a deterministic one based on file hash
        import hashlib
        file_hash = hashlib.md5(file_content[:1000]).hexdigest() if file_content else "default"
        sample_idx = int(file_hash[:2], 16) % len(self._sample_invoices)
        sample = self._sample_invoices[sample_idx]
        
        logger.info(f"Mock Document Intelligence: Returning sample invoice {sample_idx + 1}")
        return sample
    
    def _generate_sample_responses(self) -> list:
        """Generate realistic sample invoice responses"""
        samples = []
        
        # Sample 1: Standard invoice with high confidence
        samples.append({
            "confidence": 0.95,
            "invoice_id": "INV-2024-001234",
            "invoice_date": date(2024, 1, 15),
            "due_date": date(2024, 2, 15),
            "invoice_total": Decimal("1250.00"),
            "subtotal": Decimal("1150.00"),
            "total_tax": Decimal("100.00"),
            "vendor_name": "Acme Office Supplies Inc.",
            "vendor_address": {
                "street_address": "123 Business Park Drive",
                "city": "Toronto",
                "state": "ON",
                "postal_code": "M5H 2N2",
                "country_region": "Canada"
            },
            "vendor_phone": "+1 (416) 555-0123",
            "customer_name": "Canadian Air Transport Security Authority",
            "customer_id": "CATSA-001",
            "customer_address": {
                "street_address": "99 Bank Street, Suite 400",
                "city": "Ottawa",
                "state": "ON",
                "postal_code": "K1P 6B9",
                "country_region": "Canada"
            },
            "remit_to_address": {
                "street_address": "123 Business Park Drive",
                "city": "Toronto",
                "state": "ON",
                "postal_code": "M5H 2N2",
                "country_region": "Canada"
            },
            "remit_to_name": "Acme Office Supplies Inc.",
            "payment_term": "Net 30",
            "purchase_order": "PO-2024-0567",
            "standing_offer_number": None,
            "tax_registration_number": "123456789RT0001",
            "currency": "CAD",
            "items": [
                {
                    "description": "Office Chairs - Ergonomic",
                    "quantity": Decimal("10"),
                    "unit_price": Decimal("75.00"),
                    "amount": Decimal("750.00"),
                    "tax": Decimal("97.50"),
                    "confidence": 0.92
                },
                {
                    "description": "Desk Organizers - Set of 5",
                    "quantity": Decimal("8"),
                    "unit_price": Decimal("50.00"),
                    "amount": Decimal("400.00"),
                    "tax": Decimal("2.50"),
                    "confidence": 0.88
                }
            ],
            "field_confidence": {
                "InvoiceId": 0.98,
                "InvoiceDate": 0.95,
                "VendorName": 0.92,
                "InvoiceTotal": 0.97,
                "Items": 0.90,
                "VendorAddress": 0.88,
                "CustomerName": 0.90,
                "SubTotal": 0.96,
                "TotalTax": 0.94
            },
            "content": "INVOICE\nAcme Office Supplies Inc.\n123 Business Park Drive, Toronto, ON M5H 2N2\nInvoice #: INV-2024-001234\nDate: January 15, 2024\nDue Date: February 15, 2024\n\nBill To:\nCanadian Air Transport Security Authority\n99 Bank Street, Suite 400\nOttawa, ON K1P 6B9\n\nItems:\n10x Office Chairs - Ergonomic @ $75.00 = $750.00\n8x Desk Organizers - Set of 5 @ $50.00 = $400.00\n\nSubtotal: $1,150.00\nTax: $100.00\nTotal: $1,250.00\n\nPayment Terms: Net 30\nPO Number: PO-2024-0567"
        })
        
        # Sample 2: Service invoice with medium confidence
        samples.append({
            "confidence": 0.82,
            "invoice_id": "SRV-2024-005678",
            "invoice_date": date(2024, 2, 1),
            "due_date": date(2024, 3, 3),
            "invoice_total": Decimal("3450.50"),
            "subtotal": Decimal("3200.00"),
            "total_tax": Decimal("250.50"),
            "vendor_name": "SecureTech Services Ltd.",
            "vendor_address": {
                "street_address": "456 Security Boulevard",
                "city": "Montreal",
                "state": "QC",
                "postal_code": "H3A 0G4",
                "country_region": "Canada"
            },
            "vendor_phone": "+1 (514) 555-0456",
            "customer_name": "Canadian Air Transport Security Authority",
            "customer_id": "CATSA-001",
            "customer_address": {
                "street_address": "99 Bank Street, Suite 400",
                "city": "Ottawa",
                "state": "ON",
                "postal_code": "K1P 6B9",
                "country_region": "Canada"
            },
            "remit_to_address": {
                "street_address": "456 Security Boulevard",
                "city": "Montreal",
                "state": "QC",
                "postal_code": "H3A 0G4",
                "country_region": "Canada"
            },
            "remit_to_name": "SecureTech Services Ltd.",
            "payment_term": "Net 30",
            "purchase_order": None,
            "standing_offer_number": "SO-2023-1234",
            "tax_registration_number": "987654321RT0001",
            "currency": "CAD",
            "items": [
                {
                    "description": "Security System Maintenance - Monthly",
                    "quantity": Decimal("1"),
                    "unit_price": Decimal("3200.00"),
                    "amount": Decimal("3200.00"),
                    "tax": Decimal("250.50"),
                    "confidence": 0.85
                }
            ],
            "field_confidence": {
                "InvoiceId": 0.85,
                "InvoiceDate": 0.80,
                "VendorName": 0.88,
                "InvoiceTotal": 0.82,
                "Items": 0.78,
                "VendorAddress": 0.82,
                "CustomerName": 0.85,
                "SubTotal": 0.83,
                "TotalTax": 0.80
            },
            "content": "SERVICE INVOICE\nSecureTech Services Ltd.\n456 Security Boulevard, Montreal, QC H3A 0G4\nInvoice #: SRV-2024-005678\nDate: February 1, 2024\nDue Date: March 3, 2024\n\nBill To:\nCanadian Air Transport Security Authority\n99 Bank Street, Suite 400\nOttawa, ON K1P 6B9\n\nServices:\nSecurity System Maintenance - Monthly: $3,200.00\n\nSubtotal: $3,200.00\nTax: $250.50\nTotal: $3,450.50\n\nStanding Offer: SO-2023-1234\nPayment Terms: Net 30"
        })
        
        # Sample 3: Timesheet invoice with lower confidence (for HITL demo)
        samples.append({
            "confidence": 0.75,
            "invoice_id": "TS-2024-009876",
            "invoice_date": date(2024, 2, 15),
            "due_date": date(2024, 3, 17),
            "invoice_total": Decimal("5678.90"),
            "subtotal": Decimal("5200.00"),
            "total_tax": Decimal("478.90"),
            "vendor_name": "TempStaff Solutions Inc.",
            "vendor_address": {
                "street_address": "789 Employment Avenue",
                "city": "Vancouver",
                "state": "BC",
                "postal_code": "V6B 1A1",
                "country_region": "Canada"
            },
            "vendor_phone": "+1 (604) 555-0789",
            "customer_name": "Canadian Air Transport Security Authority",
            "customer_id": "CATSA-001",
            "customer_address": {
                "street_address": "99 Bank Street, Suite 400",
                "city": "Ottawa",
                "state": "ON",
                "postal_code": "K1P 6B9",
                "country_region": "Canada"
            },
            "remit_to_address": {
                "street_address": "789 Employment Avenue",
                "city": "Vancouver",
                "state": "BC",
                "postal_code": "V6B 1A1",
                "country_region": "Canada"
            },
            "remit_to_name": "TempStaff Solutions Inc.",
            "payment_term": "Net 30",
            "purchase_order": "PO-2024-0890",
            "standing_offer_number": None,
            "tax_registration_number": "112233445RT0001",
            "currency": "CAD",
            "items": [
                {
                    "description": "Security Personnel - Week 1",
                    "quantity": Decimal("80"),
                    "unit_price": Decimal("35.00"),
                    "amount": Decimal("2800.00"),
                    "tax": Decimal("238.00"),
                    "confidence": 0.72
                },
                {
                    "description": "Security Personnel - Week 2",
                    "quantity": Decimal("80"),
                    "unit_price": Decimal("35.00"),
                    "amount": Decimal("2400.00"),
                    "tax": Decimal("240.90"),
                    "confidence": 0.70
                }
            ],
            "field_confidence": {
                "InvoiceId": 0.78,
                "InvoiceDate": 0.73,
                "VendorName": 0.70,
                "InvoiceTotal": 0.75,
                "Items": 0.68,
                "VendorAddress": 0.72,
                "CustomerName": 0.75,
                "SubTotal": 0.76,
                "TotalTax": 0.74
            },
            "content": "TIMESHEET INVOICE\nTempStaff Solutions Inc.\n789 Employment Avenue, Vancouver, BC V6B 1A1\nInvoice #: TS-2024-009876\nDate: February 15, 2024\nDue Date: March 17, 2024\n\nBill To:\nCanadian Air Transport Security Authority\n99 Bank Street, Suite 400\nOttawa, ON K1P 6B9\n\nHours:\nWeek 1: 80 hours @ $35.00/hr = $2,800.00\nWeek 2: 80 hours @ $35.00/hr = $2,400.00\n\nSubtotal: $5,200.00\nTax: $478.90\nTotal: $5,678.90\n\nPO Number: PO-2024-0890\nPayment Terms: Net 30"
        })
        
        return samples

