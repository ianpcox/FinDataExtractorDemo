"""Simplified Azure Document Intelligence client"""

from typing import Optional, Dict, Any
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError, HttpResponseError
import logging

from src.config import settings
from src.utils.retry import async_retry_with_backoff, RetryableError

logger = logging.getLogger(__name__)


class DocumentIntelligenceClient:
    """Simplified client for Azure Document Intelligence"""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize Document Intelligence client
        
        Args:
            endpoint: Document Intelligence endpoint URL
            api_key: API key for authentication
        """
        endpoint = endpoint or settings.AZURE_FORM_RECOGNIZER_ENDPOINT
        api_key = api_key or settings.AZURE_FORM_RECOGNIZER_KEY
        
        if not endpoint:
            raise ValueError(
                "Document Intelligence endpoint is required. "
                "Set AZURE_FORM_RECOGNIZER_ENDPOINT environment variable."
            )
        
        if not api_key:
            raise ValueError(
                "Document Intelligence API key is required. "
                "Set AZURE_FORM_RECOGNIZER_KEY environment variable."
            )
        
        credential = AzureKeyCredential(api_key)
        self.client = DocumentAnalysisClient(
            endpoint=endpoint,
            credential=credential
        )
        
        self.model_id = settings.AZURE_FORM_RECOGNIZER_MODEL
        
        logger.info(
            f"Document Intelligence client initialized: {endpoint}, model: {self.model_id}"
        )
    
    def analyze_invoice(self, file_content: bytes) -> Dict[str, Any]:
        """
        Analyze invoice PDF using Document Intelligence with retry logic
        
        Args:
            file_content: PDF file content as bytes
            
        Returns:
            Dictionary with extracted invoice data
        """
        return self._analyze_with_retry(file_content)
    
    def _analyze_with_retry(self, file_content: bytes, attempt: int = 0) -> Dict[str, Any]:
        """Internal method with retry logic for Document Intelligence calls"""
        max_retries = 3
        initial_delay = 1.0
        max_delay = 60.0
        exponential_base = 2.0
        
        try:
            # Analyze document - Document Intelligence handles bytes directly
            poller = self.client.begin_analyze_document(
                model_id=self.model_id,
                document=file_content
            )
            result = poller.result()
            
            # Extract invoice data
            invoice_data = self._extract_invoice_fields(result)
            # include raw content for downstream subtype/LLM context if available
            try:
                if hasattr(result, "content") and result.content:
                    invoice_data["content"] = result.content
                elif hasattr(result, "pages") and result.pages:
                    page_text = " ".join([p.content for p in result.pages if getattr(p, "content", None)])
                    if page_text:
                        invoice_data["content"] = page_text
            except Exception:
                pass
            
            logger.info("Document Intelligence analysis completed successfully")
            return invoice_data
            
        except HttpResponseError as e:
            # Check if it's a retryable error (429 rate limit, 503 service unavailable)
            if e.status_code in [429, 503] and attempt < max_retries:
                delay = min(initial_delay * (exponential_base ** attempt), max_delay)
                
                retry_after = None
                if e.status_code == 429:
                    # Try to get Retry-After header if available
                    try:
                        retry_after = int(e.response.headers.get('Retry-After', delay))
                        delay = max(delay, retry_after)
                    except (ValueError, AttributeError):
                        pass
                
                logger.warning(
                    f"Document Intelligence rate limit/service error (status {e.status_code}), "
                    f"attempt {attempt + 1}/{max_retries}, backing off for {delay:.2f}s"
                )
                
                import time
                time.sleep(delay)
                return self._analyze_with_retry(file_content, attempt + 1)
            
            logger.error(f"Azure Document Intelligence HTTP error: {e}", exc_info=True)
            return {"error": str(e), "confidence": 0.0}
            
        except AzureError as e:
            # Other Azure errors - retry if not max attempts
            if attempt < max_retries:
                delay = min(initial_delay * (exponential_base ** attempt), max_delay)
                logger.warning(
                    f"Azure error: {e}, attempt {attempt + 1}/{max_retries}, "
                    f"retrying in {delay:.2f}s"
                )
                
                import time
                time.sleep(delay)
                return self._analyze_with_retry(file_content, attempt + 1)
            
            logger.error(f"Azure Document Intelligence error: {e}", exc_info=True)
            return {"error": str(e), "confidence": 0.0}
            
        except Exception as e:
            logger.error(f"Error analyzing invoice: {e}", exc_info=True)
            return {"error": str(e), "confidence": 0.0}
    
    def _extract_invoice_fields(self, result) -> Dict[str, Any]:
        """Extract invoice fields from Document Intelligence result with field-level confidence"""
        if not result.documents:
            return {
                "confidence": 0.0,
                "error": "No invoice document found in result"
            }
        
        # Get first document (invoice)
        invoice_doc = result.documents[0]
        fields = invoice_doc.fields
        
        # Extract fields with confidence scores - Using CANONICAL field names
        # Organized by category for maintainability
        invoice_data = {
            "confidence": invoice_doc.confidence or 0.0,
            
            # Header Fields
            "invoice_number": self._get_field_value(fields, "InvoiceId"),
            "invoice_date": self._get_field_value(fields, "InvoiceDate"),
            "due_date": self._get_field_value(fields, "DueDate"),
            "invoice_type": self._get_field_value(fields, "InvoiceType"),
            "reference_number": self._get_field_value(fields, "ReferenceNumber"),
            "shipping_date": self._get_field_value(fields, "ShippingDate"),
            "delivery_date": self._get_field_value(fields, "DeliveryDate"),
            
            # Vendor Fields
            "vendor_name": self._get_field_value(fields, "VendorName"),
            "vendor_id": self._get_field_value(fields, "VendorId"),
            "vendor_phone": self._get_field_value(fields, "VendorPhoneNumber") or self._get_field_value(fields, "VendorPhone"),
            "vendor_fax": self._get_field_value(fields, "VendorFax") or self._get_field_value(fields, "VendorFaxNumber"),
            "vendor_email": self._get_field_value(fields, "VendorEmail"),
            "vendor_website": self._get_field_value(fields, "VendorWebsite"),
            "vendor_address": self._get_address(fields, "VendorAddress"),
            
            # Vendor Tax ID Fields
            "business_number": self._get_field_value(fields, "BusinessNumber"),
            "gst_number": self._get_field_value(fields, "GSTNumber"),
            "qst_number": self._get_field_value(fields, "QSTNumber"),
            "pst_number": self._get_field_value(fields, "PSTNumber"),
            
            # Customer Fields
            "customer_name": self._get_field_value(fields, "CustomerName"),
            "customer_id": self._get_field_value(fields, "CustomerId"),
            "customer_phone": self._get_field_value(fields, "CustomerPhone"),
            "customer_email": self._get_field_value(fields, "CustomerEmail"),
            "customer_fax": self._get_field_value(fields, "CustomerFax"),
            "bill_to_address": self._get_address(fields, "BillingAddress") or self._get_address(fields, "CustomerAddress") or self._get_address(fields, "BillToAddress"),
            
            # Remit-To Fields
            "remit_to_address": self._get_address(fields, "RemittanceAddress") or self._get_address(fields, "RemitToAddress"),
            "remit_to_name": self._get_field_value(fields, "RemitToName"),
            
            # Contract Fields
            "entity": self._get_field_value(fields, "Entity"),
            "contract_id": self._get_field_value(fields, "ContractId"),
            "standing_offer_number": self._get_field_value(fields, "StandingOfferNumber"),
            "po_number": self._get_field_value(fields, "PurchaseOrder") or self._get_field_value(fields, "PONumber"),
            
            # Date Fields
            "period_start": self._get_field_value(fields, "ServiceStartDate"),
            "period_end": self._get_field_value(fields, "ServiceEndDate"),
            
            # Financial Fields
            "subtotal": self._get_field_value(fields, "SubTotal"),
            "discount_amount": self._get_field_value(fields, "DiscountAmount"),
            "shipping_amount": self._get_field_value(fields, "ShippingAmount"),
            "handling_fee": self._get_field_value(fields, "HandlingFee"),
            "deposit_amount": self._get_field_value(fields, "DepositAmount"),
            
            # Canadian Tax Fields
            "gst_amount": self._get_field_value(fields, "GSTAmount"),
            "gst_rate": self._get_field_value(fields, "GSTRate"),
            "hst_amount": self._get_field_value(fields, "HSTAmount"),
            "hst_rate": self._get_field_value(fields, "HSTRate"),
            "qst_amount": self._get_field_value(fields, "QSTAmount"),
            "qst_rate": self._get_field_value(fields, "QSTRate"),
            "pst_amount": self._get_field_value(fields, "PSTAmount"),
            "pst_rate": self._get_field_value(fields, "PSTRate"),
            
            # Total Fields
            "tax_amount": self._get_field_value(fields, "TotalTax"),
            "total_amount": self._get_field_value(fields, "InvoiceTotal"),
            "currency": self._get_field_value(fields, "CurrencyCode") or self._get_field_value(fields, "Currency"),
            
            # Payment Fields
            "payment_terms": self._get_field_value(fields, "PaymentTerm") or self._get_field_value(fields, "PaymentTerms"),
            "payment_method": self._get_field_value(fields, "PaymentMethod"),
            "payment_due_upon": self._get_field_value(fields, "PaymentDueUpon"),
            "tax_registration_number": self._get_field_value(fields, "TaxRegistrationNumber") or self._get_field_value(fields, "SalesTaxNumber"),
            
            # Line Items
            "items": self._extract_items(fields.get("Items")),
            
            # Field Confidence Scores
            "field_confidence": self._extract_field_confidences(fields)
        }
        
        return invoice_data
    
    def _get_field_value(self, fields: Dict, field_name: str) -> Optional[Any]:
        """Get field value with error handling"""
        field = fields.get(field_name)
        if field and hasattr(field, 'value'):
            return field.value
        return None
    
    def _get_address(self, fields: Dict, field_name: str) -> Optional[Dict]:
        """Extract address field"""
        field = fields.get(field_name)
        if not field or not hasattr(field, 'value'):
            return None
        
        address_value = field.value
        if not address_value:
            return None
        
        # Handle AddressValue objects from Azure SDK
        # AddressValue has attributes: house_number, po_box, road, city, state, postal_code,
        # country_region, street_address, unit, city_district, state_district, suburb, house, level
        if hasattr(address_value, 'street_address') or hasattr(address_value, 'city'):
            # This is an AddressValue object from Azure SDK
            address_dict = {
                "street_address": getattr(address_value, 'street_address', None),
                "city": getattr(address_value, 'city', None),
                "state": getattr(address_value, 'state', None),
                "postal_code": getattr(address_value, 'postal_code', None),
                "country_region": getattr(address_value, 'country_region', None),
                "house_number": getattr(address_value, 'house_number', None),
                "road": getattr(address_value, 'road', None),
                "po_box": getattr(address_value, 'po_box', None),
                "unit": getattr(address_value, 'unit', None),
                "level": getattr(address_value, 'level', None),
                "province": getattr(address_value, 'state', None),  # Use state as province
                "country": getattr(address_value, 'country_region', None),
            }
            
            # Build street address from components if street_address is not available
            if not address_dict["street_address"]:
                street_parts = []
                if address_dict["house_number"]:
                    street_parts.append(str(address_dict["house_number"]))
                if address_dict["road"]:
                    street_parts.append(address_dict["road"])
                if address_dict["unit"]:
                    street_parts.append(f"Unit {address_dict['unit']}")
                if address_dict["level"]:
                    street_parts.append(f"{address_dict['level']}")
                if street_parts:
                    address_dict["street_address"] = " ".join(street_parts)
            
            # Use po_box as street_address if no street_address
            if not address_dict["street_address"] and address_dict["po_box"]:
                address_dict["street_address"] = address_dict["po_box"]
            
            # Only return address dict if it has at least one non-empty value
            if any(v for v in address_dict.values() if v):
                return address_dict
            return None
        
        # Handle dict format (structured address)
        if isinstance(address_value, dict):
            address_dict = {
                "street_address": address_value.get("streetAddress") or address_value.get("street_address"),
                "city": address_value.get("city"),
                "state": address_value.get("state"),
                "postal_code": address_value.get("postalCode") or address_value.get("postal_code"),
                "country_region": address_value.get("countryRegion") or address_value.get("country_region"),
                "house_number": address_value.get("houseNumber") or address_value.get("house_number"),
                "road": address_value.get("road"),
                "province": address_value.get("province") or address_value.get("state"),
                "country": address_value.get("country") or address_value.get("countryRegion") or address_value.get("country_region"),
            }
            
            # Only return address dict if it has at least one non-empty value
            if any(v for v in address_dict.values() if v):
                return address_dict
            return None
        
        # Handle string format (try to parse)
        if isinstance(address_value, str) and address_value.strip():
            # Return as a simple dict with street_address containing the full string
            # The FieldExtractor can parse it further if needed
            return {"street_address": address_value.strip()}
        
        return None
    
    def _extract_items(self, items_field) -> list:
        """Extract line items from invoice"""
        items = []
        
        if not items_field or not hasattr(items_field, 'value'):
            return items
        
        for item in items_field.value:
            if hasattr(item, 'value') and isinstance(item.value, dict):
                item_dict = item.value
                items.append({
                    "amount": self._get_nested_value(item_dict, "Amount"),
                    "date": self._get_nested_value(item_dict, "Date"),
                    "description": self._get_nested_value(item_dict, "Description"),
                    "product_code": self._get_nested_value(item_dict, "ProductCode"),
                    "quantity": self._get_nested_value(item_dict, "Quantity"),
                    "tax": self._get_nested_value(item_dict, "Tax"),
                    "unit": self._get_nested_value(item_dict, "Unit"),
                    "unit_price": self._get_nested_value(item_dict, "UnitPrice"),
                    "confidence": item.confidence if hasattr(item, 'confidence') else 0.0
                })
        
        return items
    
    def _get_nested_value(self, dict_obj: Dict, key: str) -> Optional[Any]:
        """Get value from nested dictionary"""
        field = dict_obj.get(key)
        if field and hasattr(field, 'value'):
            return field.value
        return None
    
    def _extract_field_confidences(self, fields: Dict) -> Dict[str, float]:
        """Extract confidence scores for each field"""
        confidences = {}
        for field_name, field in fields.items():
            if hasattr(field, 'confidence'):
                # For address fields, only include confidence if the address has actual content
                address_field_names = (
                    "VendorAddress", "CustomerAddress", "BillToAddress", "RemitToAddress", 
                    "RemittanceAddress", "BillingAddress", "ShippingAddress"
                )
                if field_name in address_field_names:
                    # Check if address field has a value with content
                    if hasattr(field, 'value') and field.value:
                        has_content = False
                        
                        # Handle AddressValue objects from Azure SDK
                        if hasattr(field.value, 'street_address') or hasattr(field.value, 'city'):
                            # AddressValue object - check if it has any non-empty attributes
                            attrs_to_check = ['street_address', 'city', 'state', 'postal_code', 
                                             'country_region', 'house_number', 'road', 'po_box']
                            has_content = any(
                                getattr(field.value, attr, None) 
                                for attr in attrs_to_check
                                if getattr(field.value, attr, None) is not None
                                and (not isinstance(getattr(field.value, attr), str) or getattr(field.value, attr).strip())
                            )
                        elif isinstance(field.value, dict):
                            # Check if dict has any non-empty values
                            has_content = any(v for v in field.value.values() if v)
                        elif isinstance(field.value, str) and field.value.strip():
                            has_content = True
                        
                        if has_content:
                            confidences[field_name] = field.confidence or 0.0
                    # If address field is empty, don't include confidence (or set to 0)
                else:
                    # For non-address fields, include confidence if field has a value
                    if hasattr(field, 'value') and field.value is not None:
                        confidences[field_name] = field.confidence or 0.0
        return confidences

