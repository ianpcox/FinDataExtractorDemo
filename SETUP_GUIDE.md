# Setup Guide - FinDataExtractor Vanilla

## Quick Setup Checklist

- [ ] Clone repository
- [ ] Create virtual environment
- [ ] Install dependencies
- [ ] Configure environment variables
- [ ] Initialize database
- [ ] Start the application

## Detailed Steps

### 1. Repository Setup

```bash
# Clone the repository
git clone <repository-url>
cd FinDataExtractorVanilla
```

### 2. Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the root directory:

```env
# Required: Azure Document Intelligence
AZURE_FORM_RECOGNIZER_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_FORM_RECOGNIZER_KEY=your-api-key-here

# Optional: Database (defaults to SQLite)
DATABASE_URL=sqlite+aiosqlite:///./findataextractor.db

# Optional: Storage (defaults to local)
LOCAL_STORAGE_PATH=./storage
```

### 5. Database Initialization

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

### 6. Start Application

```bash
uvicorn api.main:app --reload
```

### 7. Verify Setup

1. Open http://localhost:8000/docs
2. Check that API documentation loads
3. Test health endpoint: http://localhost:8000/health

## Next Steps

- Read [Getting Started Guide](docs/GETTING_STARTED.md)
- Review [Architecture Overview](docs/ARCHITECTURE.md)
- Check [Repository Relationship](docs/REPOSITORY_RELATIONSHIP.md)

## Troubleshooting

### Import Errors

If you see import errors, ensure:
- Virtual environment is activated
- All dependencies are installed: `pip install -r requirements.txt`
- You're running from the project root directory

### Azure Configuration Errors

If Azure Document Intelligence fails:
- Verify endpoint URL is correct
- Check API key is valid
- Ensure Azure subscription is active

### Database Errors

If database operations fail:
- Check file permissions for SQLite database
- Verify DATABASE_URL is correct
- Ensure migrations have been run: `alembic upgrade head`

## Support

For issues or questions:
1. Check the [README](README.md)
2. Review [Documentation](docs/)
3. Create an issue in the repository

