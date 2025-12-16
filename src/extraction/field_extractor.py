"""Field extraction and mapping from Document Intelligence to Invoice model"""

from typing import Dict, Any, Optional, List
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from src.models.invoice import (
    Invoice, LineItem, Address, InvoiceSubtype, InvoiceExtensions
)
from src.models.invoice_subtypes import (
    ShiftServiceExtension,
    PerDiemTravelExtension,
    create_extension_from_data
)
from src.extraction.subtype_extractors import (
    ShiftServiceExtractor,
    PerDiemTravelExtractor
)
import logging
import re

logger = logging.getLogger(__name__)


class FieldExtractor:
    """Extracts and maps fields from Document Intelligence to Invoice model"""
    
    def __init__(self):
        """Initialize field extractor with subtype extractors"""
        self.shift_service_extractor = ShiftServiceExtractor()
        self.per_diem_travel_extractor = PerDiemTravelExtractor()
    
    def extract_invoice(
        self,
        doc_intelligence_data: Dict[str, Any],
        file_path: str,
        file_name: str,
        upload_date: datetime,
        invoice_text: Optional[str] = None
    ) -> Invoice:
        """
        Extract Invoice model from Document Intelligence data
        
        Args:
            doc_intelligence_data: Raw data from Document Intelligence
            file_path: Path to the PDF file
            file_name: Original file name
            upload_date: Upload timestamp
            invoice_text: Optional raw text content for subtype extraction
            
        Returns:
            Invoice model instance
        """
        # Extract basic invoice
        invoice = Invoice(
            id=None,  # Will be set by caller
            file_path=file_path,
            file_name=file_name,
            upload_date=upload_date,
            status="extracted"
        )
        # stash for line item post-processing (tax aggregation)
        self._current_invoice = invoice
        
        # Extract field-level confidence
        field_confidence = self._extract_field_confidence(doc_intelligence_data)
        invoice.field_confidence = field_confidence
        
        # Map Document Intelligence fields to Invoice model - Header
        invoice.invoice_number = self._get_field_value(
            doc_intelligence_data.get("invoice_id"), field_confidence.get("invoice_id")
        )
        invoice.invoice_date = self._parse_date(
            doc_intelligence_data.get("invoice_date"), field_confidence.get("invoice_date")
        )
        invoice.due_date = self._parse_date(
            doc_intelligence_data.get("due_date"), field_confidence.get("due_date")
        )
        
        # Vendor information
        invoice.vendor_name = self._get_field_value(
            doc_intelligence_data.get("vendor_name"), field_confidence.get("vendor_name")
        )
        invoice.vendor_id = self._get_field_value(
            doc_intelligence_data.get("vendor_id"), field_confidence.get("vendor_id")
        )
        vendor_address = doc_intelligence_data.get("vendor_address")
        if vendor_address:
            invoice.vendor_address = self._map_address(vendor_address)
        
        # Customer information
        invoice.customer_name = self._get_field_value(
            doc_intelligence_data.get("customer_name"), field_confidence.get("customer_name")
        )
        invoice.customer_id = self._get_field_value(
            doc_intelligence_data.get("customer_id"), field_confidence.get("customer_id")
        )
        invoice.entity = self._get_field_value(
            doc_intelligence_data.get("entity"), field_confidence.get("entity")
        )
        customer_address = doc_intelligence_data.get("customer_address")
        if customer_address:
            invoice.bill_to_address = self._map_address(customer_address)
        
        # Contract and PO
        invoice.contract_id = self._get_field_value(
            doc_intelligence_data.get("contract_id"), field_confidence.get("contract_id")
        )
        invoice.standing_offer_number = self._get_field_value(
            doc_intelligence_data.get("standing_offer_number"), field_confidence.get("standing_offer_number")
        )
        invoice.po_number = self._get_field_value(
            doc_intelligence_data.get("purchase_order"), field_confidence.get("purchase_order")
        )
        
        # Period covered
        invoice.period_start = self._parse_date(
            doc_intelligence_data.get("service_start_date"), field_confidence.get("service_start_date")
        )
        invoice.period_end = self._parse_date(
            doc_intelligence_data.get("service_end_date"), field_confidence.get("service_end_date")
        )
        
        # Financial fields
        invoice.subtotal = self._parse_decimal(
            doc_intelligence_data.get("subtotal"), field_confidence.get("subtotal")
        )
        invoice.tax_amount = self._parse_decimal(
            doc_intelligence_data.get("total_tax"), field_confidence.get("total_tax")
        )
        invoice.total_amount = self._parse_decimal(
            doc_intelligence_data.get("invoice_total"), field_confidence.get("invoice_total")
        )
        
        # Tax breakdown (by tax type)
        invoice.tax_breakdown = self._extract_tax_breakdown(doc_intelligence_data)
        
        # Currency
        currency = doc_intelligence_data.get("currency")
        invoice.currency = self._normalize_currency(currency) if currency else "CAD"
        
        # Payment terms
        invoice.payment_terms = self._get_field_value(
            doc_intelligence_data.get("payment_term"), field_confidence.get("payment_term")
        )
        
        # Line items
        items_data = doc_intelligence_data.get("items", [])
        invoice.line_items = self._extract_line_items(items_data, field_confidence)
        # Derive totals if missing
        if invoice.line_items:
            line_sum = sum([item.amount or Decimal("0.00") for item in invoice.line_items], Decimal("0.00"))
            if invoice.subtotal is None:
                invoice.subtotal = line_sum
            # If total missing but we have subtotal and tax_amount
            if invoice.total_amount is None and invoice.subtotal is not None:
                invoice.total_amount = invoice.subtotal + (invoice.tax_amount or Decimal("0.00"))
            # If tax_amount missing but we have total and subtotal
            if invoice.tax_amount is None and invoice.total_amount is not None and invoice.subtotal is not None:
                invoice.tax_amount = invoice.total_amount - invoice.subtotal
        invoice.acceptance_percentage = self._parse_decimal(
            doc_intelligence_data.get("acceptance_percentage"), field_confidence.get("acceptance_percentage")
        )
        invoice.tax_registration_number = self._get_field_value(
            doc_intelligence_data.get("tax_registration_number"), field_confidence.get("tax_registration_number")
        )
        invoice.vendor_phone = self._get_field_value(
            doc_intelligence_data.get("vendor_phone"), field_confidence.get("vendor_phone")
        )
        remit_addr = doc_intelligence_data.get("remit_to_address")
        if remit_addr:
            invoice.remit_to_address = self._map_address(remit_addr)
        invoice.remit_to_name = self._get_field_value(
            doc_intelligence_data.get("remit_to_name"), field_confidence.get("remit_to_name")
        )
        
        # Calculate overall confidence
        invoice.extraction_confidence = self._calculate_overall_confidence(field_confidence)
        invoice.extraction_timestamp = datetime.utcnow()
        
        # Detect and extract subtype
        invoice.invoice_subtype, invoice.extensions = self._detect_and_extract_subtype(
            doc_intelligence_data, invoice, invoice_text
        )
        
        return invoice
    
    def _extract_field_confidence(self, di_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract field-level confidence from Document Intelligence data"""
        confidence = {}
        
        # Document Intelligence provides confidence per field with DI field names
        # Map DI field names to our field names
        if "field_confidence" in di_data:
            di_field_confidence = di_data["field_confidence"]
            
            # Map Document Intelligence field names to our field names
            field_mapping = {
                "InvoiceId": "invoice_id",
                "InvoiceDate": "invoice_date",
                "DueDate": "due_date",
                "VendorName": "vendor_name",
                "VendorPhoneNumber": "vendor_phone",
                "VendorPhone": "vendor_phone",
                "CustomerName": "customer_name",
                "CustomerId": "customer_id",
                "VendorAddress": "vendor_address",
                "CustomerAddress": "customer_address",
                "BillToAddress": "bill_to_address",
                "SubTotal": "subtotal",
                "TotalTax": "total_tax",
                "InvoiceTotal": "invoice_total",
                "PurchaseOrder": "purchase_order",
                "PaymentTerm": "payment_term",
                "PaymentTerms": "payment_term",
                "ServiceStartDate": "service_start_date",
                "ServiceEndDate": "service_end_date",
                "CurrencyCode": "currency",
                "Currency": "currency",
                "RemitToAddress": "remit_to_address",
                "RemittanceAddress": "remit_to_address",
                "RemitToName": "remit_to_name",
                "ContractId": "standing_offer_number",
                "StandingOfferNumber": "standing_offer_number",
                "AcceptancePercentage": "acceptance_percentage",
                "TaxRegistrationNumber": "tax_registration_number",
                "SalesTaxNumber": "tax_registration_number",
            }
            
            # Map DI field names to our field names
            for di_field_name, our_field_name in field_mapping.items():
                if di_field_name in di_field_confidence:
                    confidence[our_field_name] = di_field_confidence[di_field_name]
        
        # Also check if fields have confidence embedded
        # Try to extract from Document Intelligence result structure
        # This would come from the actual DI response structure
        # For now, use default confidence if not available
        field_mapping_reverse = {
            "invoice_id": "InvoiceId",
            "invoice_date": "InvoiceDate",
            "due_date": "DueDate",
            "vendor_name": "VendorName",
            "vendor_phone": "VendorPhoneNumber",
            "customer_name": "CustomerName",
            "customer_id": "CustomerId",
            "vendor_address": "VendorAddress",
            "customer_address": "CustomerAddress",
            "bill_to_address": "BillToAddress",
            "subtotal": "SubTotal",
            "total_tax": "TotalTax",
            "invoice_total": "InvoiceTotal",
            "purchase_order": "PurchaseOrder",
            "payment_term": "PaymentTerms",
            "remit_to_address": "RemitToAddress",
            "remit_to_name": "RemitToName",
            "standing_offer_number": "StandingOfferNumber",
            "acceptance_percentage": "AcceptancePercentage",
            "tax_registration_number": "TaxRegistrationNumber",
        }
        
        for key, di_field in field_mapping_reverse.items():
            if key not in confidence:
                # Default to 0.85 if field is present (even if value is 0/False), else 0.0
                value_present = key in di_data and di_data[key] is not None
                confidence[key] = 0.85 if value_present else 0.0
        
        return confidence
    
    def _get_field_value(self, field: Any, confidence: Optional[float] = None) -> Optional[Any]:
        """Extract value from Document Intelligence field"""
        if field is None:
            return None
        
        if isinstance(field, dict):
            return field.get("content") or field.get("value") or field.get("text")
        
        return field
    
    def _parse_date(self, date_value: Any, confidence: Optional[float] = None) -> Optional[date]:
        """Parse date from various formats"""
        if not date_value:
            return None
        
        if isinstance(date_value, date):
            return date_value
        
        if isinstance(date_value, datetime):
            return date_value.date()
        
        if isinstance(date_value, str):
            try:
                # Try ISO format
                dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                return dt.date()
            except ValueError:
                try:
                    # Try date format
                    return datetime.strptime(date_value, "%Y-%m-%d").date()
                except ValueError:
                    logger.warning(f"Could not parse date: {date_value}")
                    return None
        
        return None
    
    def _parse_decimal(self, decimal_value: Any, confidence: Optional[float] = None) -> Optional[Decimal]:
        """Parse decimal from various formats"""
        if decimal_value is None:
            return None
        
        if isinstance(decimal_value, Decimal):
            return decimal_value
        
        if isinstance(decimal_value, (int, float)):
            return Decimal(str(decimal_value))
        
        if isinstance(decimal_value, str):
            # Remove currency symbols and whitespace
            cleaned = decimal_value.replace("$", "").replace(",", "").strip()
            if not cleaned:
                return None
            try:
                return Decimal(cleaned)
            except (ValueError, TypeError, InvalidOperation):
                logger.warning(f"Could not parse decimal: {decimal_value}")
                return None
        
        if isinstance(decimal_value, dict):
            value = decimal_value.get("content") or decimal_value.get("value")
            return self._parse_decimal(value, confidence)
        
        return None
    
    def _map_address(self, address_data: Dict) -> Address:
        """Map Document Intelligence address to Address model"""
        if not address_data:
            return Address()
        
        # Handle different address formats
        if isinstance(address_data, str):
            # Try to parse string address
            return Address()
        
        street = (
            address_data.get("street_address") or
            address_data.get("road") or
            ""
        )
        
        # Combine house number and road if separate
        if address_data.get("house_number") and address_data.get("road"):
            street = f"{address_data.get('house_number')} {address_data.get('road')}"
        
        return Address(
            street=street,
            city=address_data.get("city"),
            province=address_data.get("state") or address_data.get("province"),
            postal_code=address_data.get("postal_code"),
            country=address_data.get("country_region") or address_data.get("country")
        )
    
    def _extract_tax_breakdown(self, di_data: Dict[str, Any]) -> Optional[Dict[str, Decimal]]:
        """Extract tax breakdown by tax type"""
        # Document Intelligence may provide tax breakdown
        # This is typically in a structured format
        tax_breakdown = di_data.get("tax_breakdown")
        if tax_breakdown:
            result = {}
            if isinstance(tax_breakdown, dict):
                for tax_type, amount in tax_breakdown.items():
                    parsed_amount = self._parse_decimal(amount)
                    if parsed_amount:
                        result[tax_type] = parsed_amount
            return result if result else None
        
        # If no breakdown, return None (tax_amount is already set)
        return None
    
    def _extract_line_items(
        self,
        items_data: List[Dict[str, Any]],
        field_confidence: Dict[str, float]
    ) -> List[LineItem]:
        """Extract line items from Document Intelligence data"""
        line_items = []
        tax_line_total = Decimal("0.00")
        
        for idx, item_data in enumerate(items_data, start=1):
            if not isinstance(item_data, dict):
                continue
            
            # Get item confidence (default to 0.85 if field exists)
            item_conf = item_data.get("confidence", 0.85)
            desc_val = self._get_field_value(item_data.get("description")) or ""
            desc_lower = desc_val.lower()

            # Skip tax lines; accumulate into tax_line_total instead of showing as line item
            if "tax" in desc_lower:
                amt = self._parse_decimal(item_data.get("amount"))
                if amt:
                    tax_line_total += amt
                continue

            line_item = LineItem(
                line_number=idx,
                description=desc_val,
                quantity=self._parse_decimal(item_data.get("quantity")),
                unit_price=self._parse_decimal(item_data.get("unit_price")),
                amount=self._parse_decimal(item_data.get("amount")) or Decimal("0.00"),
                confidence=item_conf,
                unit_of_measure=item_data.get("unit"),
                tax_rate=self._parse_decimal(item_data.get("tax_rate")),
                tax_amount=self._parse_decimal(item_data.get("tax")),
                project_code=item_data.get("project_code"),
                region_code=item_data.get("region_code"),
                airport_code=item_data.get("airport_code"),
                cost_centre_code=item_data.get("cost_centre_code"),
            )
            
            line_items.append(line_item)
        
        # If we skipped tax lines, fold them into overall tax_amount if not already set
        if tax_line_total and (self_invoice := getattr(self, "_current_invoice", None)):
            if not self_invoice.tax_amount:
                self_invoice.tax_amount = tax_line_total
            else:
                self_invoice.tax_amount = (self_invoice.tax_amount or Decimal("0.00")) + tax_line_total
        
        return line_items
    
    def _normalize_currency(self, currency: Any) -> str:
        """Normalize currency code to ISO 4217 format"""
        if not currency:
            return "CAD"
        
        if isinstance(currency, dict):
            currency = currency.get("content") or currency.get("value") or currency.get("text", "")
        
        currency_str = str(currency).strip().upper()
        
        currency_map = {
            "$": "USD",
            "C$": "CAD",
            "CAD": "CAD",
            "CAN": "CAD",
            "CANADIAN DOLLAR": "CAD",
            "USD": "USD",
            "US$": "USD",
            "US DOLLAR": "USD",
            "EUR": "EUR",
            "€": "EUR",
            "EURO": "EUR",
        }
        
        if currency_str in currency_map:
            return currency_map[currency_str]
        
        if len(currency_str) == 3 and currency_str.isalpha():
            return currency_str
        
        # Default to CAD
        return "CAD"
    
    def _calculate_overall_confidence(self, field_confidence: Dict[str, float]) -> float:
        """Calculate overall extraction confidence from field-level confidences"""
        if not field_confidence:
            return 0.0
        
        # Important fields get higher weight
        important_fields = [
            "invoice_id", "invoice_date", "invoice_total",
            "vendor_name", "subtotal", "total_tax"
        ]
        
        important_scores = [field_confidence.get(f, 0.0) for f in important_fields if f in field_confidence]
        other_scores = [
            v for k, v in field_confidence.items()
            if k not in important_fields and v > 0.0
        ]
        
        if important_scores:
            important_avg = sum(important_scores) / len(important_scores)
            other_avg = sum(other_scores) / len(other_scores) if other_scores else 0.0
            
            # Weight important fields 70%, other fields 30%
            weighted = (important_avg * 0.7) + (other_avg * 0.3)
            return min(1.0, max(0.0, weighted))
        
        # Fallback to average of all fields
        if field_confidence:
            return sum(field_confidence.values()) / len(field_confidence)
        
        return 0.0
    
    def _detect_and_extract_subtype(
        self,
        doc_intelligence_data: Dict[str, Any],
        invoice: Invoice,
        invoice_text: Optional[str]
    ) -> tuple[InvoiceSubtype, Optional[InvoiceExtensions]]:
        """
        Detect invoice subtype and extract extension data
        
        Returns:
            Tuple of (subtype, extensions)
        """
        extensions = InvoiceExtensions()
        detected_subtype = InvoiceSubtype.STANDARD_INVOICE
        
        # Try to detect ShiftService pattern
        shift_ext = self.shift_service_extractor.extract(
            doc_intelligence_data, invoice_text
        )
        if shift_ext:
            extensions.shift_service = shift_ext
            detected_subtype = InvoiceSubtype.SHIFT_SERVICE_INVOICE
            logger.info(f"Detected ShiftService invoice subtype")
        
        # Try to detect PerDiemTravel pattern
        # Convert line items to dict format for extractor
        line_items_dict = [
            {
                "description": item.description,
                "amount": float(item.amount) if item.amount else None,
                "quantity": float(item.quantity) if item.quantity else None,
            }
            for item in invoice.line_items
        ]
        
        travel_exts = self.per_diem_travel_extractor.extract(
            doc_intelligence_data, line_items_dict, invoice_text
        )
        if travel_exts:
            extensions.per_diem_travel = travel_exts
            detected_subtype = InvoiceSubtype.PER_DIEM_TRAVEL_INVOICE
            logger.info(f"Detected PerDiemTravel invoice subtype with {len(travel_exts)} extensions")
        
        # Return extensions only if we found something
        if extensions.shift_service or extensions.per_diem_travel:
            return detected_subtype, extensions
        
        return InvoiceSubtype.STANDARD_INVOICE, None

