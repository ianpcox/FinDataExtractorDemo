# Pull Request: Merge dev into main

## Summary

This PR merges the `dev` branch into `main`, bringing significant enhancements including LLM and Multimodal LLM support, comprehensive test coverage, HITL API, Streamlit UI, and extensive documentation.

## Statistics

- **Commits:** 66 commits ahead of main
- **Files Changed:** 334 files
- **Lines Added:** 55,285
- **Lines Deleted:** 427
- **Net Change:** +54,858 lines

## Major Features

### 1. LLM and Multimodal LLM Support
- ✅ Base LLM fallback for low-confidence field extraction
- ✅ Multimodal LLM support for scanned PDFs with image rendering
- ✅ Async LLM calls with TTL cache and LRU eviction
- ✅ Configurable confidence thresholds
- ✅ Dynamic confidence scoring
- ✅ Enhanced OCR snippets for better context
- ✅ Response validation and error handling
- ✅ Progress tracking during LLM calls

### 2. Comprehensive Test Coverage
- ✅ Unit tests for DI, LLM, and Multimodal LLM field coverage (75%+ target)
- ✅ Integration tests with real Azure services
- ✅ Error handling tests for all extraction methods
- ✅ Performance tests for multimodal image rendering
- ✅ Standalone test scripts for extraction evaluation
- ✅ Test reports and CSV outputs

### 3. HITL (Human-In-The-Loop) Interface
- ✅ Complete Streamlit UI (1,883 lines)
- ✅ Form-based field editing
- ✅ Progress tracking and status updates
- ✅ Error handling and validation
- ✅ HITL API routes (1,393 lines)

### 4. Documentation
- ✅ Field coverage reports (DI, LLM, Multimodal LLM)
- ✅ Behavior documentation for LLM and Multimodal LLM
- ✅ Evaluation reports with test results
- ✅ Architecture documentation updates
- ✅ Obsolete documentation archived

### 5. API Enhancements
- ✅ HITL API endpoints
- ✅ Progress tracking endpoints
- ✅ Batch processing support
- ✅ Azure import functionality
- ✅ ERP staging service
- ✅ PDF overlay rendering

### 6. Database Migrations
- ✅ Initial migration
- ✅ Contact, remit, and tax fields
- ✅ Bill-to address
- ✅ Concurrency fields
- ✅ Comprehensive invoice fields

### 7. Extraction Service Enhancements
- ✅ Async execution for LLM calls
- ✅ Partial success handling
- ✅ Key Vault fallback for credentials
- ✅ Removed DEMO_MODE checks (always use real services)
- ✅ Enhanced field extraction (53 canonical fields)

## Key Files Added/Modified

### New Test Files
- `test_di_ocr_extraction_standalone.py`
- `test_llm_extraction_standalone.py`
- `test_multimodal_llm_extraction_standalone.py`
- `run_comprehensive_extraction_tests.py`
- `tests/integration/test_real_llm_extraction.py`
- `tests/integration/test_real_multimodal_llm_extraction.py`
- `tests/integration/test_llm_error_handling.py`
- `tests/integration/test_multimodal_llm_error_handling.py`
- `tests/integration/test_multimodal_llm_performance.py`
- `tests/unit/test_di_canonical_field_coverage.py`
- `tests/unit/test_llm_canonical_field_coverage.py`
- `tests/unit/test_multimodal_llm_canonical_field_coverage.py`

### Core Service Files
- `src/extraction/extraction_service.py` (major updates, +2,390 lines)
- `src/extraction/field_extractor.py` (new, 793 lines)
- `src/services/db_service.py` (new, 493 lines)
- `src/services/validation_service.py` (new, 330 lines)
- `src/services/progress_tracker.py` (new, 211 lines)
- `src/erp/staging_service.py` (new, 587 lines)

### API Routes
- `api/routes/hitl.py` (new, 1,393 lines)
- `api/routes/progress.py` (new)
- `api/routes/batch.py` (new)
- `api/routes/staging.py` (new)

### UI
- `streamlit_app.py` (new, 1,883 lines)

## Recent Commits (Last 10)

1. **0e008b7** - Add comprehensive extraction test suite and archive obsolete documentation
2. **1b8a590** - Add LLM and Multimodal LLM evaluation reports and comprehensive test suites
3. **7997779** - Add multimodal LLM fallback support and improve error handling
4. **4373ac08** - Remove DEMO_MODE checks - always use real Azure services
5. **8532acf** - Resolve all LLM re-extraction issues
6. **dbd24ec** - Fix: Add expected_processing_state parameter
7. **39ff29b** - Add re-extraction support with state reset
8. **2817203** - Add Key Vault fallback support
9. **4a362e4** - Remove all emojis from codebase
10. **124ca84** - UI improvements and fixes

## Testing

- ✅ All unit tests passing
- ✅ Integration tests with real Azure services
- ✅ Comprehensive field coverage tests (75%+ target)
- ✅ Error handling tests
- ✅ Performance tests

## Breaking Changes

None - this is a feature addition that maintains backward compatibility.

## Migration Notes

- Database migrations included (run `alembic upgrade head`)
- Configuration updates may be needed for LLM settings
- Key Vault fallback is optional but recommended

## Checklist

- [x] Code follows project style guidelines
- [x] Tests added/updated and passing
- [x] Documentation updated
- [x] No breaking changes
- [x] Database migrations included
- [x] Configuration documented

## Related Issues

- LLM fallback implementation
- Multimodal LLM support
- Comprehensive test coverage
- HITL interface development
