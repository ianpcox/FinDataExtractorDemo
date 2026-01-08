"""
Standalone Multimodal LLM Extraction Test (No Database)

This test bypasses database operations entirely and focuses on extraction functionality.
Results are collected in DataFrames for analysis.

Requirements:
- Azure OpenAI credentials configured
- Azure Document Intelligence credentials configured
- PyMuPDF installed for image rendering
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


class StandaloneMultimodalExtractor:
    """Standalone extractor that bypasses database operations"""
    
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
        
        # Enable multimodal LLM
        settings.USE_LLM_FALLBACK = True
        settings.USE_MULTIMODAL_LLM_FALLBACK = True
        
        print("Standalone Multimodal Extractor initialized")
        print(f"- DI Endpoint: {settings.AZURE_FORM_RECOGNIZER_ENDPOINT}")
        print(f"- AOAI Endpoint: {settings.AOAI_ENDPOINT}")
        print(f"- Multimodal Deployment: {settings.AOAI_MULTIMODAL_DEPLOYMENT_NAME or settings.AOAI_DEPLOYMENT_NAME}")
        print(f"- USE_MULTIMODAL_LLM_FALLBACK: {settings.USE_MULTIMODAL_LLM_FALLBACK}")
    
    async def extract_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract invoice data from PDF without database operations.
        
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
        invoice.id = f"standalone-test-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        invoice.processing_state = InvoiceState.EXTRACTED
        
        print(f"Extracted {len([f for f, v in invoice.model_dump().items() if v is not None and f in CANONICAL_FIELDS])} fields from DI")
        
        # Step 3: Check if PDF is scanned
        print("\nStep 3: Checking if PDF is scanned...")
        is_scanned = self.extraction_service._is_scanned_pdf(file_content)
        print(f"PDF is scanned: {is_scanned}")
        
        # Step 4: Identify low-confidence fields
        print("\nStep 4: Identifying low-confidence fields...")
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
        
        # Step 5: Run Multimodal LLM fallback (if applicable)
        multimodal_result = None
        if is_scanned and low_conf_fields:
            print("\nStep 5: Running Multimodal LLM fallback...")
            try:
                multimodal_result = await self.extraction_service._run_multimodal_fallback(
                    invoice=invoice,
                    low_conf_fields=low_conf_fields,
                    di_data=di_result,
                    di_field_confidence=field_confidence,
                    file_content=file_content,
                    invoice_id=invoice.id
                )
                
                print(f"Multimodal LLM result:")
                print(f"  - Success: {multimodal_result.get('success', False)}")
                print(f"  - Groups processed: {multimodal_result.get('groups_processed', 0)}")
                print(f"  - Groups succeeded: {multimodal_result.get('groups_succeeded', 0)}")
                print(f"  - Groups failed: {multimodal_result.get('groups_failed', 0)}")
                
            except Exception as e:
                print(f"Multimodal LLM error: {e}")
                multimodal_result = {"error": str(e)}
        
        # Step 6: Try text-based LLM fallback if multimodal didn't improve fields
        text_llm_result = None
        if low_conf_fields and (not multimodal_result or not multimodal_result.get('success')):
            print("\nStep 6: Running text-based LLM fallback...")
            try:
                text_llm_result = await self.extraction_service._run_low_confidence_fallback(
                    invoice=invoice,
                    low_conf_fields=low_conf_fields,
                    di_data=di_result,
                    di_field_confidence=field_confidence,
                    invoice_id=invoice.id
                )
                
                print(f"Text-based LLM result:")
                print(f"  - Success: {text_llm_result.get('success', False)}")
                print(f"  - Groups processed: {text_llm_result.get('groups_processed', 0)}")
                print(f"  - Groups succeeded: {text_llm_result.get('groups_succeeded', 0)}")
                print(f"  - Groups failed: {text_llm_result.get('groups_failed', 0)}")
                
            except Exception as e:
                print(f"Text-based LLM error: {e}")
                text_llm_result = {"error": str(e)}
        
        # Step 7: Collect results
        print("\nStep 7: Collecting extraction results...")
        invoice_dict = invoice.model_dump(mode="json")
        
        # Build results dictionary
        results = {
            "invoice_id": invoice.id,
            "file_name": os.path.basename(pdf_path),
            "pdf_size_bytes": len(file_content),
            "is_scanned": is_scanned,
            "di_success": True,
            "low_confidence_fields_count": len(low_conf_fields),
            "low_confidence_fields": low_conf_fields,
            "multimodal_llm_triggered": multimodal_result is not None,
            "multimodal_llm_success": multimodal_result.get('success', False) if multimodal_result else False,
            "text_llm_triggered": text_llm_result is not None,
            "text_llm_success": text_llm_result.get('success', False) if text_llm_result else False,
            "extraction_confidence": invoice.extraction_confidence,
            "field_confidence": invoice.field_confidence,
            "extracted_fields": {},
            "canonical_fields_coverage": {}
        }
        
        # Collect extracted field values
        for field_name in sorted(CANONICAL_FIELDS):
            field_value = getattr(invoice, field_name, None)
            confidence = field_confidence.get(field_name, None)
            
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
                "extracted": field_value is not None and (
                    (isinstance(field_value, str) and field_value.strip() != "") or
                    (isinstance(field_value, (int, float, Decimal)) and field_value != 0) or
                    (isinstance(field_value, dict) and len(field_value) > 0) or
                    (isinstance(field_value, list) and len(field_value) > 0) or
                    (not isinstance(field_value, (str, int, float, Decimal, dict, list)))
                )
            }
        
        # Calculate coverage statistics
        total_fields = len(CANONICAL_FIELDS)
        extracted_count = sum(1 for f in results["extracted_fields"].values() if f["extracted"])
        results["canonical_fields_coverage"] = {
            "total": total_fields,
            "extracted": extracted_count,
            "missing": total_fields - extracted_count,
            "extraction_rate": (extracted_count / total_fields * 100) if total_fields > 0 else 0
        }
        
        print(f"\nExtraction Summary:")
        print(f"  - Total canonical fields: {total_fields}")
        print(f"  - Fields extracted: {extracted_count} ({results['canonical_fields_coverage']['extraction_rate']:.1f}%)")
        print(f"  - Fields missing: {total_fields - extracted_count}")
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
        report.append("# Multimodal LLM Extraction Report (Standalone Test)")
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
        report.append(f"- **PDF Type:** {'Scanned' if results['is_scanned'] else 'Text-based'}")
        report.append(f"- **DI Success:** {results['di_success']}")
        report.append(f"- **Low-Confidence Fields:** {results['low_confidence_fields_count']}")
        report.append(f"- **Multimodal LLM Triggered:** {results['multimodal_llm_triggered']}")
        report.append(f"- **Multimodal LLM Success:** {results['multimodal_llm_success']}")
        report.append(f"- **Text-based LLM Triggered:** {results['text_llm_triggered']}")
        report.append(f"- **Text-based LLM Success:** {results['text_llm_success']}")
        report.append(f"- **Overall Extraction Confidence:** {results['extraction_confidence']}")
        report.append("")
        
        # Coverage
        coverage = results['canonical_fields_coverage']
        report.append("## Canonical Field Coverage")
        report.append("")
        report.append(f"- **Total Canonical Fields:** {coverage['total']}")
        report.append(f"- **Fields Extracted:** {coverage['extracted']} ({coverage['extraction_rate']:.1f}%)")
        report.append(f"- **Fields Missing:** {coverage['missing']} ({100 - coverage['extraction_rate']:.1f}%)")
        report.append("")
        
        # Field-by-field details
        report.append("## Extracted Fields")
        report.append("")
        report.append("| Field Name | Extracted | Confidence | Value Preview |")
        report.append("|------------|-----------|------------|---------------|")
        
        for field_name, field_data in sorted(results["extracted_fields"].items()):
            extracted_str = "✅" if field_data["extracted"] else "❌"
            conf_str = f"{field_data['confidence']:.2f}" if field_data['confidence'] is not None else "N/A"
            value_preview = str(field_data['value'])[:40] if field_data['value'] is not None else "None"
            if field_data['value'] is not None and len(str(field_data['value'])) > 40:
                value_preview += "..."
            
            report.append(f"| {field_name} | {extracted_str} | {conf_str} | {value_preview} |")
        
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
        extractor = StandaloneMultimodalExtractor()
        
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
        csv_path = "multimodal_llm_extraction_results.csv"
        df.to_csv(csv_path, index=False)
        print(f"\nDataFrame saved to: {csv_path}")
        
        # Generate and save report
        report_path = "multimodal_llm_extraction_report.md"
        report = extractor.generate_report(results, output_path=report_path)
        
        # Print summary statistics
        print("\n" + "="*80)
        print("SUMMARY STATISTICS")
        print("="*80)
        print(f"Total fields: {results['canonical_fields_coverage']['total']}")
        print(f"Extracted: {results['canonical_fields_coverage']['extracted']} ({results['canonical_fields_coverage']['extraction_rate']:.1f}%)")
        print(f"Missing: {results['canonical_fields_coverage']['missing']}")
        print(f"Overall confidence: {results['extraction_confidence']}")
        print(f"Multimodal LLM used: {results['multimodal_llm_triggered']}")
        print(f"Multimodal LLM success: {results['multimodal_llm_success']}")
        
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
            total = len(fields)
            rate = (extracted / total * 100) if total > 0 else 0
            print(f"{category:<20} {extracted}/{total} ({rate:.0f}%)")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

