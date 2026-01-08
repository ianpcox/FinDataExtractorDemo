"""Script to organize test reports and scripts into tests directory"""
import shutil
import os
from pathlib import Path

# Create directory structure
dirs = [
    "tests/reports/di_ocr",
    "tests/reports/llm",
    "tests/reports/multimodal_llm",
    "tests/reports/confusion_matrices",
    "tests/reports/metrics",
    "tests/scripts",
    "tests/utils",
]

for dir_path in dirs:
    Path(dir_path).mkdir(parents=True, exist_ok=True)
    # Create __init__.py
    init_file = Path(dir_path) / "__init__.py"
    if not init_file.exists():
        init_file.touch()

# Define file moves
file_moves = {
    # DI OCR reports
    "tests/reports/di_ocr": [
        "di_ocr_test_report_with_false_negatives.md",
        "di_ocr_extraction_with_false_negatives.csv",
        "di_ocr_extraction_results.csv",
        "false_negatives_report.csv",
    ],
    # LLM reports
    "tests/reports/llm": [
        "llm_extraction_test_report_with_false_negatives.md",
        "llm_extraction_with_false_negatives.csv",
        "llm_extraction_results.csv",
        "llm_false_negatives_report.csv",
    ],
    # Multimodal LLM reports
    "tests/reports/multimodal_llm": [
        "multimodal_llm_extraction_test_report_with_false_negatives.md",
        "multimodal_llm_extraction_with_false_negatives.csv",
        "multimodal_llm_extraction_results.csv",
        "multimodal_llm_false_negatives_report.csv",
    ],
    # Confusion matrices
    "tests/reports/confusion_matrices": [
        "confusion_matrix_report.md",
        "confusion_matrix_overall.csv",
        "confusion_matrix_per_field.csv",
        "confusion_matrix_per_pdf.csv",
    ],
    # Metrics
    "tests/reports/metrics": [
        "comprehensive_metrics_report_aggregate_metrics.csv",
        "comprehensive_metrics_report_confidence_calibration.csv",
        "comprehensive_metrics_report_document_metrics.csv",
        "comprehensive_metrics_report_field_metrics.csv",
        "comprehensive_extraction_comparison.csv",
        "comprehensive_extraction_field_details.csv",
        "per_field_metrics_report.csv",
    ],
    # Test runner scripts
    "tests/scripts": [
        "run_di_ocr_with_false_negative_detection.py",
        "run_llm_extraction_with_false_negative_detection.py",
        "run_multimodal_llm_extraction_with_false_negative_detection.py",
        "run_comprehensive_extraction_tests.py",
    ],
    # Test utility scripts
    "tests/utils": [
        "enhanced_false_negative_detector.py",
        "false_negatives_detector.py",
        "generate_confusion_matrices.py",
        "generate_per_field_metrics.py",
        "diagnose_address_extraction.py",
        "diagnose_address_from_csv.py",
        "diagnose_single_pdf_address.py",
    ],
}

def main():
    print("=" * 60)
    print("ORGANIZING TEST REPORTS AND SCRIPTS")
    print("=" * 60)
    
    moved_count = 0
    skipped_count = 0
    
    for dst_dir, files in file_moves.items():
        print(f"\n{dst_dir}:")
        for file_name in files:
            src_path = Path(file_name)
            if src_path.exists():
                dst_path = Path(dst_dir) / file_name
                shutil.move(str(src_path), str(dst_path))
                print(f"  [OK] {file_name}")
                moved_count += 1
            else:
                print(f"  [SKIP] {file_name} (not found)")
                skipped_count += 1
    
    print("\n" + "=" * 60)
    print("ORGANIZATION COMPLETE")
    print("=" * 60)
    print(f"  Moved: {moved_count} files")
    print(f"  Skipped: {skipped_count} files")
    
    # Count files in each directory
    print("\nFinal counts:")
    for dir_path in dirs:
        count = len(list(Path(dir_path).glob("*"))) - 1  # Exclude __init__.py
        if count > 0:
            print(f"  {dir_path}: {count} files")

if __name__ == "__main__":
    main()
