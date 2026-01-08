"""ERP staging service for formatting invoices for MS Dynamics Great Plains"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime, date
from decimal import Decimal
import json
import csv
import xml.etree.ElementTree as ET
from io import StringIO

from src.models.invoice import Invoice
from src.services.db_service import DatabaseService
from src.ingestion.file_handler import FileHandler

logger = logging.getLogger(__name__)


class ERPPayloadFormat(str, Enum):
    """Supported ERP payload formats"""
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    DYNAMICS_GP = "dynamics_gp"  # Microsoft Dynamics GP specific format


class ERPPayloadGenerator:
    """Generator for ERP-ready invoice payloads (MS Dynamics Great Plains)"""
    
    def __init__(self, erp_format: ERPPayloadFormat = ERPPayloadFormat.DYNAMICS_GP):
        """
        Initialize ERP payload generator
        
        Args:
            erp_format: Target ERP format (default: Dynamics GP)
        """
        self.erp_format = erp_format
    
    def generate_payload(
        self,
        invoice: Invoice,
        include_overlay_pdf: bool = False
    ) -> Dict[str, Any]:
        """
        Generate ERP payload for an approved invoice
        
        Args:
            invoice: Pydantic Invoice model
            include_overlay_pdf: Whether to include PDF overlay reference
            
        Returns:
            Dictionary with payload data:
            {
                "format": str,
                "payload": str (serialized),
                "invoice_id": str,
                "invoice_number": str,
                "vendor_id": str,
                "total_amount": Decimal,
                "currency": str,
                "export_timestamp": datetime,
                "overlay_pdf_path": Optional[str]
            }
        """
        # Build payload structure
        payload_data = self._build_payload_structure(invoice)
        
        # Serialize based on format
        if self.erp_format == ERPPayloadFormat.JSON:
            payload_str = self._serialize_json(payload_data)
        elif self.erp_format == ERPPayloadFormat.CSV:
            payload_str = self._serialize_csv(payload_data)
        elif self.erp_format == ERPPayloadFormat.XML:
            payload_str = self._serialize_xml(payload_data)
        elif self.erp_format == ERPPayloadFormat.DYNAMICS_GP:
            payload_str = self._serialize_dynamics_gp(payload_data)
        else:
            raise ValueError(f"Unsupported ERP format: {self.erp_format}")
        
        result = {
            "format": self.erp_format.value,
            "payload": payload_str,
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "vendor_id": invoice.vendor_id or invoice.vendor_name,
            "total_amount": invoice.total_amount,
            "currency": invoice.currency,
            "export_timestamp": datetime.utcnow(),
        }
        
        if include_overlay_pdf:
            result["overlay_pdf_path"] = f"overlays/{invoice.id}.pdf"
        
        return result
    
    def _build_payload_structure(self, invoice: Invoice) -> Dict[str, Any]:
        """
        Build ERP payload structure from invoice data
        
        Args:
            invoice: Pydantic Invoice model
            
        Returns:
            Dictionary with ERP payload structure
        """
        # Get GL coding from line items or defaults
        gl_code = self._get_gl_code(invoice)
        cost_centre = self._get_cost_centre(invoice)
        project_code = self._get_project_code(invoice)
        site_code = self._get_site_code(invoice)
        
        # Build header
        payload = {
            "voucher_type": "AP",  # Accounts Payable
            "vendor_id": invoice.vendor_id or invoice.vendor_name or "",
            "vendor_name": invoice.vendor_name or "",
            "invoice_number": invoice.invoice_number or "",
            "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "currency": invoice.currency or "CAD",
            "subtotal": str(invoice.subtotal) if invoice.subtotal else "0.00",
            "tax_amount": str(invoice.tax_amount) if invoice.tax_amount else "0.00",
            "total_amount": str(invoice.total_amount) if invoice.total_amount else "0.00",
            "payment_terms": invoice.payment_terms or "",
            "po_number": invoice.po_number or "",
            "contract_id": invoice.contract_id or "",
            "site_code": site_code or "",
            "reference": invoice.id,
            "entry_date": datetime.utcnow().isoformat(),
            "approved_by": {
                "business_verifier": invoice.bv_approver or "",
                "business_verification_date": invoice.bv_approval_date.isoformat() if invoice.bv_approval_date else None,
                "financial_authorizer": invoice.fa_approver or "",
                "financial_authorization_date": invoice.fa_approval_date.isoformat() if invoice.fa_approval_date else None,
            },
            "line_items": []
        }
        
        # Add tax breakdown
        payload["tax_breakdown"] = self._build_tax_breakdown(invoice)
        
        # Build line items
        for idx, line_item in enumerate(invoice.line_items, start=1):
            line_payload = {
                "line_number": idx,
                "description": line_item.description or "",
                "quantity": str(line_item.quantity) if line_item.quantity else None,
                "unit_price": str(line_item.unit_price) if line_item.unit_price else None,
                "amount": str(line_item.amount),
                "gl_code": self._get_line_gl_code(line_item, gl_code),
                "cost_centre": self._get_line_cost_centre(line_item, cost_centre),
                "project_code": self._get_line_project_code(line_item, project_code),
                "tax_code": self._get_tax_code(line_item),
                "tax_amount": str(line_item.tax_amount) if line_item.tax_amount else None,
                "unit_of_measure": line_item.unit_of_measure,
            }
            
            # Add subtype-specific line data
            if invoice.invoice_subtype and invoice.extensions:
                if invoice.invoice_subtype.value == "PER_DIEM_TRAVEL_INVOICE":
                    travel_data = invoice.extensions.per_diem_travel
                    if travel_data and idx <= len(travel_data):
                        travel_ext = travel_data[idx - 1]
                        line_payload["traveller_id"] = travel_ext.traveller_id
                        line_payload["traveller_name"] = travel_ext.traveller_name
                        line_payload["course_code"] = travel_ext.programme_or_course_code
                        line_payload["travel_days"] = travel_ext.travel_days
                        line_payload["daily_rate"] = str(travel_ext.daily_rate) if travel_ext.daily_rate else None
                
                elif invoice.invoice_subtype.value == "SHIFT_SERVICE_INVOICE":
                    shift_service = invoice.extensions.shift_service
                    if shift_service:
                        line_payload["service_location"] = shift_service.service_location
                        line_payload["shift_rate"] = str(shift_service.shift_rate) if shift_service.shift_rate else None
                        line_payload["total_shifts"] = shift_service.total_shifts_billed
            
            payload["line_items"].append(line_payload)
        
        return payload
    
    def _get_gl_code(self, invoice: Invoice) -> Optional[str]:
        """Get GL code from line items or defaults"""
        if invoice.line_items:
            for item in invoice.line_items:
                # GL code might be in project_code or a separate field
                # For vanilla, we'll need to get from HITL validation
                pass
        return None
    
    def _get_cost_centre(self, invoice: Invoice) -> Optional[str]:
        """Get cost centre from line items"""
        if invoice.line_items:
            for item in invoice.line_items:
                if item.cost_centre_code:
                    return item.cost_centre_code
        return None
    
    def _get_project_code(self, invoice: Invoice) -> Optional[str]:
        """Get project code from line items"""
        if invoice.line_items:
            for item in invoice.line_items:
                if item.project_code:
                    return item.project_code
        return None
    
    def _get_site_code(self, invoice: Invoice) -> Optional[str]:
        """Get site code from extensions or line items"""
        if invoice.extensions:
            if invoice.extensions.shift_service:
                return invoice.extensions.shift_service.service_location
        
        if invoice.line_items:
            for item in invoice.line_items:
                if item.airport_code:
                    return item.airport_code
        
        return None
    
    def _get_line_gl_code(self, line_item, default: Optional[str]) -> Optional[str]:
        """Get GL code for line item"""
        # Could be stored in line item metadata
        return default
    
    def _get_line_cost_centre(self, line_item, default: Optional[str]) -> Optional[str]:
        """Get cost centre for line item"""
        return line_item.cost_centre_code or default
    
    def _get_line_project_code(self, line_item, default: Optional[str]) -> Optional[str]:
        """Get project code for line item"""
        return line_item.project_code or default
    
    def _get_tax_code(self, line_item) -> Optional[str]:
        """Get tax code for line item"""
        if line_item.tax_amount and line_item.tax_amount > 0:
            return "GST"  # Default - could be more sophisticated
        return None
    
    def _build_tax_breakdown(self, invoice: Invoice) -> List[Dict[str, Any]]:
        """Build tax breakdown with recoverable/non-recoverable portions"""
        tax_breakdown = []
        
        if invoice.tax_amount:
            # Use tax_breakdown if available, otherwise default
            if invoice.tax_breakdown:
                for tax_type, tax_amount in invoice.tax_breakdown.items():
                    tax_breakdown.append({
                        "tax_type": tax_type,
                        "tax_rate": "0.13",  # Default - should be calculated
                        "tax_amount": str(tax_amount),
                        "recoverable_amount": str(tax_amount),  # Default: all recoverable
                        "non_recoverable_amount": "0.00"
                    })
            else:
                # Default: assume all tax is recoverable
                tax_breakdown.append({
                    "tax_type": "GST",
                    "tax_rate": "0.13",
                    "tax_amount": str(invoice.tax_amount),
                    "recoverable_amount": str(invoice.tax_amount),
                    "non_recoverable_amount": "0.00"
                })
        
        return tax_breakdown
    
    def _serialize_json(self, data: Dict[str, Any]) -> str:
        """Serialize payload to JSON"""
        return json.dumps(data, indent=2, default=str)
    
    def _serialize_csv(self, data: Dict[str, Any]) -> str:
        """Serialize payload to CSV format (header + line items)"""
        output = StringIO()
        writer = csv.writer(output)
        
        # Header row
        writer.writerow([
            "Voucher Type", "Vendor ID", "Invoice Number", "Invoice Date",
            "Due Date", "Total Amount", "Currency", "PO Number", "Contract ID"
        ])
        
        # Header data row
        writer.writerow([
            data.get("voucher_type"),
            data.get("vendor_id"),
            data.get("invoice_number"),
            data.get("invoice_date"),
            data.get("due_date"),
            data.get("total_amount"),
            data.get("currency"),
            data.get("po_number"),
            data.get("contract_id"),
        ])
        
        # Line items header
        writer.writerow([])  # Blank row
        writer.writerow([
            "Line Number", "Description", "Quantity", "Unit Price",
            "Amount", "GL Code", "Cost Centre", "Project Code", "Tax Amount"
        ])
        
        # Line items data
        for line_item in data.get("line_items", []):
            writer.writerow([
                line_item.get("line_number"),
                line_item.get("description"),
                line_item.get("quantity"),
                line_item.get("unit_price"),
                line_item.get("amount"),
                line_item.get("gl_code"),
                line_item.get("cost_centre"),
                line_item.get("project_code"),
                line_item.get("tax_amount"),
            ])
        
        return output.getvalue()
    
    def _serialize_xml(self, data: Dict[str, Any]) -> str:
        """Serialize payload to XML format"""
        root = ET.Element("Voucher")
        root.set("Type", data.get("voucher_type", "AP"))
        
        # Header
        header = ET.SubElement(root, "Header")
        ET.SubElement(header, "VendorID").text = str(data.get("vendor_id", ""))
        ET.SubElement(header, "VendorName").text = str(data.get("vendor_name", ""))
        ET.SubElement(header, "InvoiceNumber").text = str(data.get("invoice_number", ""))
        ET.SubElement(header, "InvoiceDate").text = str(data.get("invoice_date", ""))
        ET.SubElement(header, "DueDate").text = str(data.get("due_date", ""))
        ET.SubElement(header, "TotalAmount").text = str(data.get("total_amount", ""))
        ET.SubElement(header, "Currency").text = str(data.get("currency", ""))
        ET.SubElement(header, "PONumber").text = str(data.get("po_number", ""))
        ET.SubElement(header, "ContractID").text = str(data.get("contract_id", ""))
        ET.SubElement(header, "SiteCode").text = str(data.get("site_code", ""))
        ET.SubElement(header, "Reference").text = str(data.get("reference", ""))
        
        # Tax Breakdown
        if data.get("tax_breakdown"):
            tax_elem = ET.SubElement(header, "TaxBreakdown")
            for tax in data["tax_breakdown"]:
                tax_item = ET.SubElement(tax_elem, "Tax")
                ET.SubElement(tax_item, "TaxType").text = str(tax.get("tax_type", ""))
                ET.SubElement(tax_item, "TaxRate").text = str(tax.get("tax_rate", ""))
                ET.SubElement(tax_item, "TaxAmount").text = str(tax.get("tax_amount", ""))
                ET.SubElement(tax_item, "RecoverableAmount").text = str(tax.get("recoverable_amount", ""))
                ET.SubElement(tax_item, "NonRecoverableAmount").text = str(tax.get("non_recoverable_amount", ""))
        
        # Approvals
        if data.get("approved_by"):
            approvals = ET.SubElement(header, "Approvals")
            approved_by = data["approved_by"]
            ET.SubElement(approvals, "BusinessVerifier").text = str(approved_by.get("business_verifier", ""))
            ET.SubElement(approvals, "BusinessVerificationDate").text = str(approved_by.get("business_verification_date", ""))
            ET.SubElement(approvals, "FinancialAuthorizer").text = str(approved_by.get("financial_authorizer", ""))
            ET.SubElement(approvals, "FinancialAuthorizationDate").text = str(approved_by.get("financial_authorization_date", ""))
        
        # Line Items
        line_items_elem = ET.SubElement(root, "LineItems")
        for line_item in data.get("line_items", []):
            line_elem = ET.SubElement(line_items_elem, "LineItem")
            ET.SubElement(line_elem, "LineNumber").text = str(line_item.get("line_number", ""))
            ET.SubElement(line_elem, "Description").text = str(line_item.get("description", ""))
            ET.SubElement(line_elem, "Quantity").text = str(line_item.get("quantity", "")) if line_item.get("quantity") else ""
            ET.SubElement(line_elem, "UnitPrice").text = str(line_item.get("unit_price", "")) if line_item.get("unit_price") else ""
            ET.SubElement(line_elem, "Amount").text = str(line_item.get("amount", ""))
            ET.SubElement(line_elem, "GLCode").text = str(line_item.get("gl_code", ""))
            ET.SubElement(line_elem, "CostCentre").text = str(line_item.get("cost_centre", ""))
            ET.SubElement(line_elem, "ProjectCode").text = str(line_item.get("project_code", ""))
            ET.SubElement(line_elem, "TaxCode").text = str(line_item.get("tax_code", "")) if line_item.get("tax_code") else ""
            ET.SubElement(line_elem, "TaxAmount").text = str(line_item.get("tax_amount", "")) if line_item.get("tax_amount") else ""
            ET.SubElement(line_elem, "UnitOfMeasure").text = str(line_item.get("unit_of_measure", "")) if line_item.get("unit_of_measure") else ""
        
        return ET.tostring(root, encoding="unicode")
    
    def _serialize_dynamics_gp(self, data: Dict[str, Any]) -> str:
        """
        Serialize payload to Microsoft Dynamics GP format
        
        Dynamics GP typically uses XML format with specific schema.
        This is a simplified version - production would match GP's exact schema.
        """
        # Use XML format as base (Dynamics GP typically accepts XML)
        return self._serialize_xml(data)


class ERPStagingService:
    """Service for staging invoices for ERP export"""
    
    def __init__(
        self,
        erp_format: ERPPayloadFormat = ERPPayloadFormat.DYNAMICS_GP,
        file_handler: Optional[FileHandler] = None
    ):
        """
        Initialize ERP staging service
        
        Args:
            erp_format: Target ERP format
            file_handler: FileHandler instance for storage
        """
        self.payload_generator = ERPPayloadGenerator(erp_format=erp_format)
        self.file_handler = file_handler or FileHandler()
    
    async def stage_invoice(
        self,
        invoice_id: str,
        generate_overlay: bool = False,
        require_approval: bool = True
    ) -> Dict[str, Any]:
        """
        Stage an invoice for ERP export
        
        Args:
            invoice_id: Invoice ID
            generate_overlay: Whether to generate PDF overlay
            require_approval: Whether invoice must be approved before staging
            
        Returns:
            Dictionary with staging result
        """
        # Get invoice from database
        invoice = await DatabaseService.get_invoice(invoice_id)
        if not invoice:
            return {
                "success": False,
                "message": f"Invoice {invoice_id} not found"
            }
        
        # Check if invoice is approved (if required)
        if require_approval:
            if not invoice.fa_approver or not invoice.fa_approval_date:
                return {
                    "success": False,
                    "message": "Invoice must be approved (FA) before staging for ERP export"
                }
        
        try:
            # Generate ERP payload
            logger.info(f"Generating ERP payload for invoice: {invoice_id}")
            payload_result = self.payload_generator.generate_payload(
                invoice=invoice,
                include_overlay_pdf=generate_overlay
            )
            
            # Save payload to storage
            file_extension = self.payload_generator.erp_format.value
            payload_path = f"staging/{invoice_id}/payload.{file_extension}"
            
            # Determine content type
            content_type_map = {
                "json": "application/json",
                "csv": "text/csv",
                "xml": "application/xml",
                "dynamics_gp": "application/xml"
            }
            content_type = content_type_map.get(file_extension, "text/plain")
            
            # Upload payload
            upload_result = self.file_handler.upload_file(
                file_content=payload_result["payload"].encode("utf-8"),
                file_name=f"payload.{file_extension}",
                target_path=payload_path
            )
            
            result = {
                "success": True,
                "invoice_id": invoice_id,
                "payload_location": upload_result.get("file_path") or upload_result.get("blob_name"),
                "format": self.payload_generator.erp_format.value,
                "export_timestamp": payload_result["export_timestamp"].isoformat(),
            }
            
            # Generate PDF overlay if requested
            if generate_overlay:
                try:
                    from src.erp.pdf_overlay_renderer import PDFOverlayRenderer
                    overlay_renderer = PDFOverlayRenderer(file_handler=self.file_handler)
                    overlay_pdf = overlay_renderer.render_overlay(invoice)
                    
                    overlay_path = f"staging/{invoice_id}/overlay.pdf"
                    overlay_upload = self.file_handler.upload_file(
                        file_content=overlay_pdf,
                        file_name="overlay.pdf",
                        target_path=overlay_path
                    )
                    
                    result["overlay_location"] = overlay_upload.get("file_path") or overlay_upload.get("blob_name")
                except ImportError:
                    logger.warning("PDF overlay rendering not available - skipping overlay generation")
            
            # Update invoice status
            invoice.status = "staged_for_erp"
            await DatabaseService.save_invoice(invoice)
            
            logger.info(f"Invoice {invoice_id} staged successfully for ERP export")
            return result
            
        except Exception as e:
            logger.error(f"Error staging invoice {invoice_id}: {e}", exc_info=True)
            return {
                "success": False,
                "message": str(e),
                "invoice_id": invoice_id
            }
    
    async def batch_stage(
        self,
        invoice_ids: Optional[List[str]] = None,
        limit: int = 100,
        require_approval: bool = True
    ) -> Dict[str, Any]:
        """
        Batch stage multiple invoices for ERP export
        
        Args:
            invoice_ids: Optional list of specific invoice IDs to stage
            limit: Maximum number of invoices to stage if invoice_ids not provided
            require_approval: Whether invoices must be approved before staging
            
        Returns:
            Dictionary with batch staging results
        """
        if invoice_ids:
            invoices = []
            for invoice_id in invoice_ids:
                invoice = await DatabaseService.get_invoice(invoice_id)
                if invoice:
                    invoices.append(invoice)
        else:
            # Get approved invoices
            invoices = await DatabaseService.list_invoices(
                skip=0,
                limit=limit,
                status="approved"  # Assuming approved status
            )
        
        results = {
            "total": len(invoices),
            "successful": 0,
            "failed": 0,
            "staged": []
        }
        
        for invoice in invoices:
            stage_result = await self.stage_invoice(
                invoice.id,
                generate_overlay=False,
                require_approval=require_approval
            )
            
            if stage_result.get("success"):
                results["successful"] += 1
            else:
                results["failed"] += 1
            
            results["staged"].append(stage_result)
        
        return results
    
    async def get_payload(
        self,
        invoice_id: str,
        format: Optional[ERPPayloadFormat] = None
    ) -> Optional[str]:
        """
        Get staged payload for an invoice (for direct integration)
        
        Args:
            invoice_id: Invoice ID
            format: Optional format override
            
        Returns:
            Payload string or None if not found
        """
        # Get invoice
        invoice = await DatabaseService.get_invoice(invoice_id)
        if not invoice:
            return None
        
        # Generate payload
        if format:
            generator = ERPPayloadGenerator(erp_format=format)
        else:
            generator = self.payload_generator
        
        payload_result = generator.generate_payload(invoice)
        return payload_result["payload"]

