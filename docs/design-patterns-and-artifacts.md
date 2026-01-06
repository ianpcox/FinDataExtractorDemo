# Design Patterns and Corresponding Artifacts

| Pattern / Practice | Context & Purpose | Key Artifacts |
| --- | --- | --- |
| Adapter / Mapping | Isolate Azure Document Intelligence field names from the canonical model; prioritize DI totals/POs; merge PST/QST; apply acceptance %. | `src/extraction/field_extractor.py` (`DI_TO_CANONICAL`, `_extract_line_items`, `extract_invoice`) |
| Sanitizer / Defensive Serialization | Ensure prompt/response payloads are JSON-safe (dates, decimals, SDK objects), filter secrets, cap sizes. | `src/extraction/extraction_service.py` (`_sanitize_for_json_v2`) |
| Minimal Prompt Payload | Reduce token use and focus LLM on low-confidence fields with OCR snippet only. | `src/extraction/extraction_service.py` (`_build_llm_prompt`, `_build_content_snippet`) |
| Guarded LLM Fallback | Best-effort fallback that never blocks pipeline; stop on 429, log, cache, and skip on errors. | `src/extraction/extraction_service.py` (`_run_low_confidence_fallback`, `_apply_llm_suggestions`) |
| Caching | Avoid repeat LLM calls for same file+fields+snapshot. | `src/extraction/extraction_service.py` (`self._llm_cache` usage) |
| Rate-limit Jitter / Grouping | Group header/address/line-items into separate calls with delays to mitigate 429. | `src/extraction/extraction_service.py` (grouping logic and `time.sleep` jitter) |
| Safe Parsing / Validation | Prevent crashes on user/DI input (decimals, confidences) by defaulting or skipping bad values. | `api/routes/hitl.py` (`_parse_decimal_safe`); `src/extraction/field_extractor.py` (confidence defaults) |
| Non-mutating Suggestions Endpoint | Serve LLM suggestions side-by-side without mutating invoice until user applies. | `api/routes/hitl.py` (`/api/hitl/invoice/{id}/review`) |
| Explicit Persistence Control | Separate “Save to DB” from “Submit Validation”; offline queue retries failed saves. | `streamlit_app.py` (persistence buttons, offline queue) |
| Health Check / Observability | Detect DB issues early; provide ops visibility for blob extraction and LLM behavior. | `api/routes/ingestion.py` (DB health endpoints, blob listing/extract); logging in extraction/LLM paths |
| UI Fresh-Data Policy | Remove caching to always pull latest invoice state. | `streamlit_app.py` (removed `@st.cache_data` on loads) |

