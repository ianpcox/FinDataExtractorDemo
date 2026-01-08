"""
Test runner for demos - executes each demo and captures output
"""

import sys
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Fix Windows encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_api_server():
    """Check if API server is running"""
    import requests
    try:
        response = requests.get('http://localhost:8000/docs', timeout=2)
        return response.status_code == 200
    except:
        return False

def run_demo(demo_name, demo_path):
    """Run a demo script and capture output"""
    print(f"\n{'='*80}")
    print(f"RUNNING: {demo_name}")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(demo_path)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(Path(__file__).parent.parent)
        )
        
        output = result.stdout
        errors = result.stderr
        
        print(output)
        if errors:
            print("\n[STDERR]:")
            print(errors)
        
        return {
            'success': result.returncode == 0,
            'output': output,
            'errors': errors,
            'return_code': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': '',
            'errors': 'Demo timed out after 60 seconds',
            'return_code': -1
        }
    except Exception as e:
        return {
            'success': False,
            'output': '',
            'errors': str(e),
            'return_code': -1
        }

def main():
    """Run all demos and generate report"""
    print("\n" + "="*80)
    print("DEMO TEST RUNNER")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check API server
    print("\n[CHECK] Checking API server status...")
    api_running = check_api_server()
    if api_running:
        print("[OK] API server is running")
    else:
        print("[WARN] API server is NOT running")
        print("       Demos will fail. Start with: uvicorn api.main:app --reload")
    
    # Check for sample PDFs
    print("\n[CHECK] Checking for sample PDFs...")
    sample_dir = Path(__file__).parent.parent / "demos" / "sample_data"
    pdf_files = list(sample_dir.glob("*.pdf"))
    if pdf_files:
        print(f"[OK] Found {len(pdf_files)} PDF file(s)")
        for pdf in pdf_files[:3]:
            print(f"      - {pdf.name}")
    else:
        print("[WARN] No PDF files found in demos/sample_data/")
        print("       Demos 1 and 2 will fail without sample PDFs")
    
    # Run demos
    demos_dir = Path(__file__).parent.parent / "demos"
    demos = [
        ("Demo 1: Ingestion", demos_dir / "demo_01_ingestion.py"),
        ("Demo 2: Extraction", demos_dir / "demo_02_extraction.py"),
        ("Demo 3: PO Matching", demos_dir / "demo_03_po_matching.py"),
        ("Demo 4: PDF Overlay", demos_dir / "demo_04_pdf_overlay.py"),
        ("Demo 5: HITL Review", demos_dir / "demo_05_hitl_review.py"),
        ("Demo 6: ERP Staging", demos_dir / "demo_06_erp_staging.py"),
    ]
    
    results = {}
    
    for demo_name, demo_path in demos:
        if not demo_path.exists():
            print(f"\n[SKIP] {demo_name} - File not found: {demo_path}")
            continue
        
        result = run_demo(demo_name, demo_path)
        results[demo_name] = result
        
        # Small delay between demos
        time.sleep(1)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    for demo_name, result in results.items():
        status = "[OK]" if result['success'] else "[FAIL]"
        print(f"{status} {demo_name}")
        if not result['success']:
            if result['errors']:
                print(f"      Error: {result['errors'][:100]}")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

if __name__ == "__main__":
    main()

