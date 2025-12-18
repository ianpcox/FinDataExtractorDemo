"""Simplified extraction service with field extractor and database integration"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date
from decimal import Decimal
import logging
import json
import re
import hashlib
from typing import Any, Mapping, Dict

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

Formatting rules:
- Dates must be ISO 8601 date strings: "YYYY-MM-DD".
- Monetary amounts must be numeric, using "." as the decimal separator. Keep the original magnitude and currency implied by the invoice.
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
            else:
                invoice_before_llm = invoice.model_dump(mode="json")
                try:
                    self._run_low_confidence_fallback(
                        invoice=invoice,
                        low_conf_fields=low_conf_fields,
                        di_data=doc_intelligence_data,
                        di_field_confidence=fc,
                    )
                    llm_changed = invoice.model_dump(mode="json") != invoice_before_llm
                except Exception as e:
                    logger.exception("LLM fallback failed; continuing with DI-only invoice: %s", e)

            # Final save after LLM post-processing only when there was a change
            if llm_changed:
                logger.info("Saving extracted invoice to database (after LLM) for: %s", invoice_id)
                await DatabaseService.save_invoice(invoice, db=db)
            else:
                logger.info("Skipping post-LLM save; no LLM changes detected.")
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
    
    def _run_low_confidence_fallback(
        self,
        invoice: Invoice,
        low_conf_fields: List[str],
        di_data: Dict[str, Any],
        di_field_confidence: Dict[str, float],
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
            # Prepare sanitized DI snapshot for prompt/caching
            di_snapshot = {
                "di_fields": di_data or {},
                "di_field_confidence": di_field_confidence or {},
                "low_conf_fields": low_conf_fields,
            }
            di_snapshot = self._sanitize_for_json(di_snapshot)

            try:
                canonical_di = self.field_extractor.normalize_di_data(di_data or {})
            except Exception:
                canonical_di = di_data or {}

            prompt = self._build_llm_prompt(canonical_di, low_conf_fields, di_data)
            if not prompt:
                logger.info("No prompt built for LLM fallback; skipping.")
                return

            cache_key = (
                settings.AOAI_DEPLOYMENT_NAME or "",
                tuple(sorted(low_conf_fields)),
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

                logger.info("Calling Azure OpenAI chat.completions for LLM fallback.")
                resp = client.chat.completions.create(
                    model=settings.AOAI_DEPLOYMENT_NAME,
                    temperature=0.0,
                    messages=[
                        {"role": "system", "content": LLM_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                )

                if not resp.choices or not resp.choices[0].message or not resp.choices[0].message.content:
                    logger.warning("LLM fallback returned no content; skipping suggestions.")
                    return

                suggestion_text = resp.choices[0].message.content.strip()
                self._llm_cache[cache_key] = suggestion_text

            # Parse and apply suggestions (best-effort even if raw text is not strict JSON)
            llm_data = self._coerce_llm_json(suggestion_text)
            if llm_data is None:
                logger.error("LLM fallback returned non-JSON content; preserving raw text for debugging.")
                logger.debug("Raw LLM suggestion text: %s", suggestion_text)
                return

            if not isinstance(llm_data, dict):
                logger.error("LLM fallback JSON is not an object; got %s", type(llm_data))
                logger.debug("Raw LLM suggestion text: %s", suggestion_text)
                return

            self._apply_llm_suggestions(invoice, llm_data, low_conf_fields)
            logger.info("LLM fallback suggestions applied successfully.")

        except Exception as e:
            logger.exception("LLM fallback failed: %s", e)

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
        return json.dumps(payload, ensure_ascii=False, default=str)

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

        logger.info("LLM suggestions: %s", llm_suggestions)

        before = invoice.model_dump()
        for field, value in llm_suggestions.items():
            try:
                target_field = field
                if field == "payment_term":
                    target_field = "payment_terms"
                if field == "invoice_total":
                    target_field = "total_amount"
                if field == "purchase_order":
                    target_field = "po_number"

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
                invoice.field_confidence[target_field] = max(invoice.field_confidence.get(target_field, 0.0), 0.9)
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

