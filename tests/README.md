# Test Suite for FinDataExtractorVanilla

## Overview

Comprehensive test suite for the vanilla invoice processing system. Tests are organized into unit tests and integration tests, with mocks for external dependencies.

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Unit Tests Only
```bash
pytest tests/unit -v
```

### Run Integration Tests Only
```bash
pytest tests/integration -v
```

### Run with Coverage
```bash
pytest --cov=src --cov-report=html --cov-report=term
```

Coverage report will be generated in:
- HTML: `htmlcov/index.html`
- Terminal: displayed in console
- JSON: `coverage.json`

### Run Specific Test File
```bash
pytest tests/unit/test_ingestion_service.py -v
```

### Run Tests in Parallel
```bash
pytest -n auto
```

(Requires `pytest-xdist`: `pip install pytest-xdist`)

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (fast, mocked)
│   ├── test_ingestion_service.py
│   ├── test_extraction_service.py
│   ├── test_field_extractor.py
│   ├── test_db_service.py
│   ├── test_matching_service.py
│   └── test_erp_staging.py
└── integration/             # Integration tests
    ├── test_api_routes.py
    └── test_end_to_end.py
```

## Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.unit` - Unit tests (use mocks, fast)
- `@pytest.mark.integration` - Integration tests (use test database)
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.slow` - Slow running tests (> 5 seconds)
- `@pytest.mark.requires_db` - Tests requiring database
- `@pytest.mark.requires_azure` - Tests requiring Azure services (will skip if not available)

### Filter by Marker
```bash
# Run only unit tests
pytest -m unit

# Run only fast tests (exclude slow)
pytest -m "not slow"

# Run integration tests
pytest -m integration
```

## Test Fixtures

### Database Fixtures
- `db_session` - Async database session (SQLite in-memory)
- Creates fresh database for each test
- Automatically cleaned up after test

### Mock Fixtures
- `mock_file_handler` - Mocked FileHandler
- `mock_document_intelligence_client` - Mocked Document Intelligence
- `mock_pdf_processor` - Mocked PDFProcessor

### Data Fixtures
- `sample_invoice` - Sample Invoice Pydantic model
- `sample_pdf_content` - Sample PDF bytes
- `sample_document_intelligence_data` - Sample DI response
- `sample_po_data` - Sample PO data for matching

## Coverage Goals

- **Target**: 70% minimum code coverage
- **Critical Paths**: 90%+ coverage
- **Current**: Run `pytest --cov=src --cov-report=term` to see current coverage

## Writing New Tests

### Unit Test Example
```python
@pytest.mark.unit
class TestMyService:
    """Test MyService"""
    
    @pytest.mark.asyncio
    async def test_my_method(self, mock_dependency):
        """Test my method"""
        service = MyService(dependency=mock_dependency)
        result = await service.my_method()
        assert result is not None
```

### Integration Test Example
```python
@pytest.mark.integration
@pytest.mark.requires_db
class TestMyIntegration:
    """Test integration"""
    
    @pytest.mark.asyncio
    async def test_integration(self, db_session):
        """Test integration"""
        # Use real database session
        result = await my_function(db=db_session)
        assert result is not None
```

## Test Data

Test data is created using fixtures in `conftest.py`. For file-based test data, create:
```
tests/
└── fixtures/
    ├── sample_invoices/
    └── sample_pos/
```

## Continuous Integration

Tests should run automatically in CI/CD pipeline:
- On every commit
- Before merging PRs
- Coverage reports published

## Notes

- All tests use mocks for Azure services by default
- Database tests use in-memory SQLite (no external DB required)
- Integration tests may require test database setup
- Azure connection tests are optional and will skip if credentials not available

