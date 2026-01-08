# Testing Guide

## Overview

The FinDataExtractorVanilla project includes a comprehensive test suite with unit and integration tests. Tests use mocks for external dependencies (Azure services) and in-memory SQLite for database tests.

## Quick Start

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=src --cov-report=html --cov-report=term
```

Coverage report will be available at `htmlcov/index.html`

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit -v

# Integration tests only
pytest tests/integration -v

# API tests only
pytest -m api -v
```

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── unit/                          # Unit tests
│   ├── test_ingestion_service.py
│   ├── test_extraction_service.py
│   ├── test_field_extractor.py
│   ├── test_db_service.py
│   ├── test_matching_service.py
│   ├── test_erp_staging.py
│   ├── test_pdf_overlay_renderer.py
│   └── test_subtype_extractors.py
└── integration/                   # Integration tests
    ├── test_api_routes.py
    └── test_end_to_end.py
```

## Test Coverage

### Current Coverage Goals
- **Minimum**: 70% overall coverage
- **Critical Paths**: 90%+ coverage
- **Target Areas**:
  - Ingestion service
  - Extraction service
  - Field extractor
  - Database service
  - Matching service
  - ERP staging
  - API routes

### View Coverage Report
```bash
# Generate HTML report
pytest --cov=src --cov-report=html

# Open in browser
# Windows: start htmlcov/index.html
# Mac: open htmlcov/index.html
# Linux: xdg-open htmlcov/index.html
```

## Writing Tests

### Unit Test Template
```python
import pytest
from unittest.mock import Mock, MagicMock

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

### Integration Test Template
```python
import pytest

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

## Test Fixtures

### Available Fixtures

- **`db_session`** - Async database session (SQLite in-memory)
- **`sample_invoice`** - Sample Invoice Pydantic model
- **`sample_pdf_content`** - Sample PDF bytes
- **`mock_file_handler`** - Mocked FileHandler
- **`mock_document_intelligence_client`** - Mocked Document Intelligence
- **`mock_pdf_processor`** - Mocked PDFProcessor
- **`sample_document_intelligence_data`** - Sample DI response
- **`sample_po_data`** - Sample PO data

## Test Markers

Use markers to categorize tests:

```python
@pytest.mark.unit              # Unit test
@pytest.mark.integration       # Integration test
@pytest.mark.api               # API test
@pytest.mark.slow              # Slow test
@pytest.mark.requires_db       # Requires database
@pytest.mark.requires_azure    # Requires Azure (will skip if not available)
```

## Continuous Integration

Tests run automatically in GitHub Actions:
- On every push to `main` or `dev`
- On pull requests
- Coverage reports uploaded to Codecov

## Best Practices

1. **Use Mocks**: Mock external dependencies (Azure, APIs)
2. **Isolation**: Each test should be independent
3. **Fast Tests**: Unit tests should run quickly (< 1 second)
4. **Clear Names**: Test names should describe what they test
5. **Coverage**: Aim for high coverage on critical paths
6. **Fixtures**: Use fixtures for reusable test data

## Troubleshooting

### Tests Failing
1. Check that all dependencies are installed: `pip install -r requirements.txt`
2. Verify database migrations: `alembic upgrade head`
3. Check test output for specific error messages

### Coverage Too Low
1. Identify untested code: `pytest --cov=src --cov-report=term-missing`
2. Add tests for missing coverage
3. Focus on critical paths first

### Slow Tests
1. Use `pytest -m "not slow"` to skip slow tests during development
2. Run specific test files instead of entire suite
3. Use `pytest -n auto` for parallel execution (requires pytest-xdist)

## Related Documentation

- [Test README](../tests/README.md) - Detailed test documentation
- [pytest.ini](../pytest.ini) - Pytest configuration
- [Architecture](./ARCHITECTURE.md) - System architecture

