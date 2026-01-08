"""Quick test script to verify Azure Blob Storage connectivity"""

import sys
import os
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')  # Set UTF-8
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.ingestion.azure_blob_utils import AzureBlobBrowser
from src.config import settings

def test_azure_connection():
    """Test Azure Blob Storage connection and list containers/blobs"""
    print("\n" + "="*60)
    print("Testing Azure Blob Storage Connection")
    print("="*60)
    
    try:
        # Initialize browser
        print("\n[CONNECT] Connecting to Azure Blob Storage...")
        browser = AzureBlobBrowser()
        print("[OK] Connected successfully!")
        
        # List containers
        print("\n[LIST] Listing containers...")
        containers = browser.list_containers()
        print(f"[OK] Found {len(containers)} containers:")
        for container in containers:
            print(f"   - {container}")
        
        if not containers:
            print("[WARN] No containers found")
            return
        
        # Use first container or specified one
        container_name = settings.AZURE_STORAGE_CONTAINER_RAW or containers[0]
        print(f"\n[INFO] Using container: {container_name}")
        
        # List blobs (try common paths)
        print("\n[SEARCH] Searching for invoices...")
        
        # Try different path prefixes
        prefixes_to_try = [
            None,  # Root level
            "RAW Basic/",
            "Raw_Basic/",
            "RAW Basic",
            "Raw_Basic",
            "raw/",
            "Raw/"
        ]
        
        found_blobs = []
        for prefix in prefixes_to_try:
            try:
                blobs = browser.list_blobs(
                    container_name=container_name,
                    prefix=prefix
                )
                if blobs:
                    print(f"\n[OK] Found {len(blobs)} files with prefix '{prefix or '(root)'}':")
                    for blob in blobs[:10]:  # Show first 10
                        print(f"   - {blob['name']} ({blob['size']:,} bytes)")
                    found_blobs.extend(blobs)
                    if prefix:  # If we found files with a prefix, stop searching
                        break
            except Exception as e:
                print(f"   [WARN] Error with prefix '{prefix}': {e}")
                continue
        
        if not found_blobs:
            print("\n[WARN] No PDF files found. Listing all files...")
            all_blobs = browser.list_blobs(container_name=container_name)
            pdf_blobs = [b for b in all_blobs if b['name'].lower().endswith('.pdf')]
            if pdf_blobs:
                print(f"[OK] Found {len(pdf_blobs)} PDF files:")
                for blob in pdf_blobs[:10]:
                    print(f"   - {blob['name']} ({blob['size']:,} bytes)")
                found_blobs = pdf_blobs
            else:
                print(f"   Found {len(all_blobs)} total files (non-PDF):")
                for blob in all_blobs[:10]:
                    print(f"   - {blob['name']} ({blob['size']:,} bytes)")
        
        if found_blobs:
            print(f"\n[OK] Azure connection test successful!")
            print(f"   Found {len(found_blobs)} invoice files")
            print(f"\n[INFO] To process a file, use:")
            print(f"   python scripts/process_azure_invoices.py --container {container_name} --blob-path \"{found_blobs[0]['name']}\"")
        else:
            print("\n[WARN] No invoice files found, but connection is working")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_azure_connection()
    sys.exit(0 if success else 1)

