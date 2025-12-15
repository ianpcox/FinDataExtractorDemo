# Azure Setup Guide - FinDataExtractor Vanilla

## Overview

This guide covers Azure resource setup for FinDataExtractor Vanilla. You have two options:

1. **Separate Azure Resources** (Recommended) - Complete independence
2. **Shared Resources** - Use existing FinDataExtractor resources with separate containers

## Recommended: Separate Azure Resources

### Why Separate Resources?

- ✅ **Complete Independence** - No coupling with full version
- ✅ **Isolated Scaling** - Scale resources independently
- ✅ **Separate Cost Tracking** - Clear billing separation
- ✅ **Different Access Controls** - Different security requirements
- ✅ **Safe Testing** - Test changes without affecting production
- ✅ **Different Resource Tiers** - Optimize costs for simpler needs

### Required Azure Resources

#### 1. Azure Document Intelligence (Required)

**Option A: New Resource (Recommended)**
- Create a new Document Intelligence resource
- Lower tier may be sufficient (S0 tier for basic needs)
- Separate endpoint and API key

**Option B: Shared Resource**
- Use existing Document Intelligence resource
- Same endpoint, but consider rate limits
- Good for development/testing

**Setup:**
```bash
# Get from Azure Portal
AZURE_FORM_RECOGNIZER_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=your-api-key-here
```

#### 2. Azure Storage Account (Optional - Recommended for Production)

**Option A: New Storage Account (Recommended)**
- Create dedicated storage account
- Use separate containers: `vanilla-invoices-raw`, `vanilla-invoices-processed`
- Better isolation and cost tracking

**Option B: Shared Storage Account**
- Use existing storage account
- Use separate containers with `vanilla-` prefix
- Example: `vanilla-invoices-raw` vs `invoices-raw`
- Good for development, less ideal for production

**Container Naming:**
```
vanilla-invoices-raw          # Raw uploaded invoices
vanilla-invoices-processed     # Processed invoices
```

**Setup:**
```bash
# Option A: New Storage Account
AZURE_STORAGE_ACCOUNT_NAME=findataextractorvanilla
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...

# Option B: Shared Storage Account
AZURE_STORAGE_ACCOUNT_NAME=findataextractor  # Existing account
AZURE_STORAGE_CONNECTION_STRING=...          # Existing connection string
AZURE_STORAGE_CONTAINER_RAW=vanilla-invoices-raw
AZURE_STORAGE_CONTAINER_PROCESSED=vanilla-invoices-processed
```

#### 3. Azure SQL Database (Optional - Only for Production)

**Recommendation: Separate Database**
- Create new Azure SQL database: `FinDataExtractorVanilla`
- Use lower tier (Basic or S0) if volume is lower
- Separate from full version database

**Alternative: SQLite for Development**
- Vanilla version defaults to SQLite
- Perfect for local development and testing
- No Azure SQL needed until production

**Setup:**
```bash
# Development (SQLite - default)
DATABASE_URL=sqlite+aiosqlite:///./findataextractor.db

# Production (Azure SQL)
DATABASE_URL=mssql+pyodbc://user:password@server:1433/database?driver=SQL+Server&Encrypt=yes
```

## Alternative: Shared Resources (Development Only)

If you want to use existing Azure resources for development/testing:

### Shared Document Intelligence
- ✅ Same endpoint and key
- ⚠️ Watch rate limits if both projects are active
- ⚠️ Cost attribution is shared

### Shared Storage Account
- ✅ Use separate containers with `vanilla-` prefix
- ✅ Easy to set up
- ⚠️ Less isolation
- ⚠️ Shared quotas and limits

**Container Strategy:**
```
Existing Containers:
- invoices-raw
- invoices-processed

Vanilla Containers (separate):
- vanilla-invoices-raw
- vanilla-invoices-processed
```

## Cost Considerations

### Separate Resources (Recommended)

| Resource | Estimated Monthly Cost |
|----------|----------------------|
| Document Intelligence (S0) | $0.0015 per page |
| Storage Account (LRS) | ~$0.018/GB |
| Azure SQL (Basic) | ~$5/month |
| **Total (low volume)** | **~$10-20/month** |

