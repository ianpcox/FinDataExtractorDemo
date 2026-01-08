# Dev vs Main Branch Comparison

## Summary Statistics

**Files Changed:** 334 files
- **Additions:** 55,285 lines
- **Deletions:** 427 lines
- **Net Change:** +54,858 lines

## Recent Commits in Dev (not in Main)

1. **0e008b7** - Add comprehensive extraction test suite and archive obsolete documentation
2. **1b8a590** - Add LLM and Multimodal LLM evaluation reports and comprehensive test suites
3. **7997779** - Add multimodal LLM fallback support and improve error handling for missing Azure credentials
4. **4373ac08** - Remove DEMO_MODE checks that disable DI OCR and LLM - always use real Azure services when configured
5. **8532acf** - Resolve all LLM re-extraction issues: async execution, cache TTL, configurable threshold, partial success, dynamic confidence, enhanced OCR, validation, and progress updates
6. **dbd24ec** - Fix: Add expected_processing_state parameter to set_extraction_result call after LLM extraction
7. **39ff29b** - Add re-extraction support with state reset and progress tracking
8. **2817203** - Add Key Vault fallback support for LLM and DI credentials
9. **4a362e4** - Remove all emojis from codebase
10. **124ca84** - UI improvements: fix LLM error handling, remove redundant banners, fix line item headers, move acceptance_percentage to line items

## Major Feature Additions

### 1. LLM and Multimodal LLM Support
- Base LLM fallback for low-confidence fields
- Multimodal LLM support for scanned PDFs
- Image rendering and caching
- Comprehensive test suites for both methods

### 2. Comprehensive Test Coverage
- Unit tests for DI, LLM, and Multimodal LLM field coverage
- Integration tests with real Azure services
- Error handling tests
- Performance tests
- Standalone test scripts for extraction evaluation

### 3. Documentation
- Field coverage reports (DI, LLM, Multimodal LLM)
- Behavior documentation
- Evaluation reports
- Architecture documentation updates
- Archived obsolete documentation

### 4. API Enhancements
- HITL (Human-In-The-Loop) API routes
- Progress tracking endpoints
- Batch processing support
- Azure import functionality
- ERP staging service
- PDF overlay rendering

### 5. Database Migrations
- Initial migration
- Contact, remit, and tax fields
- Bill-to address
- Concurrency fields
- Comprehensive invoice fields

### 6. Streamlit UI
- Complete HITL interface
- Form-based editing
- Progress tracking
- Error handling
- Field validation

### 7. Extraction Service Enhancements
- Async LLM calls
- TTL cache with LRU eviction
- Configurable confidence thresholds
- Partial success handling
- Dynamic confidence scoring
- Enhanced OCR snippets
- Response validation
- Progress updates

### 8. Sample Data
- 50+ sample invoices (Raw and Markedup)
- Demo scripts and guides
- Test data for various scenarios

## Key File Categories

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

### New Documentation
- `DI_CANONICAL_FIELD_COVERAGE_REPORT.md`
- `LLM_CANONICAL_FIELD_COVERAGE_REPORT.md`
- `MULTIMODAL_LLM_CANONICAL_FIELD_COVERAGE_REPORT.md`
- `LLM_BEHAVIOR_DOCUMENTATION.md`
- `MULTIMODAL_LLM_BEHAVIOR_DOCUMENTATION.md`
- `LLM_EXTRACTION_EVALUATION_REPORT.md`
- `MULTIMODAL_LLM_EXTRACTION_EVALUATION_REPORT.md`
- `docs/ARCHITECTURE.md` (updated)
- `docs/ARB-architecture-overview.md` (updated)

### New API Routes
- `api/routes/hitl.py` (1,393 lines)
- `api/routes/progress.py`
- `api/routes/batch.py`
- `api/routes/staging.py`
- `api/routes/overlay.py`
- `api/routes/azure_import.py`

### Core Service Enhancements
- `src/extraction/extraction_service.py` (major updates, +2,390 lines)
- `src/extraction/field_extractor.py` (new, 793 lines)
- `src/services/db_service.py` (new, 493 lines)
- `src/services/validation_service.py` (new, 330 lines)
- `src/services/progress_tracker.py` (new, 211 lines)
- `src/erp/staging_service.py` (new, 587 lines)
- `src/erp/pdf_overlay_renderer.py` (new, 293 lines)

### UI
- `streamlit_app.py` (new, 1,883 lines)

## Archived Files

All obsolete documentation moved to `docs/archive/`:
- Fix verification documents
- Old project summaries
- Test failure documentation
- Old code reviews

## Infrastructure

- GitHub Actions workflows (CI/CD, tests)
- Azure infrastructure scripts (Bicep, PowerShell)
- Export pack for Azure resource migration
- Demo scripts and guides

## Next Steps

Consider merging dev to main when:
- All tests are passing
- Documentation is complete
- Code review is complete
- Production deployment is ready
