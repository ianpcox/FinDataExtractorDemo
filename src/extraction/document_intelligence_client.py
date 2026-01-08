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
            "bill_to_address": self._get_address(fields, "CustomerAddress") or self._get_address(fields, "BillToAddress"),
            
            # Remit-To Fields
            "remit_to_address": self._get_address(fields, "RemitToAddress") or self._get_address(fields, "RemittanceAddress"),
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
        if isinstance(address_value, dict):
            return {
                "street_address": address_value.get("streetAddress"),
                "city": address_value.get("city"),
                "state": address_value.get("state"),
                "postal_code": address_value.get("postalCode"),
                "country_region": address_value.get("countryRegion"),
                "house_number": address_value.get("houseNumber"),
                "road": address_value.get("road"),
            }
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
                confidences[field_name] = field.confidence or 0.0
        return confidences

