"""
Standalone DI OCR Extraction Test (No Database)

This test bypasses database operations entirely and focuses on Document Intelligence OCR extraction functionality.
Results are collected in DataFrames for analysis.

Requirements:
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

from src.extraction.extraction_service import CANONICAL_FIELDS
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.models.invoice import Invoice, InvoiceState
from src.config import settings


class StandaloneDIOCRExtractor:
    """Standalone DI OCR extractor that bypasses database operations"""
    
    def __init__(self):
        """Initialize extraction components"""
        # Check credentials
        if not settings.AZURE_FORM_RECOGNIZER_ENDPOINT or not settings.AZURE_FORM_RECOGNIZER_KEY:
            raise ValueError("Azure Document Intelligence credentials not configured")
        
        # Create components
        self.di_client = DocumentIntelligenceClient(
            endpoint=settings.AZURE_FORM_RECOGNIZER_ENDPOINT,
            api_key=settings.AZURE_FORM_RECOGNIZER_KEY
        )
        
        self.field_extractor = FieldExtractor()
        
        print("Standalone DI OCR Extractor initialized")
        print(f"- DI Endpoint: {settings.AZURE_FORM_RECOGNIZER_ENDPOINT}")
        print(f"- DI API Key: {'*' * 20}...{settings.AZURE_FORM_RECOGNIZER_KEY[-4:] if settings.AZURE_FORM_RECOGNIZER_KEY else 'N/A'}")
    
    async def extract_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract invoice data from PDF using Document Intelligence OCR only.
        No database operations, no LLM fallback.
        
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
        
        # Step 1: Run Document Intelligence OCR
        print("\nStep 1: Running Document Intelligence OCR...")
        start_time = datetime.utcnow()
        
        di_result = await asyncio.to_thread(
            self.di_client.analyze_invoice,
            file_content
        )
        
        end_time = datetime.utcnow()
        di_duration = (end_time - start_time).total_seconds()
        
        if not di_result or "error" in di_result:
            print(f"DI Error: {di_result.get('error', 'Unknown error')}")
            return {"error": "Document Intelligence failed", "details": di_result}
        
        print(f"DI completed successfully in {di_duration:.2f} seconds")
        
        # Step 2: Extract fields using FieldExtractor
        print("\nStep 2: Extracting fields from DI result...")
        invoice = self.field_extractor.extract_invoice(
            doc_intelligence_data=di_result,
            file_path=pdf_path,
            file_name=os.path.basename(pdf_path),
            upload_date=datetime.utcnow()
        )
        
        # Set ID for tracking
        invoice.id = f"standalone-di-test-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        invoice.processing_state = InvoiceState.EXTRACTED
        
        # Count extracted fields
        extracted_count = len([f for f, v in invoice.model_dump().items() if v is not None and f in CANONICAL_FIELDS])
        print(f"Extracted {extracted_count} fields from DI OCR")
        
        # Step 3: Analyze field confidence
        print("\nStep 3: Analyzing field confidence scores...")
        field_confidence = invoice.field_confidence or {}
        
        confidence_ranges = {
            "high": (0.75, 1.0),
            "medium": (0.50, 0.75),
            "low": (0.0, 0.50),
            "none": (None, None)
        }
        
        confidence_distribution = {range_name: 0 for range_name in confidence_ranges.keys()}
        confidence_distribution["none"] = 0
        
        for field_name in CANONICAL_FIELDS:
            confidence = field_confidence.get(field_name)
            if confidence is None:
                confidence_distribution["none"] += 1
            elif confidence >= 0.75:
                confidence_distribution["high"] += 1
            elif confidence >= 0.50:
                confidence_distribution["medium"] += 1
            else:
                confidence_distribution["low"] += 1
        
        print(f"Confidence distribution:")
        print(f"  - High (>=0.75): {confidence_distribution['high']}")
        print(f"  - Medium (0.50-0.75): {confidence_distribution['medium']}")
        print(f"  - Low (<0.50): {confidence_distribution['low']}")
        print(f"  - None: {confidence_distribution['none']}")
        
        # Step 4: Collect results
        print("\nStep 4: Collecting extraction results...")
        
        # Build results dictionary
        results = {
            "invoice_id": invoice.id,
            "file_name": os.path.basename(pdf_path),
            "pdf_size_bytes": len(file_content),
            "di_success": True,
            "di_duration_seconds": di_duration,
            "di_fields_extracted": extracted_count,
            "extraction_confidence": invoice.extraction_confidence,
            "field_confidence": invoice.field_confidence,
            "confidence_distribution": confidence_distribution,
            "extracted_fields": {},
            "canonical_fields_coverage": {},
            "di_raw_fields": {}  # Store raw DI field names for mapping analysis
        }
        
        # Collect extracted field values and map DI field names (higher-level invoice fields)
        for field_name in sorted(CANONICAL_FIELDS):
            field_value = getattr(invoice, field_name, None)
            confidence = field_confidence.get(field_name, None)
            
            # Determine if field was extracted
            is_extracted = False
            if field_value is not None:
                # Handle Address objects (Pydantic models)
                if hasattr(field_value, 'model_dump'):
                    # Check if Address has any non-None values
                    address_dict = field_value.model_dump()
                    is_extracted = any(v for v in address_dict.values() if v is not None and (not isinstance(v, str) or v.strip() != ""))
                elif isinstance(field_value, str):
                    is_extracted = field_value.strip() != ""
                elif isinstance(field_value, (int, float, Decimal)):
                    is_extracted = field_value != 0
                elif isinstance(field_value, dict):
                    is_extracted = len(field_value) > 0 and any(v for v in field_value.values() if v is not None and (not isinstance(v, str) or v.strip() != ""))
                elif isinstance(field_value, list):
                    is_extracted = len(field_value) > 0
                else:
                    is_extracted = True
            
            # Try to find which DI field(s) mapped to this canonical field
            di_field_sources = []
            if di_result:
                # Check common DI field names that map to this canonical field
                # DI_TO_CANONICAL is a class attribute, access via FieldExtractor
                for di_field, canonical_field in FieldExtractor.DI_TO_CANONICAL.items():
                    if canonical_field == field_name:
                        # Check if this DI field exists in the result
                        if di_field in di_result or di_field.lower() in str(di_result).lower():
                            di_field_sources.append(di_field)
            
            results["extracted_fields"][field_name] = {
                "value": field_value,
                "confidence": confidence,
                "extracted": is_extracted,
                "di_field_sources": di_field_sources[:3] if di_field_sources else [],  # Limit to first 3
                "confidence_category": (
                    "high" if confidence is not None and confidence >= 0.75 else
                    "medium" if confidence is not None and confidence >= 0.50 else
                    "low" if confidence is not None and confidence > 0 else
                    "none"
                )
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
        # Check DI result for Items field
        di_field_sources = []
        if di_result and "Items" in str(di_result):
            di_field_sources = ["Items"]
        
        results["extracted_fields"]["line_items"] = {
            "value": line_items_value,
            "confidence": line_items_confidence,
            "extracted": len(line_items_value) > 0,
            "di_field_sources": di_field_sources,
            "confidence_category": (
                "high" if line_items_confidence is not None and line_items_confidence >= 0.75 else
                "medium" if line_items_confidence is not None and line_items_confidence >= 0.50 else
                "low" if line_items_confidence is not None and line_items_confidence > 0 else
                "none"
            )
        }
        
        # Calculate coverage statistics
        total_fields = len(CANONICAL_FIELDS)
        extracted_count = sum(1 for f in results["extracted_fields"].values() if f["extracted"])
        high_conf_count = sum(1 for f in results["extracted_fields"].values() 
                             if f.get("confidence_category") == "high")
        medium_conf_count = sum(1 for f in results["extracted_fields"].values() 
                                if f.get("confidence_category") == "medium")
        low_conf_count = sum(1 for f in results["extracted_fields"].values() 
                            if f.get("confidence_category") == "low")
        
        results["canonical_fields_coverage"] = {
            "total": total_fields,
            "extracted": extracted_count,
            "missing": total_fields - extracted_count,
            "extraction_rate": (extracted_count / total_fields * 100) if total_fields > 0 else 0,
            "high_confidence": high_conf_count,
            "medium_confidence": medium_conf_count,
            "low_confidence": low_conf_count,
            "no_confidence": total_fields - (high_conf_count + medium_conf_count + low_conf_count)
        }
        
        print(f"\nExtraction Summary:")
        print(f"  - Total canonical fields: {total_fields}")
        print(f"  - Fields extracted: {extracted_count} ({results['canonical_fields_coverage']['extraction_rate']:.1f}%)")
        print(f"  - Fields missing: {total_fields - extracted_count}")
        print(f"  - High confidence (>=0.75): {high_conf_count}")
        print(f"  - Medium confidence (0.50-0.75): {medium_conf_count}")
        print(f"  - Low confidence (<0.50): {low_conf_count}")
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
                "confidence_category": field_data.get("confidence_category", "none"),
                "di_field_sources": ", ".join(field_data.get("di_field_sources", [])) if field_data.get("di_field_sources") else None,
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
        report.append("# DI OCR Extraction Report (Standalone Test)")
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
        report.append(f"- **DI Duration:** {results['di_duration_seconds']:.2f} seconds")
        report.append(f"- **DI Fields Extracted:** {results['di_fields_extracted']}")
        report.append(f"- **Overall Extraction Confidence:** {results['extraction_confidence']}")
        report.append("")
        
        # Confidence Distribution
        conf_dist = results['confidence_distribution']
        report.append("## Confidence Distribution")
        report.append("")
        report.append(f"- **High Confidence (>=0.75):** {conf_dist['high']}")
        report.append(f"- **Medium Confidence (0.50-0.75):** {conf_dist['medium']}")
        report.append(f"- **Low Confidence (<0.50):** {conf_dist['low']}")
        report.append(f"- **No Confidence:** {conf_dist['none']}")
        report.append("")
        
        # Coverage
        coverage = results['canonical_fields_coverage']
        report.append("## Canonical Field Coverage")
        report.append("")
        report.append(f"- **Total Canonical Fields:** {coverage['total']}")
        report.append(f"- **Fields Extracted:** {coverage['extracted']} ({coverage['extraction_rate']:.1f}%)")
        report.append(f"- **Fields Missing:** {coverage['missing']} ({100 - coverage['extraction_rate']:.1f}%)")
        report.append(f"- **High Confidence:** {coverage['high_confidence']}")
        report.append(f"- **Medium Confidence:** {coverage['medium_confidence']}")
        report.append(f"- **Low Confidence:** {coverage['low_confidence']}")
        report.append(f"- **No Confidence:** {coverage['no_confidence']}")
        report.append("")
        
        # Field-by-field details
        report.append("## Extracted Fields")
        report.append("")
        report.append("| Field Name | Extracted | Confidence | Category | DI Source | Value Preview |")
        report.append("|------------|-----------|------------|----------|-----------|---------------|")
        
        for field_name, field_data in sorted(results["extracted_fields"].items()):
            extracted_str = "[YES]" if field_data["extracted"] else "[NO]"
            conf_str = f"{field_data['confidence']:.2f}" if field_data['confidence'] is not None else "N/A"
            category = field_data.get("confidence_category", "none")
            di_sources = ", ".join(field_data.get("di_field_sources", [])[:2]) if field_data.get("di_field_sources") else "-"
            if len(field_data.get("di_field_sources", [])) > 2:
                di_sources += "..."
            
            value_preview = str(field_data['value'])[:30] if field_data['value'] is not None else "None"
            if field_data['value'] is not None and len(str(field_data['value'])) > 30:
                value_preview += "..."
            
            report.append(f"| {field_name} | {extracted_str} | {conf_str} | {category} | {di_sources} | {value_preview} |")
        
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
        extractor = StandaloneDIOCRExtractor()
        
        # Run extraction
        results = await extractor.extract_from_pdf(sample_pdf)
        
        if "error" in results:
            print(f"\nExtraction failed: {results['error']}")
            return
        
        # Convert to DataFrame
        df = extractor.results_to_dataframe(results)
        
        # Display DataFrame
        print("\n" + "="*80)
        print("EXTRACTION RESULTS (DataFrame)")
        print("="*80)
        print(df.to_string(index=False))
        
        # Save DataFrame to CSV
        csv_path = "di_ocr_extraction_results.csv"
        df.to_csv(csv_path, index=False)
        print(f"\nDataFrame saved to: {csv_path}")
        
        # Generate and save report
        report_path = "di_ocr_extraction_report.md"
        report = extractor.generate_report(results, output_path=report_path)
        
        # Print summary statistics
        print("\n" + "="*80)
        print("SUMMARY STATISTICS")
        print("="*80)
        coverage = results['canonical_fields_coverage']
        print(f"Total fields: {coverage['total']}")
        print(f"Extracted: {coverage['extracted']} ({coverage['extraction_rate']:.1f}%)")
        print(f"Missing: {coverage['missing']}")
        print(f"High confidence: {coverage['high_confidence']}")
        print(f"Medium confidence: {coverage['medium_confidence']}")
        print(f"Low confidence: {coverage['low_confidence']}")
        print(f"No confidence: {coverage['no_confidence']}")
        print(f"Overall confidence: {results['extraction_confidence']}")
        print(f"DI duration: {results['di_duration_seconds']:.2f} seconds")
        
        # Print extracted fields by category
        print("\n" + "="*80)
        print("EXTRACTED FIELDS BY CATEGORY")
        print("="*80)
        
        categories = {
            "Header": ["invoice_number", "invoice_date", "due_date", "invoice_type", "reference_number"],
            "Vendor": ["vendor_name", "vendor_id", "vendor_phone", "vendor_fax", "vendor_email", "vendor_website", "vendor_address"],
            "Vendor Tax IDs": ["gst_number", "qst_number", "pst_number", "business_number"],
            "Customer": ["customer_name", "customer_id", "customer_phone", "customer_email", "customer_fax", "bill_to_address"],
            "Remit-To": ["remit_to_address", "remit_to_name"],
            "Contract": ["entity", "contract_id", "standing_offer_number", "po_number"],
            "Dates": ["period_start", "period_end", "shipping_date", "delivery_date"],
            "Financial": ["subtotal", "discount_amount", "shipping_amount", "handling_fee", "deposit_amount"],
            "Canadian Taxes": ["gst_amount", "gst_rate", "hst_amount", "hst_rate", "qst_amount", "qst_rate", "pst_amount", "pst_rate"],
            "Total": ["tax_amount", "total_amount", "currency"],
            "Payment": ["payment_terms", "payment_method", "payment_due_upon", "tax_registration_number"],
        }
        
        for category, fields in categories.items():
            extracted = sum(1 for f in fields if results["extracted_fields"].get(f, {}).get("extracted", False))
            high_conf = sum(1 for f in fields 
                          if results["extracted_fields"].get(f, {}).get("confidence_category") == "high")
            total = len(fields)
            rate = (extracted / total * 100) if total > 0 else 0
            print(f"{category:<20} {extracted}/{total} ({rate:.0f}%) [High conf: {high_conf}]")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

