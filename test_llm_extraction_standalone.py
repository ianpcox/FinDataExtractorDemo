"""
Standalone Base LLM Extraction Test (No Database)

This test bypasses database operations entirely and focuses on text-based LLM extraction functionality.
Results are collected in DataFrames for analysis.

Requirements:
- Azure OpenAI credentials configured
- Azure Document Intelligence credentials configured
- Sample PDF available
"""

import asyncio
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import pandas as pd
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.extraction.extraction_service import ExtractionService, CANONICAL_FIELDS
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.ingestion.file_handler import FileHandler
from src.models.invoice import Invoice, InvoiceState
from src.config import settings


class StandaloneLLMExtractor:
    """Standalone extractor that bypasses database operations - text-based LLM only"""
    
    def __init__(self):
        """Initialize extraction components"""
        # Check credentials
        if not settings.AOAI_ENDPOINT or not settings.AOAI_API_KEY:
            raise ValueError("Azure OpenAI credentials not configured")
        
        if not settings.AZURE_FORM_RECOGNIZER_ENDPOINT or not settings.AZURE_FORM_RECOGNIZER_KEY:
            raise ValueError("Azure Document Intelligence credentials not configured")
        
        # Create components
        self.di_client = DocumentIntelligenceClient(
            endpoint=settings.AZURE_FORM_RECOGNIZER_ENDPOINT,
            api_key=settings.AZURE_FORM_RECOGNIZER_KEY
        )
        
        self.file_handler = FileHandler()
        self.field_extractor = FieldExtractor()
        
        self.extraction_service = ExtractionService(
            doc_intelligence_client=self.di_client,
            file_handler=self.file_handler,
            field_extractor=self.field_extractor
        )
        
        # Enable text-based LLM only (disable multimodal)
        settings.USE_LLM_FALLBACK = True
        settings.USE_MULTIMODAL_LLM_FALLBACK = False
        
        print("Standalone Base LLM Extractor initialized")
        print(f"- DI Endpoint: {settings.AZURE_FORM_RECOGNIZER_ENDPOINT}")
        print(f"- AOAI Endpoint: {settings.AOAI_ENDPOINT}")
        print(f"- LLM Deployment: {settings.AOAI_DEPLOYMENT_NAME}")
        print(f"- USE_LLM_FALLBACK: {settings.USE_LLM_FALLBACK}")
        print(f"- USE_MULTIMODAL_LLM_FALLBACK: {settings.USE_MULTIMODAL_LLM_FALLBACK} (disabled)")
    
    async def extract_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract invoice data from PDF without database operations.
        Uses text-based LLM only (no multimodal).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with extraction results
        """
        print(f"\n{'='*80}")
        print(f"Extracting from: {pdf_path}")
        print(f"{'='*80}\n")
        
        # Read PDF
        with open(pdf_path, "rb") as f:
            file_content = f.read()
        
        print(f"PDF size: {len(file_content):,} bytes")
        
        # Step 1: Run Document Intelligence
        print("\nStep 1: Running Document Intelligence OCR...")
        di_result = await asyncio.to_thread(
            self.di_client.analyze_invoice,
            file_content
        )
        
        if not di_result or "error" in di_result:
            print(f"DI Error: {di_result.get('error', 'Unknown error')}")
            return {"error": "Document Intelligence failed", "details": di_result}
        
        print(f"DI completed successfully")
        
        # Step 2: Extract fields using FieldExtractor
        print("\nStep 2: Extracting fields from DI result...")
        invoice = self.field_extractor.extract_invoice(
            doc_intelligence_data=di_result,
            file_path=pdf_path,
            file_name=os.path.basename(pdf_path),
            upload_date=datetime.utcnow()
        )
        
        # Set ID for tracking
        invoice.id = f"standalone-llm-test-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        invoice.processing_state = InvoiceState.EXTRACTED
        
        di_extracted_count = len([f for f, v in invoice.model_dump().items() if v is not None and f in CANONICAL_FIELDS])
        print(f"Extracted {di_extracted_count} fields from DI")
        
        # Step 3: Identify low-confidence fields
        print("\nStep 3: Identifying low-confidence fields...")
        low_conf_threshold = getattr(settings, "LLM_LOW_CONF_THRESHOLD", 0.75)
        field_confidence = invoice.field_confidence or {}
        
        low_conf_fields = []
        for field_name in CANONICAL_FIELDS:
            field_value = getattr(invoice, field_name, None)
            confidence = field_confidence.get(field_name, 0.0)
            
            # Include field if it has low confidence or is missing
            if confidence < low_conf_threshold or field_value is None:
                low_conf_fields.append(field_name)
        
        print(f"Found {len(low_conf_fields)} low-confidence fields (threshold: {low_conf_threshold})")
        print(f"Low-confidence fields: {low_conf_fields[:10]}{'...' if len(low_conf_fields) > 10 else ''}")
        
        # Step 4: Run text-based LLM fallback
        llm_result = None
        if low_conf_fields:
            print("\nStep 4: Running text-based LLM fallback...")
            try:
                llm_result = await self.extraction_service._run_low_confidence_fallback(
                    invoice=invoice,
                    low_conf_fields=low_conf_fields,
                    di_data=di_result,
                    di_field_confidence=field_confidence,
                    invoice_id=invoice.id
                )
                
                print(f"Text-based LLM result:")
                print(f"  - Success: {llm_result.get('success', False)}")
                print(f"  - Groups processed: {llm_result.get('groups_processed', 0)}")
                print(f"  - Groups succeeded: {llm_result.get('groups_succeeded', 0)}")
                print(f"  - Groups failed: {llm_result.get('groups_failed', 0)}")
                
                # Print per-group results
                if llm_result.get('group_results'):
                    print(f"\n  Per-group results:")
                    for group_name, group_result in llm_result['group_results'].items():
                        status = "[OK]" if group_result.get('success') else "[FAIL]"
                        fields = group_result.get('fields', [])
                        error = group_result.get('error')
                        print(f"    {status} {group_name}: {len(fields)} fields" + (f" - {error}" if error else ""))
                
            except Exception as e:
                print(f"Text-based LLM error: {e}")
                import traceback
                traceback.print_exc()
                llm_result = {"error": str(e)}
        else:
            print("\nStep 4: Skipping LLM fallback (no low-confidence fields)")
        
        # Step 5: Collect results
        print("\nStep 5: Collecting extraction results...")
        invoice_dict = invoice.model_dump(mode="json")
        
        # Determine if LLM actually improved fields by comparing before/after
        # We'll check if any fields that were low-confidence now have higher confidence
        llm_improved_fields = []
        if llm_result and llm_result.get('success'):
            # Check which fields were improved by LLM
            for field_name in low_conf_fields:
                field_value = getattr(invoice, field_name, None)
                confidence = field_confidence.get(field_name, 0.0)
                # If field was low confidence and now has a value or higher confidence, LLM may have helped
                if field_value is not None or confidence >= low_conf_threshold:
                    llm_improved_fields.append(field_name)
        
        # Build results dictionary
        results = {
            "invoice_id": invoice.id,
            "file_name": os.path.basename(pdf_path),
            "pdf_size_bytes": len(file_content),
            "di_success": True,
            "di_fields_extracted": di_extracted_count,
            "low_confidence_fields_count": len(low_conf_fields),
            "low_confidence_fields": low_conf_fields,
            "llm_triggered": llm_result is not None and not llm_result.get('error'),
            "llm_success": llm_result.get('success', False) if llm_result and not llm_result.get('error') else False,
            "llm_groups_processed": llm_result.get('groups_processed', 0) if llm_result and not llm_result.get('error') else 0,
            "llm_groups_succeeded": llm_result.get('groups_succeeded', 0) if llm_result and not llm_result.get('error') else 0,
            "llm_groups_failed": llm_result.get('groups_failed', 0) if llm_result and not llm_result.get('error') else 0,
            "llm_group_results": llm_result.get('group_results', {}) if llm_result and not llm_result.get('error') else {},
            "llm_improved_fields": llm_improved_fields,
            "extraction_confidence": invoice.extraction_confidence,
            "field_confidence": invoice.field_confidence,
            "extracted_fields": {},
            "canonical_fields_coverage": {}
        }
        
        # Collect extracted field values (higher-level invoice fields)
        for field_name in sorted(CANONICAL_FIELDS):
            field_value = getattr(invoice, field_name, None)
            confidence = field_confidence.get(field_name, None)
            
            # Determine if field was extracted
            is_extracted = False
            if field_value is not None:
                if isinstance(field_value, str):
                    is_extracted = field_value.strip() != ""
                elif isinstance(field_value, (int, float, Decimal)):
                    is_extracted = field_value != 0
                elif isinstance(field_value, dict):
                    is_extracted = len(field_value) > 0
                elif isinstance(field_value, list):
                    is_extracted = len(field_value) > 0
                else:
                    is_extracted = True
            
            # Convert date/datetime objects to strings for serialization
            serialized_value = field_value
            if field_value is not None:
                if hasattr(field_value, 'isoformat'):
                    serialized_value = field_value.isoformat()
                elif isinstance(field_value, (dict, list)):
                    # Keep complex types as-is for now
                    serialized_value = field_value
            
            results["extracted_fields"][field_name] = {
                "value": serialized_value,
                "confidence": confidence,
                "extracted": is_extracted,
                "extracted_by_di": confidence is not None and confidence >= low_conf_threshold if confidence is not None else False,
                "extracted_by_llm": field_name in results.get("llm_improved_fields", []) if "llm_improved_fields" in results else False
            }
        
        # Add line items (new table structure)
        line_items_value = []
        if invoice.line_items:
            for item in invoice.line_items:
                line_items_value.append({
                    "line_number": item.line_number,
                    "description": item.description,
                    "quantity": float(item.quantity) if item.quantity else None,
                    "unit_price": float(item.unit_price) if item.unit_price else None,
                    "amount": float(item.amount) if item.amount else None,
                    "tax_amount": float(item.tax_amount) if item.tax_amount else None,
                    "gst_amount": float(item.gst_amount) if item.gst_amount else None,
                    "pst_amount": float(item.pst_amount) if item.pst_amount else None,
                    "qst_amount": float(item.qst_amount) if item.qst_amount else None,
                    "confidence": item.confidence or 0.0
                })
        
        # Add line_items to extracted_fields
        line_items_confidence = field_confidence.get("line_items")
        results["extracted_fields"]["line_items"] = {
            "value": line_items_value,
            "confidence": line_items_confidence,
            "extracted": len(line_items_value) > 0,
            "extracted_by_di": line_items_confidence is not None and line_items_confidence >= low_conf_threshold if line_items_confidence is not None else False,
            "extracted_by_llm": False  # Line items typically come from DI
        }
        
        # Calculate coverage statistics
        total_fields = len(CANONICAL_FIELDS)
        extracted_count = sum(1 for f in results["extracted_fields"].values() if f["extracted"])
        di_extracted = sum(1 for f in results["extracted_fields"].values() if f.get("extracted_by_di", False))
        llm_extracted = sum(1 for f in results["extracted_fields"].values() if f.get("extracted_by_llm", False))
        
        results["canonical_fields_coverage"] = {
            "total": total_fields,
            "extracted": extracted_count,
            "missing": total_fields - extracted_count,
            "extraction_rate": (extracted_count / total_fields * 100) if total_fields > 0 else 0,
            "di_extracted": di_extracted,
            "llm_extracted": llm_extracted,
            "di_only": di_extracted - llm_extracted,
            "llm_only": llm_extracted
        }
        
        print(f"\nExtraction Summary:")
        print(f"  - Total canonical fields: {total_fields}")
        print(f"  - Fields extracted: {extracted_count} ({results['canonical_fields_coverage']['extraction_rate']:.1f}%)")
        print(f"  - Fields missing: {total_fields - extracted_count}")
        print(f"  - DI extracted: {di_extracted}")
        print(f"  - LLM extracted: {llm_extracted}")
        print(f"  - Overall confidence: {invoice.extraction_confidence}")
        
        return results
    
    def results_to_dataframe(self, results: Dict[str, Any]) -> pd.DataFrame:
        """
        Convert extraction results to a pandas DataFrame.
        
        Args:
            results: Extraction results dictionary
            
        Returns:
            DataFrame with field-by-field extraction data
        """
        rows = []
        for field_name, field_data in results["extracted_fields"].items():
            rows.append({
                "field_name": field_name,
                "value": str(field_data["value"]) if field_data["value"] is not None else None,
                "confidence": field_data["confidence"],
                "extracted": field_data["extracted"],
                "extracted_by_di": field_data.get("extracted_by_di", False),
                "extracted_by_llm": field_data.get("extracted_by_llm", False),
                "value_type": type(field_data["value"]).__name__ if field_data["value"] is not None else "NoneType"
            })
        
        df = pd.DataFrame(rows)
        return df
    
    def generate_report(self, results: Dict[str, Any], output_path: str = None):
        """
        Generate a detailed extraction report.
        
        Args:
            results: Extraction results dictionary
            output_path: Optional path to save report (markdown format)
        """
        report = []
        report.append("# Base LLM Extraction Report (Standalone Test)")
        report.append("")
        report.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append(f"**File:** {results['file_name']}")
        report.append(f"**Invoice ID:** {results['invoice_id']}")
        report.append("")
        report.append("---")
        report.append("")
        
        # Summary
        report.append("## Extraction Summary")
        report.append("")
        report.append(f"- **PDF Size:** {results['pdf_size_bytes']:,} bytes")
        report.append(f"- **DI Success:** {results['di_success']}")
        report.append(f"- **DI Fields Extracted:** {results['di_fields_extracted']}")
        report.append(f"- **Low-Confidence Fields:** {results['low_confidence_fields_count']}")
        report.append(f"- **LLM Triggered:** {results['llm_triggered']}")
        report.append(f"- **LLM Success:** {results['llm_success']}")
        report.append(f"- **LLM Groups Processed:** {results['llm_groups_processed']}")
        report.append(f"- **LLM Groups Succeeded:** {results['llm_groups_succeeded']}")
        report.append(f"- **LLM Groups Failed:** {results['llm_groups_failed']}")
        report.append(f"- **Overall Extraction Confidence:** {results['extraction_confidence']}")
        report.append("")
        
        # LLM Group Results
        if results.get('llm_group_results'):
            report.append("## LLM Group Results")
            report.append("")
            for group_name, group_result in results['llm_group_results'].items():
                status = "[SUCCESS]" if group_result.get('success') else "[FAILED]"
                fields = group_result.get('fields', [])
                error = group_result.get('error')
                report.append(f"### {group_name.capitalize()} Group: {status}")
                report.append(f"- **Fields:** {len(fields)}")
                if fields:
                    report.append(f"- **Field Names:** {', '.join(fields[:10])}{'...' if len(fields) > 10 else ''}")
                if error:
                    report.append(f"- **Error:** {error}")
                report.append("")
        
        # Coverage
        coverage = results['canonical_fields_coverage']
        report.append("## Canonical Field Coverage")
        report.append("")
        report.append(f"- **Total Canonical Fields:** {coverage['total']}")
        report.append(f"- **Fields Extracted:** {coverage['extracted']} ({coverage['extraction_rate']:.1f}%)")
        report.append(f"- **Fields Missing:** {coverage['missing']} ({100 - coverage['extraction_rate']:.1f}%)")
        report.append(f"- **Extracted by DI:** {coverage['di_extracted']}")
        report.append(f"- **Extracted by LLM:** {coverage['llm_extracted']}")
        report.append(f"- **DI Only:** {coverage['di_only']}")
        report.append(f"- **LLM Only:** {coverage['llm_only']}")
        report.append("")
        
        # Field-by-field details
        report.append("## Extracted Fields")
        report.append("")
        report.append("| Field Name | Extracted | Confidence | Source | Value Preview |")
        report.append("|------------|-----------|------------|--------|---------------|")
        
        for field_name, field_data in sorted(results["extracted_fields"].items()):
            extracted_str = "[YES]" if field_data["extracted"] else "[NO]"
            conf_str = f"{field_data['confidence']:.2f}" if field_data['confidence'] is not None else "N/A"
            
            # Determine source - check if field was in low-confidence list and now has value
            if field_name in results.get("llm_improved_fields", []):
                source = "LLM"
            elif field_data.get("extracted_by_di"):
                source = "DI"
            else:
                source = "-"
            
            value_preview = str(field_data['value'])[:40] if field_data['value'] is not None else "None"
            if field_data['value'] is not None and len(str(field_data['value'])) > 40:
                value_preview += "..."
            
            report.append(f"| {field_name} | {extracted_str} | {conf_str} | {source} | {value_preview} |")
        
        report.append("")
        report.append("---")
        report.append("")
        report.append("**Report End**")
        
        report_text = "\n".join(report)
        
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_text)
            print(f"\nReport saved to: {output_path}")
        
        return report_text


async def main():
    """Main test function"""
    # Sample PDF path
    sample_pdf = "data/sample_invoices/Raw/Raw_Basic/ACC012 4202092525.pdf"
    
    if not os.path.exists(sample_pdf):
        print(f"Error: Sample PDF not found at {sample_pdf}")
        print("Please provide a valid PDF path")
        return
    
    try:
        # Create extractor
        extractor = StandaloneLLMExtractor()
        
        # Run extraction
        results = await extractor.extract_from_pdf(sample_pdf)
        
        # Convert to DataFrame
        df = extractor.results_to_dataframe(results)
        
        # Display DataFrame
        print("\n" + "="*80)
        print("EXTRACTION RESULTS (DataFrame)")
        print("="*80)
        print(df.to_string(index=False))
        
        # Save DataFrame to CSV
        csv_path = "llm_extraction_results.csv"
        df.to_csv(csv_path, index=False)
        print(f"\nDataFrame saved to: {csv_path}")
        
        # Generate and save report
        report_path = "llm_extraction_report.md"
        report = extractor.generate_report(results, output_path=report_path)
        
        # Print summary statistics
        print("\n" + "="*80)
        print("SUMMARY STATISTICS")
        print("="*80)
        coverage = results['canonical_fields_coverage']
        print(f"Total fields: {coverage['total']}")
        print(f"Extracted: {coverage['extracted']} ({coverage['extraction_rate']:.1f}%)")
        print(f"Missing: {coverage['missing']}")
        print(f"DI extracted: {coverage['di_extracted']}")
        print(f"LLM extracted: {coverage['llm_extracted']}")
        print(f"DI only: {coverage['di_only']}")
        print(f"LLM only: {coverage['llm_only']}")
        print(f"Overall confidence: {results['extraction_confidence']}")
        print(f"LLM triggered: {results['llm_triggered']}")
        print(f"LLM success: {results['llm_success']}")
        print(f"LLM groups succeeded: {results['llm_groups_succeeded']}/{results['llm_groups_processed']}")
        
        # Print extracted fields by category
        print("\n" + "="*80)
        print("EXTRACTED FIELDS BY CATEGORY")
        print("="*80)
        
        categories = {
            "Header": ["invoice_number", "invoice_date", "due_date", "invoice_type", "reference_number"],
            "Vendor": ["vendor_name", "vendor_id", "vendor_phone", "vendor_fax", "vendor_email", "vendor_website", "vendor_address"],
            "Customer": ["customer_name", "customer_id", "customer_phone", "customer_email", "customer_fax", "bill_to_address"],
            "Financial": ["subtotal", "discount_amount", "shipping_amount", "handling_fee", "deposit_amount"],
            "Canadian Taxes": ["gst_amount", "gst_rate", "hst_amount", "hst_rate", "qst_amount", "qst_rate", "pst_amount", "pst_rate"],
            "Total": ["tax_amount", "total_amount", "currency"],
        }
        
        for category, fields in categories.items():
            extracted = sum(1 for f in fields if results["extracted_fields"].get(f, {}).get("extracted", False))
            di_extracted = sum(1 for f in fields if results["extracted_fields"].get(f, {}).get("extracted_by_di", False))
            llm_extracted = sum(1 for f in fields if results["extracted_fields"].get(f, {}).get("extracted_by_llm", False))
            total = len(fields)
            rate = (extracted / total * 100) if total > 0 else 0
            print(f"{category:<20} {extracted}/{total} ({rate:.0f}%) [DI: {di_extracted}, LLM: {llm_extracted}]")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

