"""Simplified extraction service with field extractor and database integration"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date
from decimal import Decimal
import logging
import json
import hashlib

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

LLM_SYSTEM_PROMPT = """
You are an expert accounts-payable invoice validator working for a Canadian federal agency.

You are given:
- JSON containing the fields extracted from a single vendor invoice (the canonical extraction result); 
- a list of canonical field names that currently have LOW confidence; and
- a snippet of the invoice text that contains the raw evidence.

Your task:
- For each low-confidence field, look at the evidence text and the current extracted value.
- If the correct value is clearly present in the evidence text, correct it.
- If the value is present but the format is wrong (e.g., date style, thousand separators, currency symbol), normalize the format.
- If the correct value cannot be identified with high confidence, DO NOT guess or hallucinate: simply omit that field from your JSON response.

Formatting rules:
- Dates must be ISO 8601 date strings: "YYYY-MM-DD".
- Monetary amounts must be numeric, using "." as the decimal separator.
- Do not change currencies or magnitudes: if the invoice says 1,234.56, keep that amount, including cents.
- Trim whitespace and normalize casing where appropriate, but do not rewrite vendor names beyond obvious OCR fixes.
- For address fields (vendor_address, bill_to_address, remit_to_address), return an object with keys: street, city, province, postal_code, country. Leave any unknown subfields empty or omit the address field entirely if not confident.

