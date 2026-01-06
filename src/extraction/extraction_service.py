"""Simplified extraction service with field extractor and database integration"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date
from decimal import Decimal
import logging
import json
import re
import hashlib
from typing import Any, Mapping, Dict
import time

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from .document_intelligence_client import DocumentIntelligenceClient
from .field_extractor import FieldExtractor
from src.ingestion.file_handler import FileHandler
from src.models.invoice import Invoice
from src.services.db_service import DatabaseService
from src.services.validation_service import ValidationService
from src.models.db_utils import address_to_dict, line_items_to_json, _sanitize_tax_breakdown
from src.services.progress_tracker import progress_tracker, ProcessingStep
from src.config import settings
try:
    from openai import AzureOpenAI
    from openai import RateLimitError, APIError
except ImportError:
    AzureOpenAI = None
    RateLimitError = None
    APIError = None

logger = logging.getLogger(__name__)

# Canonical field names - single source of truth
CANONICAL_FIELDS = {
    # Header
    "invoice_number", "invoice_date", "due_date", "invoice_type", "reference_number",
    # Vendor
    "vendor_name", "vendor_id", "vendor_phone", "vendor_fax", "vendor_email", 
    "vendor_website", "vendor_address",
    # Vendor Tax IDs
    "gst_number", "qst_number", "pst_number", "business_number",
    # Customer
    "customer_name", "customer_id", "customer_phone", "customer_email", 
    "customer_fax", "bill_to_address",
    # Remit-To
    "remit_to_address", "remit_to_name",
    # Contract
    "entity", "contract_id", "standing_offer_number", "po_number",
    # Dates
    "period_start", "period_end", "shipping_date", "delivery_date",
    # Financial
    "subtotal", "discount_amount", "shipping_amount", "handling_fee", "deposit_amount",
    # Canadian Taxes
    "gst_amount", "gst_rate", "hst_amount", "hst_rate", 
    "qst_amount", "qst_rate", "pst_amount", "pst_rate",
    # Total
    "tax_amount", "total_amount", "currency", "tax_breakdown",
    # Payment
    "payment_terms", "payment_method", "payment_due_upon", 
    "acceptance_percentage", "tax_registration_number",
}

LLM_SYSTEM_PROMPT = """
You are a specialized invoice extraction QA assistant for CATSA.

You receive:
- A JSON object `di_payload` that contains the extracted invoice fields and their values, using the canonical field names expected by downstream systems.
- A JSON object `field_confidence` with per-field confidence scores from the upstream extractor.
- A JSON array `low_conf_fields` listing the subset of fields that the upstream model is uncertain about.
- Optionally, a short OCR text snippet from the invoice PDF.

Your task:
1. For each field in `low_conf_fields`, decide whether the value in `di_payload` is correct.
2. If it is clearly wrong or missing, infer a corrected value using ONLY the provided JSON and OCR snippet.
3. NEVER invent fields, change field names, or guess values that are not strongly supported by the data.
4. If you cannot reliably correct a field, set it to null.
5. Output ONLY a single JSON object whose keys are exactly the field names from `low_conf_fields`, with their corrected (or null) values.
6. Do NOT include explanations, comments, or extra properties.

CANONICAL FIELD NAMES (use these EXACTLY):
Header: invoice_number, invoice_date, due_date, invoice_type, reference_number
Vendor: vendor_name, vendor_id, vendor_phone, vendor_fax, vendor_email, vendor_website, vendor_address
Vendor Tax IDs: gst_number, qst_number, pst_number, business_number
Customer: customer_name, customer_id, customer_phone, customer_email, customer_fax, bill_to_address
Remit-To: remit_to_address, remit_to_name
Contract: entity, contract_id, standing_offer_number, po_number
Dates: period_start, period_end, shipping_date, delivery_date
Financial: subtotal, discount_amount, shipping_amount, handling_fee, deposit_amount
Canadian Taxes: gst_amount, gst_rate, hst_amount, hst_rate, qst_amount, qst_rate, pst_amount, pst_rate
Total: tax_amount, total_amount, currency
Payment: payment_terms, payment_method, payment_due_upon, acceptance_percentage, tax_registration_number

