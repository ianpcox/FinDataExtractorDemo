"""Simplified extraction service"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging

from .document_intelligence_client import DocumentIntelligenceClient
from src.ingestion.file_handler import FileHandler
from src.models.invoice import Invoice

logger = logging.getLogger(__name__)


class ExtractionService:
    """Simplified service for extracting data from invoice PDFs"""
    
    def __init__(
        self,
        doc_intelligence_client: Optional[DocumentIntelligenceClient] = None,
        file_handler: Optional[FileHandler] = None
    ):
        """
        Initialize extraction service
        
        Args:
            doc_intelligence_client: DocumentIntelligenceClient instance
            file_handler: FileHandler instance
        """
        self.doc_intelligence_client = (
            doc_intelligence_client or DocumentIntelligenceClient()
        )
        self.file_handler = file_handler or FileHandler()
    
    async def extract_invoice(
        self,
        invoice_id: str,
        file_identifier: str,
        file_name: str,
        upload_date: datetime
    ) -> Dict[str, Any]:
        """
        Extract data from an invoice PDF
        
        Args:
            invoice_id: Unique invoice ID
            file_identifier: File path (local) or blob name (Azure)
            file_name: Original file name
            upload_date: Upload timestamp
            
        Returns:
            Dictionary with extraction result
        """
        errors = []
        
        try:
            logger.info(f"Starting extraction for invoice: {invoice_id}")
            
            # Step 1: Download PDF
            logger.info(f"Downloading PDF: {file_identifier}")
            file_content = self.file_handler.download_file(file_identifier)
            
            if not file_content:
                errors.append("Failed to download file")
                return {
                    "invoice_id": invoice_id,
                    "status": "error",
                    "errors": errors
                }
            
            # Step 2: Analyze with Document Intelligence
            logger.info(f"Analyzing invoice with Document Intelligence: {invoice_id}")
            doc_intelligence_data = self.doc_intelligence_client.analyze_invoice(
                file_content
            )
            
            if not doc_intelligence_data or doc_intelligence_data.get("error"):
                errors.append(
                    doc_intelligence_data.get("error", "Document Intelligence analysis failed")
                )
                return {
                    "invoice_id": invoice_id,
                    "status": "extraction_failed",
                    "errors": errors
                }
            
            # Step 3: Map to Invoice model
            logger.info(f"Mapping extracted data to Invoice model: {invoice_id}")
            file_path = self.file_handler.get_file_path(file_identifier)
            
            invoice = self._map_to_invoice(
                doc_intelligence_data,
                file_path,
                file_name,
                upload_date
            )
            invoice.id = invoice_id
            
            # Calculate confidence (simplified)
            confidence = 0.85  # Default confidence
            
            result = {
                "invoice_id": invoice_id,
                "status": "extracted",
                "invoice": invoice.dict(),
                "confidence": confidence,
                "extraction_timestamp": datetime.utcnow(),
                "errors": []
            }
            
            logger.info(f"Extraction completed successfully for invoice: {invoice_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting invoice {invoice_id}: {e}", exc_info=True)
            errors.append(str(e))
            return {
                "invoice_id": invoice_id,
                "status": "error",
                "errors": errors
            }
    
    def _map_to_invoice(
        self,
        doc_data: Dict[str, Any],
        file_path: str,
        file_name: str,
        upload_date: datetime
    ) -> Invoice:
        """Map Document Intelligence data to Invoice model"""
        from src.models.invoice import Address, LineItem
        from decimal import Decimal
        
        invoice = Invoice(
            file_path=file_path,
            file_name=file_name,
            upload_date=upload_date,
            status="extracted"
        )
        
        # Map basic fields
        invoice.invoice_number = doc_data.get("invoice_id")
        invoice.invoice_date = self._parse_date(doc_data.get("invoice_date"))
        invoice.due_date = self._parse_date(doc_data.get("due_date"))
        invoice.vendor_name = doc_data.get("vendor_name")
        invoice.customer_name = doc_data.get("customer_name")
        invoice.customer_id = doc_data.get("customer_id")
        invoice.payment_terms = doc_data.get("payment_term")
        invoice.po_number = doc_data.get("purchase_order")
        
        # Map addresses
        vendor_addr = doc_data.get("vendor_address")
        if vendor_addr:
            invoice.vendor_address = Address(**vendor_addr)
        
        # Map financial fields
        invoice.subtotal = self._parse_decimal(doc_data.get("subtotal"))
        invoice.tax_amount = self._parse_decimal(doc_data.get("total_tax"))
        invoice.total_amount = self._parse_decimal(doc_data.get("invoice_total"))
        
        # Map line items
        items_data = doc_data.get("items", [])
        invoice.line_items = [
            LineItem(
                line_number=i + 1,
                description=item.get("description", ""),
                quantity=self._parse_decimal(item.get("quantity")),
                unit_price=self._parse_decimal(item.get("unit_price")),
                amount=self._parse_decimal(item.get("amount")),
            )
            for i, item in enumerate(items_data)
        ]
        
        invoice.extraction_timestamp = datetime.utcnow()
        invoice.extraction_confidence = 0.85  # Default
        
        return invoice
    
    def _parse_date(self, value) -> Optional[date]:
        """Parse date from various formats"""
        if not value:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        # Try to parse string
        try:
            from dateutil.parser import parse
            dt = parse(str(value))
            return dt.date() if isinstance(dt, datetime) else dt
        except:
            return None
    
    def _parse_decimal(self, value) -> Optional[Decimal]:
        """Parse decimal from various formats"""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except:
            return None