Output:
- Return ONE JSON object only (no explanations, comments, code fences, or extra keys).
- The JSON object’s keys must be a subset of the canonical field names you are given (e.g., "invoice_number", "invoice_date", "vendor_name", "total_amount", "vendor_address", "bill_to_address", "remit_to_address").
- For scalar fields, use a single string/number/ISO date. For address fields, use an object with street, city, province, postal_code, country.
"""


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
        # Simple in-memory cache to avoid re-spending tokens for identical requests
        self._llm_cache: Dict[Tuple[str, Tuple[str, ...], str, str], str] = {}
    
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
                invoice_text=doc_intelligence_data.get("content") or invoice_text
            )
            invoice.id = invoice_id
            invoice.status = "extracted"
            
            # Step 5: Save to database
            logger.info(f"Saving extracted invoice to database: {invoice_id}")
            await DatabaseService.save_invoice(invoice, db=db)
            
            # Prepare JSON-serializable payload
            invoice_dict = invoice.model_dump(mode="json")
            extraction_ts = invoice.extraction_timestamp.isoformat() if invoice.extraction_timestamp else None

            # Low-confidence fallback: decide which fields to send to LLM
            low_conf_threshold = 1.1  # TEMP: force all REQUIRED fields through fallback for testing
            low_conf_fields: List[str] = []
            REQUIRED = [
                "invoice_number",
                "invoice_date",
                "due_date",
                "total_amount",
                "currency",
                "vendor_name",
            ]
            fc = invoice.field_confidence or {}

            for name in REQUIRED:
                conf = fc.get(name)
                if conf is None or conf < low_conf_threshold:
                    low_conf_fields.append(name)

            line_items = invoice.line_items
            if line_items and invoice.line_items:
                line_item_required = ["description", "quantity", "unit_price", "amount"]
                for idx, li in enumerate(invoice.line_items):
                    licf = {}
                    if hasattr(li, "confidence") and isinstance(li.confidence, dict):
                        licf = (li.confidence or {}).get("fields", {}) or {}
                    for fname in line_item_required:
                        conf = licf.get(fname)
                        if conf is None or conf < low_conf_threshold:
                            key = f"line_item[{idx}].{fname}"
                            low_conf_fields.append(key)

            if not low_conf_fields:
                logger.info("No fields below low_conf_threshold=%.2f, skipping LLM fallback", low_conf_threshold)
            else:
                try:
                    self._run_low_confidence_fallback(
                        invoice=invoice,
                        low_conf_fields=low_conf_fields,
                        di_payload=doc_intelligence_data,
                    )
                except Exception as e:
                    logger.exception("LLM fallback failed; continuing with DI-only invoice: %s", e)

            # Final save after LLM post-processing
            logger.info("Saving extracted invoice to database (after LLM) for: %s", invoice_id)
            await DatabaseService.save_invoice(invoice, db=db)
            invoice_dict = invoice.model_dump(mode="json")

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

            try:
                canonical_di = self.field_extractor.normalize_di_data(di_payload or {})
            except Exception:
                canonical_di = di_payload or {}

            prompt = self._build_llm_prompt(canonical_di, low_conf_fields)
            if not prompt:
                return

            cache_key = (
                settings.AOAI_DEPLOYMENT_NAME or "",
                tuple(sorted(low_conf_fields)),
                invoice.id or "",
                hashlib.sha256(prompt.encode("utf-8", "ignore")).hexdigest(),
            )

            suggestion_text = self._llm_cache.get(cache_key)
            if suggestion_text is None:
                resp = client.chat.completions.create(
                    model=settings.AOAI_DEPLOYMENT_NAME,
                    temperature=0.0,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": LLM_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                )
                if not resp.choices:
                    logger.warning("LLM fallback returned no choices")
                    return
                suggestion_text = resp.choices[0].message.content
                if suggestion_text:
                    self._llm_cache[cache_key] = suggestion_text
                else:
                    logger.warning("LLM fallback returned empty content")
                    return

            self._apply_llm_suggestions(invoice, suggestion_text, low_conf_fields)
        except Exception as e:
            logger.error(f"LLM fallback failed: {e}", exc_info=True)

    def _build_llm_prompt(self, di_payload: Dict[str, Any], low_conf_fields: List[str]) -> Optional[str]:
        """Build prompt using canonical field names and DI content as evidence."""
        try:
            # Only send the low-confidence fields to keep the LLM call surgical/cheap
            minimal = {k: v for k, v in di_payload.items() if k in low_conf_fields}

            # Keep evidence small: only low-conf fields + limited text
            content_snippet = ""
            pages = di_payload.get("pages")
            if isinstance(pages, list) and pages:
                first_page = str(pages[0])
                last_page = str(pages[-1]) if len(pages) > 1 else ""
                head = first_page[:1200]
                tail = last_page[-800:] if last_page else ""
                content_snippet = head + ("\n...\n" + tail if tail else "")
            else:
                raw_content = str(di_payload.get("content", ""))
                if len(raw_content) > 2000:
                    head = raw_content[:1200]
                    tail = raw_content[-800:]
                    content_snippet = head + "\n...\n" + tail
                else:
                    content_snippet = raw_content

            sanitized = self._sanitize_for_json(minimal)
            parts = [
                "Given this invoice extraction (JSON), improve only the listed low-confidence fields using the evidence text.",
                "Return JSON with just those fields corrected. If unknown, omit the field.",
                f"Low-confidence fields (canonical): {', '.join(low_conf_fields)}",
                f"Data:\n{json.dumps(sanitized, default=str)[:6000]}",
            ]
            if content_snippet:
                parts.append(f"Evidence text (may be truncated):\n{content_snippet[:2000]}")
            return "\n\n".join(parts)
        except Exception as e:
            logger.error(f"Failed to build LLM prompt: {e}", exc_info=True)
            return None

    def _apply_llm_suggestions(self, invoice: Invoice, suggestion_text: str, low_conf_fields: List[str]):
        try:
            data = json.loads(suggestion_text)
        except Exception as e:
            logger.warning(f"Could not parse LLM suggestions as JSON: {e}")
            return

        logger.info(
            "LLM suggestions for invoice %s (fields=%s): %s",
            invoice.id,
            ", ".join(low_conf_fields),
            suggestion_text,
        )

        # Map known fields
        for field in low_conf_fields:
            if field in data:
                try:
                    target_field = field
                    if field == "payment_term":
                        target_field = "payment_terms"
                    if field == "invoice_total":
                        target_field = "total_amount"
                    if field == "purchase_order":
                        target_field = "po_number"

                    if target_field in ["subtotal", "tax_amount", "total_amount", "acceptance_percentage"]:
                        parsed = self.field_extractor._parse_decimal(data[field])
                        old_val = getattr(invoice, target_field, None)
                        if old_val != parsed:
                            logger.info(
                                "LLM updated %s for invoice %s: %r -> %r",
                                target_field,
                                invoice.id,
                                old_val,
                                parsed,
                            )
                        setattr(invoice, target_field, parsed)
                    elif target_field in [
                        "invoice_date",
                        "due_date",
                        "service_start_date",
                        "service_end_date",
                        "period_start",
                        "period_end",
                    ]:
                        from dateutil.parser import parse

                        new_val = parse(data[field]).date()
                        old_val = getattr(invoice, target_field, None)
                        if old_val != new_val:
                            logger.info(
                                "LLM updated %s for invoice %s: %r -> %r",
                                target_field,
                                invoice.id,
                                old_val,
                                new_val,
                            )
                        setattr(invoice, target_field, new_val)
                    elif target_field in ["vendor_address", "bill_to_address", "remit_to_address"]:
                        addr = data[field]
                        if isinstance(addr, dict):
                            from src.models.invoice import Address

                            new_val = Address(**addr)
                            old_val = getattr(invoice, target_field, None)
                            if old_val != new_val:
                                logger.info(
                                    "LLM updated %s for invoice %s: %r -> %r",
                                    target_field,
                                    invoice.id,
                                    old_val,
                                    new_val,
                                )
                            setattr(invoice, target_field, new_val)
                    else:
                        new_val = data[field]
                        old_val = getattr(invoice, target_field, None)
                        if old_val != new_val:
                            logger.info(
                                "LLM updated %s for invoice %s: %r -> %r",
                                target_field,
                                invoice.id,
                                old_val,
                                new_val,
                            )
                        setattr(invoice, target_field, new_val)

                    if invoice.field_confidence is None:
                        invoice.field_confidence = {}
                    invoice.field_confidence[target_field] = max(invoice.field_confidence.get(target_field, 0.0), 0.9)
                except Exception as e:
                    logger.warning(f"Could not apply LLM suggestion for {field}: {e}")

        # Recompute overall confidence after applying suggestions
        try:
            if invoice.field_confidence:
                invoice.extraction_confidence = self.field_extractor._calculate_overall_confidence(
                    invoice.field_confidence
                )
        except Exception:
            pass

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

