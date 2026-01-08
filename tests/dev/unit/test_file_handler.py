"""Unit tests for FileHandler (local storage path)."""

from pathlib import Path

import pytest

from src.ingestion.file_handler import FileHandler


@pytest.mark.unit
class TestFileHandler:
    def test_local_upload_download_and_paths(self, tmp_path: Path):
        handler = FileHandler(storage_path=str(tmp_path), use_azure=False)

        content = b"hello-world"
        upload = handler.upload_file(file_content=content, file_name="invoice.pdf")

        assert upload["storage_type"] == "local"
        assert upload["size"] == len(content)
        assert upload["original_filename"] == "invoice.pdf"
        assert Path(upload["file_path"]).exists()

        # Download via absolute path
        assert handler.download_file(upload["file_path"]) == content

        # Download via stored name (relative to raw/)
        assert handler.download_file(upload["stored_name"]) == content

        # Download via legacy "storage/raw/" prefix
        assert handler.download_file(f"storage/raw/{upload['stored_name']}") == content

        # get_file_path mirrors the same rules
        assert handler.get_file_path(upload["file_path"]) == upload["file_path"]
        assert handler.get_file_path(upload["stored_name"]).endswith(f"/raw/{upload['stored_name']}")
        assert handler.get_file_path(f"storage/raw/{upload['stored_name']}").endswith(f"/raw/{upload['stored_name']}")

