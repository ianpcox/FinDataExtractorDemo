"""Simplified Azure Document Intelligence client"""

from typing import Optional, Dict, Any
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError
import logging

from src.config import settings

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
        Analyze invoice PDF using Document Intelligence
        
        Args:
            file_content: PDF file content as bytes
            
        Returns:
            Dictionary with extracted invoice data
        """
        try:
            from io import BytesIO
            
            # Analyze document
            poller = self.client.begin_analyze_document(
                model_id=self.model_id,
                document=BytesIO(file_content)
            )
            result = poller.result()
            
            # Extract invoice data
            invoice_data = self._extract_invoice_fields(result)
            
            logger.info("Document Intelligence analysis completed successfully")
            return invoice_data
            
        except AzureError as e:
            logger.error(f"Azure Document Intelligence error: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Error analyzing invoice: {e}")
            return {"error": str(e)}
    
    def _extract_invoice_fields(self, result) -> Dict[str, Any]:
        """Extract invoice fields from Document Intelligence result"""
        invoice_data = {}
        
        # Get document fields
        if hasattr(result, 'documents') and result.documents:
            doc = result.documents[0]
            fields = doc.fields
            
            # Extract basic fields
            invoice_data["invoice_id"] = self._get_field_value(fields.get("InvoiceId"))
            invoice_data["invoice_date"] = self._get_field_value(fields.get("InvoiceDate"))
            invoice_data["due_date"] = self._get_field_value(fields.get("DueDate"))
            invoice_data["vendor_name"] = self._get_field_value(fields.get("VendorName"))
            invoice_data["vendor_address"] = self._get_address(fields.get("VendorAddress"))
            invoice_data["customer_name"] = self._get_field_value(fields.get("CustomerName"))
            invoice_data["customer_id"] = self._get_field_value(fields.get("CustomerId"))
            invoice_data["customer_address"] = self._get_address(fields.get("BillingAddress"))
            invoice_data["subtotal"] = self._get_field_value(fields.get("SubTotal"))
            invoice_data["total_tax"] = self._get_field_value(fields.get("TotalTax"))
            invoice_data["invoice_total"] = self._get_field_value(fields.get("InvoiceTotal"))
            invoice_data["payment_term"] = self._get_field_value(fields.get("PaymentTerms"))
            invoice_data["purchase_order"] = self._get_field_value(fields.get("PurchaseOrder"))
            
            # Extract line items
            items = []
            if fields.get("Items"):
                for item in fields.get("Items").value:
                    item_data = {
                        "description": self._get_field_value(item.get("Description")),
                        "quantity": self._get_field_value(item.get("Quantity")),
                        "unit_price": self._get_field_value(item.get("UnitPrice")),
                        "amount": self._get_field_value(item.get("Amount")),
                    }
                    items.append(item_data)
            invoice_data["items"] = items
        
        return invoice_data
    
    def _get_field_value(self, field) -> Optional[Any]:
        """Extract value from Document Intelligence field"""
        if field is None:
            return None
        if hasattr(field, 'value'):
            return field.value
        return field
    
    def _get_address(self, address_field) -> Optional[Dict[str, Any]]:
        """Extract address from Document Intelligence field"""
        if not address_field or not hasattr(address_field, 'value'):
            return None
        
        address = address_field.value
        return {
            "street": getattr(address, 'street_address', None),
            "city": getattr(address, 'city', None),
            "state": getattr(address, 'state', None),
            "postal_code": getattr(address, 'postal_code', None),
            "country": getattr(address, 'country_region', None),
        }

