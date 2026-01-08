"""Script to reorganize tests into DEMO/DEV/PROD structure"""
import shutil
import os
from pathlib import Path

# Define test organization
test_moves = {
    # DEMO tests (standalone, simple scripts)
    "demo/integration": [
        "tests/integration/standalone/test_di_ocr_extraction_standalone.py",
        "tests/integration/standalone/test_llm_extraction_standalone.py",
        "tests/integration/standalone/test_multimodal_llm_extraction_standalone.py",
        "tests/integration/test_di_ocr_real.py",
        "tests/integration/test_llm_extraction_real.py",
        "tests/integration/test_multimodal_llm_extraction_real.py",
        "tests/integration/test_multimodal_llm_direct.py",
        "tests/integration/test_extraction_direct.py",
    ],
    "demo/e2e": [
        "tests/integration/test_real_extraction.py",
    ],
    # DEV tests (with mocks)
    "dev/unit": [
        # All unit tests
        "tests/unit",
    ],
    "dev/integration": [
        "tests/integration/test_api_routes.py",
        "tests/integration/test_db_isolation.py",
        "tests/integration/test_llm_extraction.py",
        "tests/integration/test_llm_error_handling.py",
        "tests/integration/test_multimodal_llm_error_handling.py",
        "tests/integration/test_concurrent_extraction.py",
        "tests/integration/test_hitl_decimal_wire.py",
        "tests/integration/test_hitl_explicit_clear.py",
        "tests/integration/test_hitl_optimistic_locking.py",
    ],
    "dev/e2e": [
        "tests/integration/test_end_to_end.py",
    ],
    # PROD tests (real services)
    "prod/integration": [
        "tests/integration/test_real_di_extraction.py",
        "tests/integration/test_real_llm_extraction.py",
        "tests/integration/test_real_multimodal_llm_extraction.py",
        "tests/integration/test_real_pdf_integration.py",
        "tests/integration/test_line_item_extraction_and_aggregation.py",
        "tests/integration/test_line_item_persistence.py",
        "tests/integration/test_keyvault_fallback.py",
        "tests/integration/azure",
        "tests/integration/migration",
    ],
    "prod/e2e": [
        "tests/integration/test_large_invoice_performance.py",
        "tests/integration/test_multimodal_llm_performance.py",
    ],
}

def move_file_or_dir(src, dst_dir):
    """Move a file or directory to destination"""
    src_path = Path(src)
    if not src_path.exists():
        print(f"  [SKIP] {src} (not found)")
        return False
    
    dst_path = Path("tests") / dst_dir
    dst_path.mkdir(parents=True, exist_ok=True)
    
    if src_path.is_file():
        dst_file = dst_path / src_path.name
        shutil.move(str(src_path), str(dst_file))
        print(f"  [OK] {src_path.name} -> {dst_dir}/")
        return True
    elif src_path.is_dir():
        # Move directory contents
        for item in src_path.iterdir():
            if item.is_file() and item.suffix == ".py":
                dst_file = dst_path / item.name
                shutil.move(str(item), str(dst_file))
                print(f"  [OK] {item.name} -> {dst_dir}/")
        return True
    return False

def main():
    print("=" * 60)
    print("REORGANIZING TESTS INTO DEMO/DEV/PROD STRUCTURE")
    print("=" * 60)
    
    # Move files
    for dst_dir, sources in test_moves.items():
        print(f"\n{dst_dir}:")
        for src in sources:
            move_file_or_dir(src, dst_dir)
    
    # Clean up empty directories
    print("\nCleaning up empty directories...")
    for dir_path in ["tests/integration", "tests/unit"]:
        dir_obj = Path(dir_path)
        if dir_obj.exists():
            try:
                # Check if directory is empty (only __pycache__ and __init__.py)
                items = [item for item in dir_obj.rglob("*") if item.name not in ["__pycache__", "__init__.py"]]
                if not items:
                    shutil.rmtree(str(dir_obj))
                    print(f"  [OK] Removed {dir_path}")
            except Exception as e:
                print(f"  [WARN] Could not remove {dir_path}: {e}")
    
    print("\n" + "=" * 60)
    print("REORGANIZATION COMPLETE")
    print("=" * 60)
    
    # Count files
    for env in ["demo", "dev", "prod"]:
        count = len(list(Path(f"tests/{env}").rglob("test_*.py")))
        print(f"  {env.upper()}: {count} test files")

if __name__ == "__main__":
    main()
