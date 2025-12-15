# Repository Relationship Guide

## Overview

**FinDataExtractor Vanilla** is a simplified, user-friendly version of the full **FinDataExtractor** system. This document explains the relationship between the two repositories and when to use each.

## Repository Structure

```
GitHub Organization:
├── FinDataExtractor          # Full-featured enterprise version
└── FinDataExtractorVanilla    # Simplified version (this repo)
```

## Key Differences

### FinDataExtractor (Full Version)

**Target Audience**: Enterprise users, developers, advanced use cases

**Features**:
- ✅ Full ML observability and A/B testing
- ✅ Event sourcing and saga patterns
- ✅ Complex workflow orchestration
- ✅ Advanced Azure Key Vault integration
- ✅ API versioning
- ✅ Dead letter queues
- ✅ Circuit breakers and advanced retry logic
- ✅ Comprehensive error handling
- ✅ Full database schema with ML tables

**Use When**:
- You need enterprise-grade features
- You require ML observability
- You need complex workflow orchestration
- You want advanced error handling patterns
- You have a dedicated DevOps team

### FinDataExtractor Vanilla (This Version)

**Target Audience**: CATSA users, simple deployments, quick setup

**Features**:
- ✅ Core invoice ingestion
- ✅ Data extraction with Azure Document Intelligence
- ✅ Basic validation
- ✅ Simple document matching
- ✅ Straightforward REST API
- ✅ Local or Azure storage
- ✅ Simplified configuration

**Use When**:
- You need basic invoice processing
- You want simple setup and configuration
- You don't need advanced ML features
- You prefer straightforward documentation
- You want to get started quickly

## Code Relationship

### Shared Concepts

Both versions share:
- Core invoice processing workflow
- Azure Document Intelligence integration
- Basic data models (Invoice, LineItem, Address)
- PDF validation logic

### Implementation Differences

| Feature | Full Version | Vanilla Version |
|---------|-------------|-----------------|
| Configuration | Azure Key Vault + env vars | Simple env vars only |
| API Structure | Versioned (`/api/v1/...`) | Non-versioned (`/api/...`) |
| Storage | Azure Blob Storage (required) | Local or Azure (optional) |
| Database | Azure SQL (production) | SQLite (default) |
| Error Handling | Circuit breakers, retries, DLQ | Basic error handling |
| Workflow | Saga patterns, event sourcing | Simple linear flow |
| ML Features | Full observability, A/B testing | None |

## Migration Path

### From Vanilla to Full Version

If you start with Vanilla and need more features:

1. **Data Migration**: Export data from Vanilla database
2. **Configuration**: Set up Azure Key Vault and full Azure services
3. **Code Migration**: Adapt API calls to versioned endpoints
4. **Feature Enablement**: Enable ML observability, workflows, etc.

### From Full to Vanilla

If you want to simplify:

1. **Feature Removal**: Remove ML, event sourcing, saga patterns
2. **Configuration Simplification**: Remove Key Vault, use env vars
3. **API Simplification**: Remove versioning, simplify endpoints
4. **Storage Simplification**: Option to use local storage

## Maintenance Strategy

### Independent Development

- Each repository is maintained independently
- Vanilla version focuses on simplicity and ease of use
- Full version focuses on enterprise features

### Code Sharing

- Core concepts are shared but implementations differ
- No direct code dependencies between repositories
- Each can evolve independently

### Bug Fixes

- Critical bugs in shared logic should be fixed in both
- Feature-specific bugs are fixed in respective repository
- Security fixes should be applied to both

## Version Compatibility

### API Compatibility

- **Full Version**: Versioned APIs (`/api/v1/...`)
- **Vanilla Version**: Non-versioned APIs (`/api/...`)
- APIs are **not compatible** - different endpoints

### Data Compatibility

- Database schemas are different
- Data models are similar but not identical
- Migration scripts would be needed to move data

## Recommendations

### For New Users

1. **Start with Vanilla** if you:
   - Need quick setup
   - Don't need advanced features
   - Want simple configuration

2. **Start with Full Version** if you:
   - Need enterprise features
   - Have DevOps support
   - Require ML observability

### For Existing Users

- **Vanilla Users**: Upgrade to Full Version when you need:
  - ML observability
  - Complex workflows
  - Advanced error handling

- **Full Version Users**: Consider Vanilla if you:
  - Want to simplify deployment
  - Don't use advanced features
  - Need easier maintenance

## Support and Documentation

- **Vanilla Documentation**: Focuses on quick start and simplicity
- **Full Version Documentation**: Comprehensive enterprise documentation
- Both have separate issue trackers and support channels

## License

Both repositories maintain the same license (to be determined).