Formatting rules:
- Dates must be ISO 8601 date strings: "YYYY-MM-DD".
- Monetary amounts must be numeric strings, using "." as the decimal separator (e.g., "1234.56").
- Trim whitespace and normalize casing where appropriate, but do not rewrite vendor names beyond obvious OCR fixes.
- For address fields (vendor_address, bill_to_address, remit_to_address), return an object with keys: street, city, province, postal_code, country. Use null or empty for unknown subfields.
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
        self.validation_service = ValidationService()
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

            claimed = await DatabaseService.claim_for_extraction(invoice_id)
            if not claimed:
                return {
                    "invoice_id": invoice_id,
                    "status": "conflict",
                    "errors": ["Invoice is already processing"],
                }
            
            # Step 1: Download PDF
            logger.info(f"Downloading PDF: {file_identifier}")
            file_content = await run_in_threadpool(self.file_handler.download_file, file_identifier)
            
            if not file_content:
                errors.append("Failed to download file")
                return {
                    "invoice_id": invoice_id,
                    "status": "error",
                    "errors": errors
                }
            
            # Step 2: Analyze with Document Intelligence
            logger.info(f"Analyzing invoice with Document Intelligence: {invoice_id}")
            doc_intelligence_data = await run_in_threadpool(
                self.doc_intelligence_client.analyze_invoice,
                file_content,
            )
            
            if not doc_intelligence_data or doc_intelligence_data.get("error"):
                errors.append(
                    doc_intelligence_data.get("error", "Document Intelligence analysis failed")
                )
                return {
                    "invoice_id": invoice_id,
                    "status": "upstream_error",
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
            patch = self._invoice_to_patch(invoice)
            ok = await DatabaseService.set_extraction_result(invoice_id, patch, db=db)
            if not ok:
                raise ValueError("Failed to persist extraction result; state mismatch")
            
            # Prepare JSON-serializable payload
            invoice_dict = invoice.model_dump(mode="json")
            extraction_ts = invoice.extraction_timestamp.isoformat() if invoice.extraction_timestamp else None

            # Low-confidence fallback: trigger when required fields are missing or low, and when any field is explicitly low.
            low_conf_threshold = 0.75
            low_conf_fields: List[str] = []
            fc = invoice.field_confidence or {}

            required = [
                "invoice_number",
                "invoice_date",
                "vendor_name",
                "total_amount",
                "vendor_address",
                "bill_to_address",
                "remit_to_address",
            ]
            for field in required:
                val = getattr(invoice, field, None)
                conf = fc.get(field)
                if val in (None, "", {}) or conf is None or conf < low_conf_threshold:
                    low_conf_fields.append(field)

            for name, conf in fc.items():
                if name in required:
                    continue
                if conf is None or conf < low_conf_threshold:
                    low_conf_fields.append(name)

            # Deduplicate while preserving order
            seen = set()
            low_conf_fields = [x for x in low_conf_fields if not (x in seen or seen.add(x))]

            llm_changed = False
            if not low_conf_fields:
                logger.info("No fields below low_conf_threshold=%.2f, skipping LLM fallback", low_conf_threshold)
                await progress_tracker.update(invoice_id, 100, "No LLM evaluation needed")
            else:
                aoai_ready = self._has_aoai_config()
                use_llm = bool(getattr(settings, "USE_LLM_FALLBACK", False))
                use_demo_llm = settings.DEMO_MODE and not aoai_ready

                if not use_llm and not use_demo_llm:
                    logger.info("LLM fallback disabled; skipping %d low-confidence fields", len(low_conf_fields))
                    await progress_tracker.update(invoice_id, 100, "LLM evaluation disabled")
                else:
                    await progress_tracker.start(
                        invoice_id,
                        ProcessingStep.LLM_EVALUATION,
                        f"Evaluating {len(low_conf_fields)} low-confidence fields with LLM...",
                    )
                    await progress_tracker.update(
                        invoice_id,
                        75,
                        f"Starting {'mock' if use_demo_llm else 'LLM'} evaluation for {len(low_conf_fields)} fields...",
                    )
                    invoice_before_llm = invoice.model_dump(mode="json")
                    try:
                        if use_demo_llm:
                            self._run_mock_llm_fallback(
                                invoice,
                                low_conf_fields,
                                doc_intelligence_data,
                                fc,
                            )
                        else:
                            await run_in_threadpool(
                                self._run_low_confidence_fallback,
                                invoice,
                                low_conf_fields,
                                doc_intelligence_data,
                                fc,
                            )
                        llm_changed = invoice.model_dump(mode="json") != invoice_before_llm
                        await progress_tracker.update(invoice_id, 95, "LLM evaluation complete")
                        await progress_tracker.complete_step(invoice_id, ProcessingStep.LLM_EVALUATION, "LLM evaluation complete")
                    except Exception as e:
                        logger.exception("LLM fallback failed; continuing with DI-only invoice: %s", e)
                        await progress_tracker.error(invoice_id, f"LLM evaluation failed: {str(e)}", ProcessingStep.LLM_EVALUATION)

            # Final save after LLM post-processing only when there was a change
            if llm_changed:
                logger.info("Saving extracted invoice to database (after LLM) for: %s", invoice_id)
                await progress_tracker.update(invoice_id, 98, "Saving LLM-enhanced results...")
                patch = self._invoice_to_patch(invoice)
                ok2 = await DatabaseService.set_extraction_result(invoice_id, patch, db=db)
                if not ok2:
                    raise ValueError("Failed to persist post-LLM extraction result; state mismatch")
            else:
                logger.info("Skipping post-LLM save; no LLM changes detected.")
            invoice_dict = invoice.model_dump(mode="json")

            # Run business rule validation
            validation_result = self.validation_service.validate(invoice)
            logger.info(
                f"Invoice {invoice_id} validation: {validation_result['passed_rules']}/{validation_result['total_rules']} rules passed"
            )

            result = {
                "invoice_id": invoice_id,
                "status": "extracted",
                "invoice": invoice_dict,
                "confidence": invoice.extraction_confidence,
                "field_confidence": invoice.field_confidence,
                "extraction_timestamp": extraction_ts,
                "errors": [],
                "low_confidence_fields": low_conf_fields,
                "low_confidence_triggered": bool(low_conf_fields),
                "validation": validation_result
            }
            
            logger.info(f"Extraction completed successfully for invoice: {invoice_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting invoice {invoice_id}: {e}", exc_info=True)
            errors.append(str(e))
            await DatabaseService.set_extraction_failed(invoice_id, "; ".join(errors), db=db)
            return {
                "invoice_id": invoice_id,
                "status": "error",
                "errors": errors
            }
    
    async def run_ai_extraction(
        self,
        invoice_id: str,
        confidence_threshold: float = 0.7,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Manually trigger AI extraction for low-confidence fields
        
        Args:
            invoice_id: Invoice ID to improve
            confidence_threshold: Minimum confidence threshold (fields below will be processed)
            db: Optional async DB session
            
        Returns:
            Dictionary with AI extraction results
        """
        try:
            logger.info(f"Starting manual AI extraction for invoice: {invoice_id}")
            
            # Get current invoice from database
            invoice_dict = await DatabaseService.get_invoice(invoice_id, db=db)
            if not invoice_dict:
                return {
                    "invoice_id": invoice_id,
                    "status": "error",
                    "errors": ["Invoice not found"]
                }
            
            # Convert to Invoice model
            invoice = Invoice(**invoice_dict)
            
            # Get field confidence
            fc = invoice.field_confidence or {}
            
            # Identify low-confidence fields
            low_conf_fields = []
            for field_name, confidence in fc.items():
                if confidence is not None and confidence < confidence_threshold:
                    low_conf_fields.append(field_name)
            
            # Also check required fields with no value or confidence
            required = [
                "invoice_number", "invoice_date", "vendor_name", "total_amount",
                "vendor_address", "bill_to_address", "remit_to_address",
            ]
            for field in required:
                val = getattr(invoice, field, None)
                conf = fc.get(field)
                if (val in (None, "", {}) or conf is None or conf < confidence_threshold) and field not in low_conf_fields:
                    low_conf_fields.append(field)
            
            if not low_conf_fields:
                logger.info(f"No low-confidence fields found for invoice {invoice_id}")
                return {
                    "invoice_id": invoice_id,
                    "status": "success",
                    "message": "All fields have sufficient confidence",
                    "fields_improved": 0,
                    "low_confidence_fields": []
                }
            
            logger.info(f"Processing {len(low_conf_fields)} low-confidence fields: {low_conf_fields}")
            
            # Get original DI data - we need the content for LLM context
            # For now, we'll work with what we have in the invoice
            # TODO: Store original DI data with bounding boxes for better LLM context
            di_data = {
                "content": invoice_dict.get("content") or "",
                "invoice_number": invoice.invoice_number,
                "vendor_name": invoice.vendor_name,
                "total_amount": str(invoice.total_amount) if invoice.total_amount else None,
            }
            
            # Store before state
            invoice_before = invoice.model_dump(mode="json")
            
            # Run LLM fallback
            await run_in_threadpool(
                self._run_low_confidence_fallback,
                invoice,
                low_conf_fields,
                di_data,
                fc,
            )
            
            # Check what changed
            invoice_after = invoice.model_dump(mode="json")
            fields_improved = []
            for field in low_conf_fields:
                before_val = invoice_before.get(field)
                after_val = invoice_after.get(field)
                if before_val != after_val:
                    fields_improved.append(field)
            
            # Save updated invoice
            if fields_improved:
                logger.info(f"AI extraction improved {len(fields_improved)} fields: {fields_improved}")
                patch = self._invoice_to_patch(invoice)
                ok = await DatabaseService.set_extraction_result(invoice_id, patch, db=db)
                if not ok:
                    raise ValueError("Failed to persist AI extraction result")
            else:
                logger.info("AI extraction did not improve any fields")
            
            return {
                "invoice_id": invoice_id,
                "status": "success",
                "fields_improved": len(fields_improved),
                "improved_fields": fields_improved,
                "low_confidence_fields": low_conf_fields,
                "invoice": invoice.model_dump(mode="json")
            }
            
        except Exception as e:
            logger.error(f"Error in AI extraction for {invoice_id}: {e}", exc_info=True)
            return {
                "invoice_id": invoice_id,
                "status": "error",
                "errors": [str(e)]
            }
    
    def _run_low_confidence_fallback(
        self,
        invoice: Invoice,
        low_conf_fields: List[str],
        di_data: Dict[str, Any],
        di_field_confidence: Optional[Dict[str, float]] = None,
    ) -> None:
        """Run LLM fallback to refine low-confidence fields. Best-effort and non-blocking."""
        logger.info("Running LLM fallback for low confidence fields: %s", low_conf_fields)

        if not low_conf_fields:
            logger.info("No low-confidence fields to refine; skipping LLM fallback.")
            return

        if not getattr(settings, "USE_LLM_FALLBACK", False):
            logger.info("LLM fallback disabled via settings; skipping.")
            return

        if AzureOpenAI is None:
            logger.warning("openai package not installed; skipping LLM fallback.")
            return

        if not settings.AOAI_ENDPOINT or not settings.AOAI_API_KEY or not settings.AOAI_DEPLOYMENT_NAME:
            logger.warning("AOAI config missing; skipping LLM fallback.")
            return

        try:
            # group fields to reduce payload; process sequentially with small jitter
            fc = di_field_confidence or {}
            groups = [
                (
                    "fields",
                    {
                        "invoice_number", "invoice_date", "due_date",
                        "vendor_name", "vendor_id", "vendor_phone",
                        "customer_name", "customer_id",
                        "subtotal", "tax_amount", "total_amount",
                        "currency", "payment_terms", "acceptance_percentage",
                        "tax_registration_number",
                    },
                ),
                ("addresses", {"vendor_address", "bill_to_address", "remit_to_address"}),
                ("line_items", {f for f in low_conf_fields if f.startswith("line_items")}),
            ]

            # Prepare sanitized DI snapshot for caching (common)
            di_snapshot_base = {
                "di_fields": di_data or {},
                "di_field_confidence": fc,
            }
            try:
                canonical_di = self.field_extractor.normalize_di_data(di_data or {})
            except Exception:
                canonical_di = di_data or {}

            for idx, (grp_name, grp_fields) in enumerate(groups):
                sub_fields = [f for f in low_conf_fields if f in grp_fields]
                if not sub_fields:
                    continue

                di_snapshot = dict(di_snapshot_base)
                di_snapshot["low_conf_fields"] = sub_fields
                di_snapshot = self._sanitize_for_json(di_snapshot)

                prompt = self._build_llm_prompt(canonical_di, sub_fields, di_data)
                if not prompt:
                    logger.info("No prompt built for group %s; skipping.", grp_name)
                    continue

                cache_key = (
                    settings.AOAI_DEPLOYMENT_NAME or "",
                    tuple(sorted(sub_fields)),
                    invoice.file_name or invoice.id or "",
                    json.dumps(di_snapshot, sort_keys=True),
                )

                suggestion_text = self._llm_cache.get(cache_key)
                if suggestion_text is None:
                    client = AzureOpenAI(
                        api_key=settings.AOAI_API_KEY,
                        api_version=settings.AOAI_API_VERSION,
                        azure_endpoint=settings.AOAI_ENDPOINT,
                    )

                    logger.info("Calling Azure OpenAI chat.completions for group %s.", grp_name)
                    
                    # Retry logic for OpenAI calls
                    max_retries = 3
                    initial_delay = 1.0
                    max_delay = 60.0
                    exponential_base = 2.0
                    
                    for attempt in range(max_retries + 1):
                        try:
                            resp = client.chat.completions.create(
                                model=settings.AOAI_DEPLOYMENT_NAME,
                                temperature=0.0,
                                messages=[
                                    {"role": "system", "content": LLM_SYSTEM_PROMPT},
                                    {"role": "user", "content": prompt},
                                ],
                            )
                            break  # Success, exit retry loop
                            
                        except Exception as call_err:
                            status = getattr(call_err, "status_code", None)
                            
                            # Rate limit error (429) - always retry with backoff
                            if status == 429 or (RateLimitError and isinstance(call_err, RateLimitError)):
                                if attempt < max_retries:
                                    delay = min(initial_delay * (exponential_base ** attempt), max_delay)
                                    # Try to get retry_after from error if available
                                    try:
                                        retry_after = getattr(call_err, "retry_after", None)
                                        if retry_after:
                                            delay = max(delay, float(retry_after))
                                    except (ValueError, AttributeError):
                                        pass
                                    
                                    logger.warning(
                                        f"LLM fallback hit rate limit (429) on group {grp_name}, "
                                        f"attempt {attempt + 1}/{max_retries}, backing off for {delay:.2f}s"
                                    )
                                    time.sleep(delay)
                                    continue
                                else:
                                    logger.warning("LLM fallback hit rate limit (429) on group %s after max retries; stopping further LLM calls.", grp_name)
                                    break
                            
                            # Other API errors - retry if not max attempts
                            elif APIError and isinstance(call_err, APIError) and attempt < max_retries:
                                delay = min(initial_delay * (exponential_base ** attempt), max_delay)
                                logger.warning(
                                    f"LLM fallback API error on group {grp_name}, "
                                    f"attempt {attempt + 1}/{max_retries}: {call_err}, retrying in {delay:.2f}s"
                                )
                                time.sleep(delay)
                                continue
                            
                            # Non-retryable error or max retries reached
                            logger.error("LLM fallback call failed for group %s: %s", grp_name, call_err, exc_info=True)
                            break
                    else:
                        # All retries exhausted without success
                        logger.error("LLM fallback exhausted all retries for group %s", grp_name)
                        continue

                    if not resp.choices or not resp.choices[0].message or not resp.choices[0].message.content:
                        logger.warning("LLM fallback returned no content for group %s; skipping.", grp_name)
                        continue

                    suggestion_text = resp.choices[0].message.content.strip()
                    self._llm_cache[cache_key] = suggestion_text

                llm_data = self._coerce_llm_json(suggestion_text)
                if llm_data is None:
                    logger.error("LLM fallback returned non-JSON content for group %s; skipping.", grp_name)
                    logger.debug("Raw LLM suggestion text: %s", suggestion_text)
                    continue

                if not isinstance(llm_data, dict):
                    logger.error("LLM fallback JSON is not an object for group %s; got %s", grp_name, type(llm_data))
                    logger.debug("Raw LLM suggestion text: %s", suggestion_text)
                    continue

                self._apply_llm_suggestions(invoice, llm_data, sub_fields)
                logger.info("LLM fallback suggestions applied successfully for group %s.", grp_name)

        except Exception as e:
            logger.exception("LLM fallback failed: %s", e)

    def _run_mock_llm_fallback(
        self,
        invoice: Invoice,
        low_conf_fields: List[str],
        di_data: Dict[str, Any],
        di_field_confidence: Optional[Dict[str, float]] = None,
    ) -> None:
        """Demo-mode LLM fallback that uses deterministic heuristics (no external calls)."""
        logger.info("Running mock LLM fallback for low confidence fields: %s", low_conf_fields)
        if not low_conf_fields:
            return

        canonical = self.field_extractor.normalize_di_data(di_data or {})
        di_raw = di_data or {}

        def _first_value(*values):
            for val in values:
                if val not in (None, "", {}):
                    return val
            return None

        def _promote_confidence(field_name: str) -> None:
            if invoice.field_confidence is None:
                invoice.field_confidence = {}
            current = invoice.field_confidence.get(field_name, 0.0)
            invoice.field_confidence[field_name] = max(float(current or 0.0), 0.9)

        for field in low_conf_fields:
            try:
                if field in {"vendor_address", "bill_to_address", "remit_to_address"}:
                    addr_data = _first_value(canonical.get(field), di_raw.get(field))
                    if addr_data:
                        setattr(invoice, field, self.field_extractor._map_address(addr_data))
                        _promote_confidence(field)
                    continue

                if field in {"invoice_date", "due_date", "period_start", "period_end"}:
                    parsed = self.field_extractor._parse_date(canonical.get(field))
                    if parsed:
                        setattr(invoice, field, parsed)
                        _promote_confidence(field)
                    continue

                if field in {"subtotal", "tax_amount", "total_amount", "acceptance_percentage"}:
                    parsed = self.field_extractor._parse_decimal(canonical.get(field))
                    if parsed is not None:
                        setattr(invoice, field, parsed)
                        _promote_confidence(field)
                    continue

                candidate = _first_value(
                    canonical.get(field),
                    di_raw.get(field),
                    di_raw.get("invoice_id") if field == "invoice_number" else None,
                    di_raw.get("InvoiceId") if field == "invoice_number" else None,
                    di_raw.get("purchase_order") if field == "po_number" else None,
                    di_raw.get("PurchaseOrder") if field == "po_number" else None,
                    di_raw.get("payment_term") if field == "payment_terms" else None,
                    di_raw.get("PaymentTerm") if field == "payment_terms" else None,
                )
                if candidate not in (None, "", {}):
                    setattr(invoice, field, candidate)
                    _promote_confidence(field)
            except Exception as err:
                logger.warning("Mock LLM fallback skipped field %s: %s", field, err)

        try:
            if invoice.field_confidence:
                invoice.extraction_confidence = self.field_extractor._calculate_overall_confidence(
                    invoice.field_confidence
                )
        except Exception:
            pass

    def _has_aoai_config(self) -> bool:
        """Return True if AOAI client/config is available for real LLM fallback."""
        return bool(
            AzureOpenAI is not None
            and settings.AOAI_ENDPOINT
            and settings.AOAI_API_KEY
            and settings.AOAI_DEPLOYMENT_NAME
        )

    def _build_llm_prompt(
        self,
        canonical_di: Dict[str, Any],
        low_conf_fields: list[str],
        di_raw: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build a JSON-safe prompt payload for the LLM, focusing ONLY on low-confidence fields.
        """
        if not canonical_di or not low_conf_fields:
            return ""

        # Only include the fields the DI model is unsure about
        minimal = {k: canonical_di.get(k) for k in low_conf_fields}

        # Make sure there are no date/Decimal/etc. objects
        sanitized = self._sanitize_for_json(minimal)

        payload = {
            "low_confidence_fields": low_conf_fields,
            "fields": sanitized,
        }

        snippet = self._build_content_snippet(di_raw or {})
        if snippet:
            payload["ocr_snippet"] = snippet

        # This string is what you send as the LLM "input"
        prefix = f"Low-confidence fields: {', '.join(low_conf_fields)}\n"
        return prefix + json.dumps(payload, ensure_ascii=False, default=str)

    def _build_content_snippet(self, di_data: Dict[str, Any]) -> str:
        """Extract a small OCR snippet to limit token usage."""
        try:
            pages = di_data.get("pages")
            if isinstance(pages, list) and pages:
                first_page = str(pages[0])
                last_page = str(pages[-1]) if len(pages) > 1 else ""
                head = first_page[:1200]
                tail = last_page[-800:] if last_page else ""
                return head + ("\n...\n" + tail if tail else "")
            raw_content = str(di_data.get("content", ""))
            if len(raw_content) > 2000:
                head = raw_content[:1200]
                tail = raw_content[-800:]
                return head + "\n...\n" + tail
            return raw_content
        except Exception:
            return ""

    def _apply_llm_suggestions(self, invoice: Invoice, suggestions: Any, low_conf_fields: List[str]):
        """
        Apply LLM suggestions to the invoice. Accepts either raw text or a parsed dict.
        Validates that LLM only returns canonical field names.
        """
        if isinstance(suggestions, str):
            llm_suggestions = self._coerce_llm_json(suggestions)
        elif isinstance(suggestions, dict):
            llm_suggestions = suggestions
        else:
            logger.warning("LLM suggestions are neither str nor dict; skipping apply.")
            return

        if llm_suggestions is None:
            logger.warning("LLM suggestions could not be coerced to JSON; skipping apply.")
            return

        # Validate LLM output - only canonical fields allowed
        invalid_fields = set(llm_suggestions.keys()) - CANONICAL_FIELDS
        if invalid_fields:
            logger.warning(f"LLM returned non-canonical fields (ignoring them): {invalid_fields}")
            # Remove non-canonical fields
            llm_suggestions = {k: v for k, v in llm_suggestions.items() if k in CANONICAL_FIELDS}
        
        if not llm_suggestions:
            logger.info("No valid canonical fields in LLM suggestions after validation")
            return

        logger.info("LLM suggestions (validated): %s", llm_suggestions)

        before = invoice.model_dump()
        for field, value in llm_suggestions.items():
            try:
                # Field names from LLM should already be canonical
                target_field = field

                # Allow explicit null to clear a low-confidence field
                if value is None:
                    setattr(invoice, target_field, None)
                elif target_field in ["subtotal", "tax_amount", "total_amount", "acceptance_percentage"]:
                    parsed = self.field_extractor._parse_decimal(value)
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

                    setattr(invoice, target_field, parse(value).date())
                elif target_field in ["vendor_address", "bill_to_address", "remit_to_address"]:
                    if isinstance(value, dict):
                        from src.models.invoice import Address

                        setattr(invoice, target_field, Address(**value))
                    else:
                        setattr(invoice, target_field, None)
                else:
                    setattr(invoice, target_field, value)

                if invoice.field_confidence is None:
                    invoice.field_confidence = {}
                invoice.field_confidence[target_field] = 0.9
            except Exception as e:
                logger.warning(f"Could not apply LLM suggestion for {field}: {e}")

        after = invoice.model_dump()
        diff = {
            k: {"before": before.get(k), "after": after.get(k)}
            for k in llm_suggestions.keys()
            if before.get(k) != after.get(k)
        }
        logger.info("LLM applied diff: %s", diff)

        # Recompute overall confidence after applying suggestions
        try:
            if invoice.field_confidence:
                invoice.extraction_confidence = self.field_extractor._calculate_overall_confidence(
                    invoice.field_confidence
                )
        except Exception:
            pass

    def _invoice_to_patch(self, invoice: Invoice) -> Dict[str, Any]:
        """Convert an Invoice Pydantic model into a dict suitable for DB update."""
        return {
            "status": invoice.status,
            "processing_state": invoice.processing_state,
            "content_sha256": invoice.content_sha256,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date,
            "due_date": invoice.due_date,
            "vendor_name": invoice.vendor_name,
            "vendor_id": invoice.vendor_id,
            "vendor_phone": invoice.vendor_phone,
            "vendor_address": address_to_dict(invoice.vendor_address),
            "customer_name": invoice.customer_name,
            "customer_id": invoice.customer_id,
            "entity": invoice.entity,
            "bill_to_address": address_to_dict(invoice.bill_to_address),
            "remit_to_address": address_to_dict(invoice.remit_to_address),
            "remit_to_name": invoice.remit_to_name,
            "contract_id": invoice.contract_id,
            "standing_offer_number": invoice.standing_offer_number,
            "po_number": invoice.po_number,
            "period_start": invoice.period_start,
            "period_end": invoice.period_end,
            "subtotal": invoice.subtotal,
            "tax_breakdown": _sanitize_tax_breakdown(invoice.tax_breakdown),
            "tax_amount": invoice.tax_amount,
            "total_amount": invoice.total_amount,
            "currency": invoice.currency,
            "acceptance_percentage": invoice.acceptance_percentage,
            "tax_registration_number": invoice.tax_registration_number,
            "payment_terms": invoice.payment_terms,
            "line_items": line_items_to_json(invoice.line_items),
            "invoice_subtype": invoice.invoice_subtype.value if invoice.invoice_subtype else None,
            "extensions": invoice.extensions.dict() if invoice.extensions else None,
            "extraction_confidence": invoice.extraction_confidence,
            "field_confidence": invoice.field_confidence,
            "extraction_timestamp": invoice.extraction_timestamp,
            "review_status": invoice.review_status,
            "reviewer": invoice.reviewer,
            "review_timestamp": invoice.review_timestamp,
            "review_notes": invoice.review_notes,
        }

    def _sanitize_for_json(self, obj):
        """Recursively convert payload objects to JSON-serializable primitives."""
        return self._sanitize_for_json_v2(obj)

    def _coerce_llm_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Best-effort extraction of JSON object from LLM output that may include noise or code fences.
        Returns a parsed dict if successful, otherwise None.
        """
        if not text:
            return None

        # 1) Fast path: direct JSON
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except Exception:
            pass

        # 2) Strip common code fences like ```json ... ```
        fenced = re.search(r"```(?:json)?\\s*(\\{.*?\\})\\s*```", text, re.DOTALL)
        if fenced:
            candidate = fenced.group(1)
            try:
                data = json.loads(candidate)
                return data if isinstance(data, dict) else None
            except Exception:
                pass

        # 3) Take substring from first '{' to last '}' and try to parse
        if "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            candidate = text[start:end]
            try:
                data = json.loads(candidate)
                return data if isinstance(data, dict) else None
            except Exception:
                pass

        # 4) Gentle single-quote to double-quote normalization on the candidate block
        if "{" in text and "}" in text:
            candidate = text[text.find("{"): text.rfind("}") + 1]
            try:
                normalized = candidate.replace("'", "\"")
                data = json.loads(normalized)
                return data if isinstance(data, dict) else None
            except Exception:
                pass

        return None

    def _sanitize_for_json_v2(
        self,
        data: Any,
        max_depth: int = 4,
        _depth: int = 0,
    ) -> Any:
        """Best-effort scrubber to make DI/canonical data JSON-safe and small."""
        if _depth >= max_depth:
            return str(data)

        # Primitives
        if data is None or isinstance(data, (str, int, float, bool)):
            return data

        # Dates → ISO strings
        if isinstance(data, (date, datetime)):
            return data.isoformat()

        # Decimals → float
        if isinstance(data, Decimal):
            return float(data)

        # Mappings/dicts
        if isinstance(data, Mapping):
            filtered: Dict[str, Any] = {}
            for k, v in data.items():
                # Only string keys, skip private-ish keys
                if not isinstance(k, str) or k.startswith("_"):
                    continue

                key = k.lower()
                # Drop obvious secrets
                if any(bad in key for bad in ("password", "secret", "token", "key")):
                    continue

                filtered[k] = self._sanitize_for_json_v2(v, max_depth=max_depth, _depth=_depth + 1)
            return filtered

        # Lists / tuples / sets
        if isinstance(data, (list, tuple, set)):
            return [
                self._sanitize_for_json_v2(v, max_depth=max_depth, _depth=_depth + 1)
                for v in list(data)[:64]  # cap length so payload stays small
            ]

        # Handle Azure SDK field objects like CurrencyValue by using amount/value/text
        if hasattr(data, "amount"):
            return self._sanitize_for_json_v2(getattr(data, "amount"), max_depth=max_depth, _depth=_depth + 1)
        if hasattr(data, "value"):
            return self._sanitize_for_json_v2(getattr(data, "value"), max_depth=max_depth, _depth=_depth + 1)
        if hasattr(data, "text"):
            return self._sanitize_for_json_v2(getattr(data, "text"), max_depth=max_depth, _depth=_depth + 1)

        # Everything else
        return str(data)

