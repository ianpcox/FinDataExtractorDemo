"""Simplified FastAPI application entry point"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Setup logging
from src.logging_config import setup_logging
setup_logging()

load_dotenv()

app = FastAPI(
    title="FinDataExtractor Vanilla API",
    description="Simplified Invoice Processing System",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def _init_database() -> None:
    """Ensure database tables exist (demo-friendly)."""
    from src.models.database import Base, engine
    # Import all models to ensure they're registered with Base
    from src.models.db_models import Invoice  # noqa: F401
    from src.models.line_item_db_models import LineItem  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "FinDataExtractor Vanilla API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


# Import routes
from api.routes import ingestion, extraction, matching, overlay, hitl, staging, azure_import, batch, progress
app.include_router(ingestion.router, prefix="/api", tags=["ingestion"])
app.include_router(extraction.router, prefix="/api", tags=["extraction"])
app.include_router(matching.router, prefix="/api", tags=["matching"])
app.include_router(overlay.router, prefix="/api", tags=["overlay"])
app.include_router(hitl.router, prefix="/api", tags=["hitl"])
app.include_router(staging.router, prefix="/api", tags=["staging"])
app.include_router(azure_import.router, prefix="/api", tags=["azure-import"])
app.include_router(batch.router, tags=["batch"])
app.include_router(progress.router, prefix="/api", tags=["progress"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

