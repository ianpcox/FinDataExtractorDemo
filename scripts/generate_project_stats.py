#!/usr/bin/env python3
"""Generate project statistics for README metadata section

This script computes various metrics about the FinDataExtractorDEMO project
and outputs them in a format suitable for inclusion in the README.

This script is designed to be run in CI/CD pipelines to keep README metrics current.
It can also be run manually to update the "System at a Glance" section.

Usage:
    python scripts/generate_project_stats.py > docs/project_stats.json
    python scripts/generate_project_stats.py --markdown  # Output as Markdown table

Recommended: Run this script in CI after tests complete to auto-update metrics.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None


def count_api_routes() -> Dict[str, int]:
    """Count API routes by module"""
    routes_dir = project_root / "api" / "routes"
    route_counts = {}
    
    route_files = {
        "ingestion": "ingestion.py",
        "extraction": "extraction.py",
        "hitl": "hitl.py",
        "matching": "matching.py",
        "staging": "staging.py",
        "azure_import": "azure_import.py",
        "batch": "batch.py",
        "progress": "progress.py",
        "overlay": "overlay.py",
    }
    
    for module, filename in route_files.items():
        file_path = routes_dir / filename
        if file_path.exists():
            try:
                content = file_path.read_text(encoding='utf-8')
                # Count @router decorators (approximate)
                count = len(re.findall(r'@router\.(get|post|put|delete|patch)', content, re.IGNORECASE))
                route_counts[module] = count
            except Exception as e:
                print(f"Warning: Could not read {filename}: {e}", file=sys.stderr)
                route_counts[module] = 0
    
    return route_counts


def count_schema_fields() -> Dict[str, int]:
    """Count fields in schema files"""
    schemas_dir = project_root / "schemas"
    schema_fields = {}
    
    schema_files = {
        "canonical": "invoice.canonical.v1.schema.json",
        "hitl_view": "invoice.hitl_view.v1.schema.json",
        "contract": "invoice.contract.v1.schema.json",
    }
    
    for schema_name, filename in schema_files.items():
        file_path = schemas_dir / filename
        if file_path.exists():
            try:
                schema_data = json.loads(file_path.read_text(encoding='utf-8'))
                props = schema_data.get("properties", {})
                schema_fields[schema_name] = len(props)
                
                # Count validators if canonical schema
                if schema_name == "canonical":
                    validators = 0
                    for prop_name, prop_def in props.items():
                        if any(key in prop_def for key in ['pattern', 'format', 'minimum', 'maximum', 'enum', 'items']):
                            validators += 1
                    schema_fields[f"{schema_name}_validators"] = validators
                    schema_fields[f"{schema_name}_required"] = len(schema_data.get("required", []))
            except Exception as e:
                print(f"Warning: Could not parse {filename}: {e}", file=sys.stderr)
                schema_fields[schema_name] = 0
    
    return schema_fields


def count_tests() -> Dict[str, int]:
    """Count test files by category"""
    tests_dir = project_root / "tests"
    counts = {
        "unit": 0,
        "integration": 0,
        "e2e": 0,
        "total": 0,
    }
    
    for test_file in tests_dir.rglob("test_*.py"):
        counts["total"] += 1
        test_path_str = str(test_file)
        if "unit" in test_path_str:
            counts["unit"] += 1
        elif "integration" in test_path_str:
            counts["integration"] += 1
        elif "e2e" in test_path_str:
            counts["e2e"] += 1
    
    return counts


def count_migrations() -> int:
    """Count database migrations"""
    migrations_dir = project_root / "alembic" / "versions"
    if not migrations_dir.exists():
        return 0
    return len([f for f in migrations_dir.glob("*.py") if f.name != "__init__.py"])


def count_src_modules() -> Dict[str, int]:
    """Count Python modules in src directory"""
    src_dir = project_root / "src"
    modules = {}
    
    for subdir in src_dir.iterdir():
        if subdir.is_dir() and not subdir.name.startswith("__") and not subdir.name.startswith("."):
            py_files = list(subdir.rglob("*.py"))
            # Exclude __init__.py and __pycache__
            non_init = [f for f in py_files if f.name != "__init__.py" and "__pycache__" not in str(f)]
            if non_init:
                modules[subdir.name] = len(non_init)
    
    return modules


def get_coverage_info() -> Dict[str, Any]:
    """Get test coverage information if available"""
    coverage_file = project_root / "coverage.json"
    if not coverage_file.exists():
        return {"available": False}
    
    try:
        coverage_data = json.loads(coverage_file.read_text(encoding='utf-8'))
        totals = coverage_data.get("totals", {})
        return {
            "available": True,
            "percent_covered": totals.get("percent_covered", 0),
            "num_statements": totals.get("num_statements", 0),
            "missing_lines": totals.get("missing_lines", 0),
        }
    except Exception:
        return {"available": False}


def count_dependencies() -> Dict[str, int]:
    """Count dependencies from requirements.txt"""
    req_file = project_root / "requirements.txt"
    if not req_file.exists():
        return {"direct": 0, "total": 0}
    
    try:
        content = req_file.read_text(encoding='utf-8')
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
        direct = len([l for l in lines if not l.startswith("--")])
        return {"direct": direct, "total": direct}  # Simplified
    except Exception:
        return {"direct": 0, "total": 0}


def get_invoice_subtypes() -> list:
    """Get supported invoice subtypes"""
    invoice_file = project_root / "src" / "models" / "invoice.py"
    if invoice_file.exists():
        try:
            content = invoice_file.read_text(encoding='utf-8')
            subtypes = []
            if "STANDARD_INVOICE" in content:
                subtypes.append("Standard Invoice")
            if "SHIFT_SERVICE_INVOICE" in content:
                subtypes.append("Shift Service Invoice")
            if "PER_DIEM_TRAVEL_INVOICE" in content:
                subtypes.append("Per Diem Travel Invoice")
            return subtypes
        except Exception:
            return []
    return []


def get_processing_states() -> list:
    """Get invoice processing state machine"""
    invoice_file = project_root / "src" / "models" / "invoice.py"
    if invoice_file.exists():
        try:
            content = invoice_file.read_text(encoding='utf-8')
            states = []
            state_map = {
                "PENDING": "Pending",
                "PROCESSING": "Processing",
                "EXTRACTED": "Extracted",
                "VALIDATED": "Validated",
                "SEC34_APPROVED": "Sec34 Approved",
                "SEC33_APPROVED": "Sec33 Approved",
                "STAGED": "Staged",
            }
            for key, label in state_map.items():
                if key in content:
                    states.append(label)
            return states
        except Exception:
            return []
    return []


def main():
    """Generate and output project statistics"""
    stats = {
        "api": {
            "routes_by_module": count_api_routes(),
            "total_routes": sum(count_api_routes().values()),
            "modules": len(count_api_routes()),
        },
        "schemas": {
            "files": len(list((project_root / "schemas").glob("*.schema.json"))),
            "fields_by_schema": count_schema_fields(),
            "total_canonical_fields": count_schema_fields().get("canonical", 0),
        },
        "tests": count_tests(),
        "database": {
            "migrations": count_migrations(),
        },
        "source_code": {
            "modules_by_category": count_src_modules(),
            "total_modules": len(count_src_modules()),
        },
        "dependencies": count_dependencies(),
        "coverage": get_coverage_info(),
        "invoice_processing": {
            "supported_subtypes": get_invoice_subtypes(),
            "processing_states": get_processing_states(),
        },
    }
    
    # Output format
    if "--markdown" in sys.argv:
        output_markdown(stats)
    else:
        print(json.dumps(stats, indent=2, ensure_ascii=False))


def output_markdown(stats: Dict[str, Any]):
    """Output stats as Markdown tables"""
    print("## System at a Glance")
    print()
    
    # API Surface
    print("### API Surface")
    routes = stats["api"]["routes_by_module"]
    print(f"- **{stats['api']['total_routes']} total routes** across **{stats['api']['modules']} modules**")
    print("  - Modules: " + ", ".join([f"{k} ({v})" for k, v in sorted(routes.items()) if v > 0]))
    print()
    
    # Schemas
    print("### Schema & Contracts")
    schema_fields = stats["schemas"]["fields_by_schema"]
    print(f"- **{stats['schemas']['total_canonical_fields']} canonical fields** (invoice.canonical.v1.schema.json)")
    if schema_fields.get("canonical_required"):
        print(f"  - {schema_fields.get('canonical_required', 0)} required fields")
    if schema_fields.get("canonical_validators"):
        print(f"  - {schema_fields.get('canonical_validators', 0)} fields with validators")
    print(f"- **{schema_fields.get('hitl_view', 0)} HITL view fields**")
    print(f"- **{stats['schemas']['files']} schema variants**")
    print()
    
    # Tests
    print("### Quality Posture")
    test_counts = stats["tests"]
    coverage = stats["coverage"]
    print(f"- **{test_counts['total']} test files** ({test_counts['unit']} unit, {test_counts['integration']} integration, {test_counts['e2e']} e2e)")
    if coverage.get("available"):
        print(f"- **{coverage['percent_covered']:.1f}% code coverage** ({coverage['num_statements']} statements)")
    else:
        print("- Coverage: Run `pytest --cov=src` to generate")
    print()
    
    # Invoice Processing
    print("### Invoice Processing Capabilities")
    subtypes = stats["invoice_processing"]["supported_subtypes"]
    states = stats["invoice_processing"]["processing_states"]
    print(f"- **Invoice Subtypes**: {', '.join(subtypes) if subtypes else 'Standard'}")
    print(f"- **Processing States**: {' -> '.join(states) if states else 'PENDING -> STAGED'}")
    print(f"- **Database Migrations**: {stats['database']['migrations']}")
    print()
    
    # Source Code Structure
    print("### Code Organization")
    modules = stats["source_code"]["modules_by_category"]
    print(f"- **{stats['source_code']['total_modules']} major modules**: " + ", ".join(sorted(modules.keys())))
    print()
    
    # Dependencies
    deps = stats["dependencies"]
    print(f"- **{deps['direct']} direct dependencies** (Python)")
    print()


if __name__ == "__main__":
    main()
