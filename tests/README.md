# Test Organization

Tests are organized by **environment** (DEMO/DEV/PROD) and **test pyramid** (unit/integration/e2e).

## Structure

```
tests/
├── demo/          # Quick, standalone tests for demos
│   ├── unit/      # (empty - for future demo unit tests)
│   ├── integration/ # Standalone extraction tests (no DB) - 8 files
│   └── e2e/       # Simple end-to-end scripts - 1 file
│
├── dev/           # Development tests with mocks
│   ├── unit/      # Fast, isolated unit tests - 30 files
│   ├── integration/ # Integration tests with mocked services - 9 files
│   └── e2e/       # End-to-end tests with mocks - 1 file
│
├── prod/          # Production tests with real services
│   ├── unit/      # (empty - for future prod unit tests)
│   ├── integration/ # Real service integration tests - 13 files
│   └── e2e/       # Performance and scalability tests - 2 files
│
├── reports/       # Test reports and results
│   ├── di_ocr/    # DI OCR test reports - 4 files
│   ├── llm/       # Base LLM test reports - 4 files
│   ├── multimodal_llm/ # Multimodal LLM test reports - 4 files
│   ├── confusion_matrices/ # Confusion matrix reports - 4 files
│   └── metrics/   # Comprehensive metrics reports - 7 files
│
├── scripts/       # Test runner scripts - 4 files
└── utils/         # Test utility scripts - 7 files
```

## Test Categories

### DEMO Tests
- **Purpose**: Quick, standalone tests for demonstrations
- **Characteristics**: 
  - No database dependencies
  - Simple script-style tests
  - Can run without full environment setup
- **Examples**: Standalone extraction tests, simple real extraction scripts

### DEV Tests
- **Purpose**: Development and CI/CD testing
- **Characteristics**:
  - Use mocks for external services
  - Fast execution
  - No real Azure service calls
  - Isolated test databases
- **Examples**: Unit tests, integration tests with mocks, HITL tests

### PROD Tests
- **Purpose**: Production validation and performance testing
- **Characteristics**:
  - Real Azure service calls (DI, LLM, Blob Storage)
  - Comprehensive integration tests
  - Performance benchmarks
  - May require credentials and incur costs
- **Examples**: Real extraction tests, performance tests, migration tests

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run by environment
```bash
# Demo tests only
pytest tests/demo/

# Dev tests only (fast, with mocks)
pytest tests/dev/

# Prod tests only (requires Azure credentials)
pytest tests/prod/
```

### Run by test pyramid level
```bash
# Unit tests only
pytest tests/*/unit/

# Integration tests only
pytest tests/*/integration/

# E2E tests only
pytest tests/*/e2e/
```

### Run specific category
```bash
# Fast dev unit tests
pytest tests/dev/unit/

# Real service integration tests
pytest tests/prod/integration/
```

## Test Markers

Tests are marked with pytest markers:
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests (real services)
- `@pytest.mark.asyncio` - Async tests

## Test Reports

Test reports are organized in `tests/reports/` by test type:
- **di_ocr/** - Document Intelligence OCR test reports
- **llm/** - Base LLM extraction test reports
- **multimodal_llm/** - Multimodal LLM extraction test reports
- **confusion_matrices/** - Confusion matrix analysis
- **metrics/** - Comprehensive metrics reports

## Test Scripts

Test runner scripts are in `tests/scripts/`:
- `run_di_ocr_with_false_negative_detection.py`
- `run_llm_extraction_with_false_negative_detection.py`
- `run_multimodal_llm_extraction_with_false_negative_detection.py`
- `run_comprehensive_extraction_tests.py`

## Test Utilities

Utility scripts for test analysis are in `tests/utils/`:
- `enhanced_false_negative_detector.py`
- `false_negatives_detector.py`
- `generate_confusion_matrices.py`
- `generate_per_field_metrics.py`
- `diagnose_*.py` - Diagnostic scripts

## Notes

- **DEMO tests** are simple scripts that can run standalone
- **DEV tests** use mocks and are suitable for CI/CD
- **PROD tests** require Azure credentials and may incur costs
- Duplicate tests have been merged or removed
- All tests follow the test pyramid principle (many unit, some integration, few e2e)
- All test reports and scripts are organized within the `tests/` directory
