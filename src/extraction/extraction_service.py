"""Simplified extraction service with field extractor and database integration"""

from typing import Optional, Dict, Any, List
from datetime import datetime, date
from decimal import Decimal
import logging
import json

from sqlalchemy.ext.asyncio import AsyncSession

from .document_intelligence_client import DocumentIntelligenceClient
from .field_extractor import FieldExtractor
from src.ingestion.file_handler import FileHandler
from src.models.invoice import Invoice
from src.services.db_service import DatabaseService
from src.config import settings
try:
    from openai import AzureOpenAI
except ImportError:
    AzureOpenAI = None

logger = logging.getLogger(__name__)


class ExtractionService:
    """Service for extracting data from invoice PDFs"""
    
    def __init__(
        self,
        doc_intelligence_client: Optional[DocumentIntelligenceClient] = None,
        file_handler: Optional[FileHandler] = None,
        field_extractor: Optional[FieldExtractor] = None
    ):
        """
        Initialize extraction service
        
        Args:
            doc_intelligence_client: DocumentIntelligenceClient instance
            file_handler: FileHandler instance
            field_extractor: FieldExtractor instance
        """
        self.doc_intelligence_client = (
            doc_intelligence_client or DocumentIntelligenceClient()
        )
        self.file_handler = file_handler or FileHandler()
        self.field_extractor = field_extractor or FieldExtractor()
    
    async def extract_invoice(
        self,
        invoice_id: str,
        file_identifier: str,
        file_name: str,
        upload_date: datetime,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Extract data from an invoice PDF
        
        Args:
            invoice_id: Unique invoice ID
            file_identifier: File path (local) or blob name (Azure)
            file_name: Original file name
            upload_date: Upload timestamp
            db: Optional async DB session (uses default if not provided)
            
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
            
            # Step 3: Extract text for subtype detection (optional, for better subtype extraction)
            invoice_text = None  # Could extract from PDF if needed
            
            # Step 4: Map to Invoice model using FieldExtractor
            logger.info(f"Mapping extracted data to Invoice model: {invoice_id}")
            file_path = self.file_handler.get_file_path(file_identifier)
            
            invoice = self.field_extractor.extract_invoice(
                doc_intelligence_data=doc_intelligence_data,
                file_path=file_path,
                file_name=file_name,
                upload_date=upload_date,
                invoice_text=invoice_text
            )
            invoice.id = invoice_id
            invoice.status = "extracted"
            
            # Step 5: Save to database
            logger.info(f"Saving extracted invoice to database: {invoice_id}")
            await DatabaseService.save_invoice(invoice, db=db)
            
            # Prepare JSON-serializable payload
            invoice_dict = invoice.model_dump(mode="json")
            extraction_ts = invoice.extraction_timestamp.isoformat() if invoice.extraction_timestamp else None

            # Low-confidence fallback stub: capture fields below threshold (0.75)
            low_conf_threshold = 0.75
            low_conf_fields = []
            if invoice.field_confidence:
                low_conf_fields = [
                    name for name, conf in invoice.field_confidence.items()
                    if conf is not None and conf < low_conf_threshold
                ]
            # Placeholder for future multimodal correction hook
            if low_conf_fields:
                self._run_low_confidence_fallback(invoice, low_conf_fields, doc_intelligence_data)
                # re-save after potential adjustments
                invoice_dict = invoice.model_dump(mode="json")
                await DatabaseService.save_invoice(invoice, db=db)
            
            result = {
                "invoice_id": invoice_id,
                "status": "extracted",
                "invoice": invoice_dict,
                "confidence": invoice.extraction_confidence,
                "field_confidence": invoice.field_confidence,
                "extraction_timestamp": extraction_ts,
                "errors": [],
                "low_confidence_fields": low_conf_fields,
                "low_confidence_triggered": bool(low_conf_fields)
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
    
    def _run_low_confidence_fallback(self, invoice: Invoice, low_conf_fields: list, di_payload: dict):
        """
        Low-confidence fallback hook. Currently a stub; if settings.USE_LLM_FALLBACK is True,
        this is where we would call a multimodal LLM to suggest corrections.
        """
        if not getattr(settings, "USE_LLM_FALLBACK", False):
            logger.info(
                "Low-confidence fallback stub (LLM disabled). Invoice %s fields: %s",
                invoice.id,
                ", ".join(low_conf_fields)
            )
            return

        if AzureOpenAI is None:
            logger.warning("openai package not installed; skipping LLM fallback.")
            return

        if not settings.AOAI_ENDPOINT or not settings.AOAI_API_KEY or not settings.AOAI_DEPLOYMENT_NAME:
            logger.warning("AOAI config missing; skipping LLM fallback.")
            return

        try:
            client = AzureOpenAI(
                azure_endpoint=settings.AOAI_ENDPOINT,
                api_key=settings.AOAI_API_KEY,
                api_version=settings.AOAI_API_VERSION,
            )

            prompt = self._build_llm_prompt(di_payload, low_conf_fields)
            if not prompt:
                return

            resp = client.chat.completions.create(
                model=settings.AOAI_DEPLOYMENT_NAME,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": "You are an assistant that fixes invoice extraction results. Return JSON only."},
                    {"role": "user", "content": prompt},
                ],
            )
            if not resp.choices:
                logger.warning("LLM fallback returned no choices")
                return
            suggestion_text = resp.choices[0].message.content if resp.choices else None
            if suggestion_text:
                self._apply_llm_suggestions(invoice, suggestion_text, low_conf_fields)
            else:
                logger.warning("LLM fallback returned empty content")
        except Exception as e:
            logger.error(f"LLM fallback failed: {e}", exc_info=True)

    def _build_llm_prompt(self, di_payload: Dict[str, Any], low_conf_fields: List[str]) -> Optional[str]:
        try:
            minimal = {k: v for k, v in di_payload.items() if k in low_conf_fields or k == "items"}
            sanitized = self._sanitize_for_json(minimal)
            return (
                "Given this invoice extraction (JSON), improve only the listed low-confidence fields. "
                "Return JSON with just those fields corrected. If unknown, omit the field. "
                f"Low-confidence fields: {', '.join(low_conf_fields)}\n"
                f"Data:\n{json.dumps(sanitized, default=str)[:8000]}"
            )
        except Exception as e:
            logger.error(f"Failed to build LLM prompt: {e}", exc_info=True)
            return None

    def _apply_llm_suggestions(self, invoice: Invoice, suggestion_text: str, low_conf_fields: List[str]):
        try:
            data = json.loads(suggestion_text)
        except Exception as e:
            logger.warning(f"Could not parse LLM suggestions as JSON: {e}")
            return

        # Map known fields
        for field in low_conf_fields:
            if field in data:
                try:
                    # alias single -> plural for payment terms
                    target_field = field
                    if field == "payment_term":
                        target_field = "payment_terms"

                    if target_field in ["subtotal", "tax_amount", "total_amount", "acceptance_percentage"]:
                        setattr(invoice, target_field, Decimal(str(data[field])))
                    elif target_field in ["invoice_date", "due_date", "service_start_date", "service_end_date", "period_start", "period_end"]:
                        from dateutil.parser import parse
                        setattr(invoice, target_field, parse(data[field]).date())
                    elif target_field in ["vendor_address", "customer_address", "remit_to_address"]:
                        # Expect dict with street/city/province/postal_code/country
                        addr = data[field]
                        if isinstance(addr, dict):
                            from src.models.invoice import Address
                            setattr(invoice, target_field, Address(**addr))
                    else:
                        setattr(invoice, target_field, data[field])
                    if invoice.field_confidence:
                        invoice.field_confidence[target_field] = 0.9
                except Exception as e:
                    logger.warning(f"Could not apply LLM suggestion for {field}: {e}")

    def _sanitize_for_json(self, obj):
        """Recursively convert payload objects to JSON-serializable primitives."""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._sanitize_for_json(v) for v in obj]
        # Handle Azure SDK field objects like CurrencyValue by using amount/value/text
        if hasattr(obj, "amount"):
            return self._sanitize_for_json(getattr(obj, "amount"))
        if hasattr(obj, "value"):
            return self._sanitize_for_json(getattr(obj, "value"))
        if hasattr(obj, "text"):
            return self._sanitize_for_json(getattr(obj, "text"))
        # Fallback to string
        return str(obj)

