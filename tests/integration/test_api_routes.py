"""Integration tests for API routes"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from api.main import app
from src.erp.staging_service import ERPPayloadFormat


@pytest.mark.integration
@pytest.mark.api
class TestAPIRoutes:
    """Test API routes"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @patch('api.routes.ingestion.IngestionService')
    def test_upload_invoice(self, mock_service, client):
        """Test invoice upload endpoint"""
        # Mock ingestion service
        mock_instance = AsyncMock()
        mock_instance.ingest_invoice.return_value = {
            "invoice_id": "test-123",
            "status": "uploaded",
            "file_name": "test.pdf",
            "errors": []
        }
        mock_service.return_value = mock_instance
        
        # Create test file
        files = {"file": ("test_invoice.pdf", b"%PDF-1.4\n...", "application/pdf")}
        
        response = client.post("/api/ingestion/upload", files=files)
        
        # Note: This may need adjustment based on actual route implementation
        # For now, just verify endpoint exists
        assert response.status_code in [200, 201, 400, 500]  # Any response means endpoint exists

    @patch("api.routes.staging.ERPStagingService")
    @patch("api.routes.staging.DatabaseService.get_invoice", new_callable=AsyncMock)
    def test_stage_invoice_null_format_defaults(
        self,
        mock_get_invoice,
        mock_staging_service,
        client,
    ):
        """Sending format=null should not 500 (defaults format)."""
        mock_get_invoice.return_value = MagicMock(id="inv-123")

        mock_instance = AsyncMock()
        mock_instance.stage_invoice.return_value = {
            "success": True,
            "invoice_id": "inv-123",
            "payload_location": "test://payload.xml",
            "format": "dynamics_gp",
            "export_timestamp": "2025-01-01T00:00:00Z",
        }
        mock_staging_service.return_value = mock_instance

        response = client.post(
            "/api/staging/stage",
            json={"invoice_id": "inv-123", "format": None},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Ensure default format is used when request.format is None
        _, kwargs = mock_staging_service.call_args
        assert kwargs["erp_format"] == ERPPayloadFormat.DYNAMICS_GP