### Shared Resources

| Resource | Additional Cost |
|----------|----------------|
| Document Intelligence | Same (shared usage) |
| Storage Account | Minimal (just containers) |
| Database | $0 (use SQLite) |
| **Total** | **~$0-5/month** |

## Setup Steps

### Option 1: New Azure Resources (Recommended)

1. **Create Document Intelligence Resource**
   ```bash
   # Azure Portal > Create Resource > Document Intelligence
   # Tier: S0 (pay-as-you-go) or F0 (free tier for testing)
   # Get endpoint and key
   ```

2. **Create Storage Account**
   ```bash
   # Azure Portal > Create Resource > Storage Account
   # Performance: Standard
   # Redundancy: LRS (for cost savings)
   # Create containers: vanilla-invoices-raw, vanilla-invoices-processed
   ```

3. **Create Azure SQL (Optional - Production Only)**
   ```bash
   # Azure Portal > Create Resource > Azure SQL Database
   # Tier: Basic or S0
   # Database name: FinDataExtractorVanilla
   ```

### Option 2: Shared Resources (Development)

1. **Use Existing Document Intelligence**
   - Copy endpoint and key from full version
   - Add to `.env` file

2. **Use Existing Storage Account**
   - Use existing connection string
   - Create new containers: `vanilla-invoices-raw`, `vanilla-invoices-processed`
   - Update `.env` with container names

3. **Use SQLite (Default)**
   - No Azure SQL needed for development
   - Database file: `./findataextractor.db`

## Environment Configuration

### Development (Shared Resources)

```env
# Azure Document Intelligence (shared)
AZURE_FORM_RECOGNIZER_ENDPOINT=https://existing-resource.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=existing-key

# Azure Storage (shared account, separate containers)
AZURE_STORAGE_ACCOUNT_NAME=findataextractor
AZURE_STORAGE_CONNECTION_STRING=existing-connection-string
AZURE_STORAGE_CONTAINER_RAW=vanilla-invoices-raw
AZURE_STORAGE_CONTAINER_PROCESSED=vanilla-invoices-processed

# Database (SQLite - no Azure needed)
DATABASE_URL=sqlite+aiosqlite:///./findataextractor.db
```

### Production (Separate Resources)

```env
# Azure Document Intelligence (dedicated)
AZURE_FORM_RECOGNIZER_ENDPOINT=https://vanilla-resource.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=vanilla-key

# Azure Storage (dedicated account)
AZURE_STORAGE_ACCOUNT_NAME=findataextractorvanilla
AZURE_STORAGE_CONNECTION_STRING=vanilla-connection-string
AZURE_STORAGE_CONTAINER_RAW=invoices-raw
AZURE_STORAGE_CONTAINER_PROCESSED=invoices-processed

# Database (Azure SQL - production)
DATABASE_URL=mssql+pyodbc://user:password@vanilla-server:1433/FinDataExtractorVanilla?driver=SQL+Server&Encrypt=yes
```

## Recommendation Summary

### For Development/Testing
- ✅ **Shared Document Intelligence** - Same endpoint/key
- ✅ **Shared Storage Account** - Separate containers (`vanilla-*`)
- ✅ **SQLite Database** - No Azure SQL needed

### For Production
- ✅ **Separate Document Intelligence** - Dedicated resource
- ✅ **Separate Storage Account** - Complete isolation
- ✅ **Separate Azure SQL** - Or continue with SQLite if volume is low

## Migration Path

1. **Start with Shared Resources** (development)
   - Quick setup
   - Low cost
   - Easy testing

2. **Move to Separate Resources** (production)
   - When ready for production
   - When you need isolation
   - When cost tracking becomes important

## Security Considerations

- **Separate Resources**: Better security isolation
- **Shared Resources**: Ensure proper access controls and container-level permissions
- **Key Management**: Vanilla uses env vars (simpler), full version uses Key Vault (more secure)

## Next Steps

1. Choose your approach (shared for dev, separate for prod)
2. Set up Azure resources
3. Configure `.env` file
4. Test connection: `python scripts/verify_config.py` (if you create one)
5. Start using the system

