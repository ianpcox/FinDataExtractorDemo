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

    DI_TO_CANONICAL = {
        "InvoiceId": "invoice_number",
        "InvoiceDate": "invoice_date",
        "InvoiceType": "invoice_type",
        "ReferenceNumber": "reference_number",
        "DueDate": "due_date",
        "ShippingDate": "shipping_date",
        "DeliveryDate": "delivery_date",
        "VendorName": "vendor_name",
        "VendorId": "vendor_id",
        "VendorPhoneNumber": "vendor_phone",
        "VendorPhone": "vendor_phone",
        "VendorFax": "vendor_fax",
        "VendorFaxNumber": "vendor_fax",
        "VendorEmail": "vendor_email",
        "VendorWebsite": "vendor_website",
        "VendorAddress": "vendor_address",
        "BusinessNumber": "business_number",
        "GSTNumber": "gst_number",
        "QSTNumber": "qst_number",
        "PSTNumber": "pst_number",
        "CustomerName": "customer_name",
        "CustomerId": "customer_id",
        "CustomerPhone": "customer_phone",
        "CustomerEmail": "customer_email",
        "CustomerFax": "customer_fax",
        "CustomerAddress": "bill_to_address",
        "BillToAddress": "bill_to_address",
        "RemitToAddress": "remit_to_address",
        "RemittanceAddress": "remit_to_address",
        "RemitToName": "remit_to_name",
        "Entity": "entity",
        "ContractId": "contract_id",
        "StandingOfferNumber": "standing_offer_number",
        "PurchaseOrder": "po_number",
        "PONumber": "po_number",
        "ServiceStartDate": "period_start",
        "ServiceEndDate": "period_end",
        "SubTotal": "subtotal",
        "DiscountAmount": "discount_amount",
        "ShippingAmount": "shipping_amount",
        "HandlingFee": "handling_fee",
        "DepositAmount": "deposit_amount",
        "GSTAmount": "gst_amount",
        "GSTRate": "gst_rate",
        "HSTAmount": "hst_amount",
        "HSTRate": "hst_rate",
        "QSTAmount": "qst_amount",
        "QSTRate": "qst_rate",
        "PSTAmount": "pst_amount",
        "PSTRate": "pst_rate",
        "TotalTax": "tax_amount",
        "InvoiceTotal": "total_amount",
        "CurrencyCode": "currency",
        "Currency": "currency",
        "PaymentTerm": "payment_terms",
        "PaymentTerms": "payment_terms",
        "PaymentMethod": "payment_method",
        "PaymentDueUpon": "payment_due_upon",
        "TaxRegistrationNumber": "tax_registration_number",
        "SalesTaxNumber": "tax_registration_number",
    }

    def __init__(self):
        """Initialize field extractor with subtype extractors"""
        self.shift_service_extractor = ShiftServiceExtractor()
        self.per_diem_travel_extractor = PerDiemTravelExtractor()

    def normalize_di_data(self, di_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize DI payload to canonical invoice field names."""
        canonical: Dict[str, Any] = {}
        if not di_data:
            return canonical

        # Map known DI fields to canonical
        for di_key, canon_key in self.DI_TO_CANONICAL.items():
            if di_key in di_data:
                canonical[canon_key] = di_data.get(di_key)

        # Keep items/content if present
        if "items" in di_data:
            canonical["items"] = di_data["items"]
        if "content" in di_data:
            canonical["content"] = di_data["content"]

        # Allow already canonical keys in the input to pass through
        for key in [
            "invoice_number", "invoice_type", "reference_number", "invoice_date", "due_date", 
            "shipping_date", "delivery_date", "vendor_name", "vendor_id",
            "vendor_phone", "vendor_fax", "vendor_email", "vendor_website", "vendor_address", 
            "business_number", "gst_number", "qst_number", "pst_number",
            "customer_name", "customer_id", "customer_phone", "customer_email", "customer_fax",
            "bill_to_address", "remit_to_address", "remit_to_name", "entity",
            "contract_id", "standing_offer_number", "po_number", "period_start",
            "period_end", "subtotal", "discount_amount", "shipping_amount", "handling_fee", 
            "deposit_amount", "gst_amount", "gst_rate", "hst_amount", "hst_rate",
            "qst_amount", "qst_rate", "pst_amount", "pst_rate",
            "tax_breakdown", "tax_amount", "total_amount",
            "currency", "tax_registration_number",
            "payment_terms", "payment_method", "payment_due_upon", "items", "content"
        ]:
            if key in di_data and key not in canonical:
                canonical[key] = di_data[key]

        # Map field_confidence using canonical extractor
        fc_canonical = self._extract_field_confidence(di_data)
        if fc_canonical:
            canonical["field_confidence"] = fc_canonical

        return canonical
    
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
        canonical_data = self.normalize_di_data(doc_intelligence_data)

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
        field_confidence = canonical_data.get("field_confidence", {})
        invoice.field_confidence = field_confidence
        
        # Map Document Intelligence fields to Invoice model - Header
        invoice.invoice_number = self._get_field_value(
            canonical_data.get("invoice_number"), field_confidence.get("invoice_number")
        )
        if invoice.invoice_number is None:
            invoice.invoice_number = doc_intelligence_data.get("invoice_id") or doc_intelligence_data.get("InvoiceId")
        
        invoice.invoice_type = self._get_field_value(
            canonical_data.get("invoice_type"), field_confidence.get("invoice_type")
        )
        invoice.reference_number = self._get_field_value(
            canonical_data.get("reference_number"), field_confidence.get("reference_number")
        )
        invoice.invoice_date = self._parse_date(
            canonical_data.get("invoice_date"), field_confidence.get("invoice_date")
        )
        invoice.due_date = self._parse_date(
            canonical_data.get("due_date"), field_confidence.get("due_date")
        )
        invoice.shipping_date = self._parse_date(
            canonical_data.get("shipping_date"), field_confidence.get("shipping_date")
        )
        invoice.delivery_date = self._parse_date(
            canonical_data.get("delivery_date"), field_confidence.get("delivery_date")
        )
        
        # Vendor information
        invoice.vendor_name = self._get_field_value(
            canonical_data.get("vendor_name"), field_confidence.get("vendor_name")
        )
        invoice.vendor_id = self._get_field_value(
            canonical_data.get("vendor_id"), field_confidence.get("vendor_id")
        )
        invoice.vendor_phone = self._get_field_value(
            canonical_data.get("vendor_phone"), field_confidence.get("vendor_phone")
        )
        invoice.vendor_fax = self._get_field_value(
            canonical_data.get("vendor_fax"), field_confidence.get("vendor_fax")
        )
        invoice.vendor_email = self._get_field_value(
            canonical_data.get("vendor_email"), field_confidence.get("vendor_email")
        )
        invoice.vendor_website = self._get_field_value(
            canonical_data.get("vendor_website"), field_confidence.get("vendor_website")
        )
        vendor_address = canonical_data.get("vendor_address")
        if vendor_address:
            invoice.vendor_address = self._map_address(vendor_address)
        
        # Vendor tax IDs
        invoice.business_number = self._get_field_value(
            canonical_data.get("business_number"), field_confidence.get("business_number")
        )
        invoice.gst_number = self._get_field_value(
            canonical_data.get("gst_number"), field_confidence.get("gst_number")
        )
        invoice.qst_number = self._get_field_value(
            canonical_data.get("qst_number"), field_confidence.get("qst_number")
        )
        invoice.pst_number = self._get_field_value(
            canonical_data.get("pst_number"), field_confidence.get("pst_number")
        )
        
        # Customer information
        invoice.customer_name = self._get_field_value(
            canonical_data.get("customer_name"), field_confidence.get("customer_name")
        )
        invoice.customer_id = self._get_field_value(
            canonical_data.get("customer_id"), field_confidence.get("customer_id")
        )
        invoice.customer_phone = self._get_field_value(
            canonical_data.get("customer_phone"), field_confidence.get("customer_phone")
        )
        invoice.customer_email = self._get_field_value(
            canonical_data.get("customer_email"), field_confidence.get("customer_email")
        )
        invoice.customer_fax = self._get_field_value(
            canonical_data.get("customer_fax"), field_confidence.get("customer_fax")
        )
        invoice.entity = self._get_field_value(
            canonical_data.get("entity"), field_confidence.get("entity")
        )
        customer_address = canonical_data.get("bill_to_address")
        if customer_address:
            invoice.bill_to_address = self._map_address(customer_address)
        
        # Contract and PO
        invoice.contract_id = self._get_field_value(
            canonical_data.get("contract_id"), field_confidence.get("contract_id")
        )
        invoice.standing_offer_number = self._get_field_value(
            canonical_data.get("standing_offer_number"), field_confidence.get("standing_offer_number")
        )
        invoice.po_number = self._get_field_value(
            canonical_data.get("po_number"), field_confidence.get("po_number")
        )
        if invoice.po_number is None:
            invoice.po_number = doc_intelligence_data.get("purchase_order") or doc_intelligence_data.get("PurchaseOrder")
        
        # Period covered
        invoice.period_start = self._parse_date(
            canonical_data.get("period_start"), field_confidence.get("period_start")
        )
        invoice.period_end = self._parse_date(
            canonical_data.get("period_end"), field_confidence.get("period_end")
        )
        
        # Financial fields
        invoice.subtotal = self._parse_decimal(
            canonical_data.get("subtotal"), field_confidence.get("subtotal")
        )
        invoice.discount_amount = self._parse_decimal(
            canonical_data.get("discount_amount"), field_confidence.get("discount_amount")
        )
        invoice.shipping_amount = self._parse_decimal(
            canonical_data.get("shipping_amount"), field_confidence.get("shipping_amount")
        )
        invoice.handling_fee = self._parse_decimal(
            canonical_data.get("handling_fee"), field_confidence.get("handling_fee")
        )
        invoice.deposit_amount = self._parse_decimal(
            canonical_data.get("deposit_amount"), field_confidence.get("deposit_amount")
        )
        
        # Canadian tax fields
        invoice.gst_amount = self._parse_decimal(
            canonical_data.get("gst_amount"), field_confidence.get("gst_amount")
        )
        invoice.gst_rate = self._parse_decimal(
            canonical_data.get("gst_rate"), field_confidence.get("gst_rate")
        )
        invoice.hst_amount = self._parse_decimal(
            canonical_data.get("hst_amount"), field_confidence.get("hst_amount")
        )
        invoice.hst_rate = self._parse_decimal(
            canonical_data.get("hst_rate"), field_confidence.get("hst_rate")
        )
        invoice.qst_amount = self._parse_decimal(
            canonical_data.get("qst_amount"), field_confidence.get("qst_amount")
        )
        invoice.qst_rate = self._parse_decimal(
            canonical_data.get("qst_rate"), field_confidence.get("qst_rate")
        )
        invoice.pst_amount = self._parse_decimal(
            canonical_data.get("pst_amount"), field_confidence.get("pst_amount")
        )
        invoice.pst_rate = self._parse_decimal(
            canonical_data.get("pst_rate"), field_confidence.get("pst_rate")
        )
        
        invoice.tax_amount = self._parse_decimal(
            canonical_data.get("tax_amount"), field_confidence.get("tax_amount")
        )
        di_total_raw = (
            canonical_data.get("total_amount")
            or doc_intelligence_data.get("InvoiceTotal")
            or doc_intelligence_data.get("invoice_total")
        )
        invoice.total_amount = self._parse_decimal(
            di_total_raw, field_confidence.get("total_amount")
        )
        
        # Tax breakdown (by tax type)
        invoice.tax_breakdown = self._extract_tax_breakdown(canonical_data)
        
        # Currency
        currency = canonical_data.get("currency")
        invoice.currency = self._normalize_currency(currency) if currency else "CAD"
        
        # Payment information
        invoice.payment_terms = self._get_field_value(
            canonical_data.get("payment_terms"), field_confidence.get("payment_terms")
        )
        invoice.payment_method = self._get_field_value(
            canonical_data.get("payment_method"), field_confidence.get("payment_method")
        )
        invoice.payment_due_upon = self._get_field_value(
            canonical_data.get("payment_due_upon"), field_confidence.get("payment_due_upon")
        )
        invoice.tax_registration_number = self._get_field_value(
            canonical_data.get("tax_registration_number"), field_confidence.get("tax_registration_number")
        )
        
        # Line items
        items_data = canonical_data.get("items", [])
        invoice.line_items = self._extract_line_items(items_data, field_confidence)
        # Derive totals only if DI did not provide them
        if invoice.line_items and di_total_raw is None:
            line_sum = sum([item.amount or Decimal("0.00") for item in invoice.line_items], Decimal("0.00"))
            if invoice.subtotal is None:
                invoice.subtotal = line_sum
            if invoice.total_amount is None and invoice.subtotal is not None:
                invoice.total_amount = invoice.subtotal + (invoice.tax_amount or Decimal("0.00"))
            if invoice.tax_amount is None and invoice.total_amount is not None and invoice.subtotal is not None:
                invoice.tax_amount = invoice.total_amount - invoice.subtotal
        invoice.tax_registration_number = self._get_field_value(
            canonical_data.get("tax_registration_number"), field_confidence.get("tax_registration_number")
        )
        invoice.vendor_phone = self._get_field_value(
            canonical_data.get("vendor_phone"), field_confidence.get("vendor_phone")
        )
        remit_addr = canonical_data.get("remit_to_address")
        if remit_addr:
            invoice.remit_to_address = self._map_address(remit_addr)
        invoice.remit_to_name = self._get_field_value(
            canonical_data.get("remit_to_name"), field_confidence.get("remit_to_name")
        )

        # If a field failed to extract but DI still emitted a confidence score,
        # drop the confidence to 0 so the UI doesn't show a misleading high score.
        for attr, key in [
            ("invoice_number", "invoice_number"),
            ("invoice_date", "invoice_date"),
            ("vendor_name", "vendor_name"),
            ("total_amount", "total_amount"),
        ]:
            if getattr(invoice, attr) in (None, "", {}):
                if invoice.field_confidence is None:
                    invoice.field_confidence = {}
                if key in invoice.field_confidence:
                    invoice.field_confidence[key] = 0.0
        
        # Calculate overall confidence
        invoice.extraction_confidence = self._calculate_overall_confidence(field_confidence)
        invoice.extraction_timestamp = datetime.utcnow()
        
        # Detect and extract subtype
        invoice.invoice_subtype, invoice.extensions = self._detect_and_extract_subtype(
            canonical_data, invoice, invoice_text
        )
        
        return invoice
    
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
        
        # handle objects with amount/value/text
        if hasattr(decimal_value, "amount"):
            return self._parse_decimal(getattr(decimal_value, "amount"), confidence)
        if hasattr(decimal_value, "value"):
            return self._parse_decimal(getattr(decimal_value, "value"), confidence)
        if hasattr(decimal_value, "text"):
            return self._parse_decimal(getattr(decimal_value, "text"), confidence)

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
            
            # Get item confidence (default to 0.85 if missing/None)
            raw_conf = item_data.get("confidence")
            try:
                item_conf = float(raw_conf) if raw_conf is not None else 0.85
            except Exception:
                item_conf = 0.85
            desc_val = self._get_field_value(item_data.get("description")) or ""
            desc_lower = desc_val.lower()

            # Skip tax lines; accumulate into tax_line_total instead of showing as line item
            if "tax" in desc_lower:
                amt = self._parse_decimal(item_data.get("amount"))
                if amt:
                    tax_line_total += amt
                continue

            # Taxes: merge PST/QST into a single pst_amount; compute tax_amount/combined_tax if missing
            gst_amt = self._parse_decimal(item_data.get("gst_amount") or item_data.get("gst"))
            pst_qst_raw = item_data.get("pst_amount") or item_data.get("pst") or item_data.get("qst_amount") or item_data.get("qst")
            pst_amt = self._parse_decimal(pst_qst_raw)
            combined_tax = self._parse_decimal(item_data.get("combined_tax"))
            if combined_tax is None and (gst_amt is not None or pst_amt is not None):
                combined_tax = (gst_amt or Decimal("0")) + (pst_amt or Decimal("0"))
            tax_amount = self._parse_decimal(item_data.get("tax"))
            if tax_amount is None:
                tax_amount = combined_tax

            # Acceptance percentage per line item; apply to computed line total if provided and non-zero
            acc_pct = self._parse_decimal(item_data.get("acceptance_percentage"))
            has_acc = acc_pct is not None and acc_pct != 0

            quantity_val = self._parse_decimal(item_data.get("quantity"))
            unit_price_val = self._parse_decimal(item_data.get("unit_price"))
            amount_val = self._parse_decimal(item_data.get("amount")) or Decimal("0.00")
            if has_acc:
                base_subtotal = amount_val
                if quantity_val is not None and unit_price_val is not None:
                    base_subtotal = quantity_val * unit_price_val
                amount_val = base_subtotal * (acc_pct / Decimal("100"))

            line_item = LineItem(
                line_number=idx,
                description=desc_val,
                quantity=quantity_val,
                unit_price=unit_price_val,
                amount=amount_val,
                confidence=item_conf,
                unit_of_measure=item_data.get("unit"),
                tax_rate=self._parse_decimal(item_data.get("tax_rate")),
                tax_amount=tax_amount,
                gst_amount=gst_amt,
                pst_amount=pst_amt,
                qst_amount=None,
                combined_tax=combined_tax,
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
            "invoice_number",
            "invoice_date",
            "total_amount",
            "vendor_name",
            "subtotal",
            "tax_amount",
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

    def _extract_field_confidence(self, di_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Map DI confidence keys to canonical Invoice field names.
        If DI provides no confidence, return {} (do not default).
        """
        di_fc = (di_data or {}).get("field_confidence") or {}
        if not isinstance(di_fc, dict) or not di_fc:
            return {}

        di_to_canon = {
            # DI (prebuilt invoice) field names -> canonical invoice fields
            "InvoiceId": "invoice_number",
            "InvoiceDate": "invoice_date",
            "DueDate": "due_date",
            "VendorName": "vendor_name",
            "VendorPhoneNumber": "vendor_phone",
            "VendorPhone": "vendor_phone",
            "VendorAddress": "vendor_address",
            "CustomerName": "customer_name",
            "CustomerId": "customer_id",
            "CustomerAddress": "bill_to_address",
            "BillToAddress": "bill_to_address",
            "RemitToAddress": "remit_to_address",
            "RemittanceAddress": "remit_to_address",
            "SubTotal": "subtotal",
            "TotalTax": "tax_amount",
            "InvoiceTotal": "total_amount",
            "PurchaseOrder": "po_number",
            "PaymentTerm": "payment_terms",
            "ContractId": "standing_offer_number",
            "StandingOfferNumber": "standing_offer_number",
            "CurrencyCode": "currency",
            "Currency": "currency",
        }

        # Legacy/normalized snake-case keys seen in the pipeline
        legacy_to_canon = {
            "invoice_id": "invoice_number",
            "invoice_total": "total_amount",
            "total_tax": "tax_amount",
            "purchase_order": "po_number",
            "payment_term": "payment_terms",
        }

        canonical_allowlist = {
            "invoice_number", "invoice_id", "invoice_date", "due_date",
            "vendor_name", "vendor_id", "vendor_phone", "vendor_address",
            "customer_name", "customer_id", "bill_to_address", "remit_to_address",
            "subtotal", "tax_amount", "total_amount",
            "po_number", "payment_terms", "currency",
            "standing_offer_number", "contract_id",
        }

        out: Dict[str, float] = {}
        for k, v in di_fc.items():
            canon = di_to_canon.get(k) or legacy_to_canon.get(k) or (k if k in canonical_allowlist else None)
            if not canon:
                continue
            try:
                out[canon] = float(v)
                if canon == "invoice_number":
                    out["invoice_id"] = float(v)
            except Exception:
                # ignore non-numeric confidence values
                pass
        return out

