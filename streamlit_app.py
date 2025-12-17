"""
Streamlit HITL (Human-in-the-Loop) Interface
Web UI for reviewing and validating extracted invoice data
"""

import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional
import io
import base64
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="Invoice Review & Validation",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theming (colors/fonts inspired by CATSA palette)
PRIMARY = "#c8102e"  # red accent
ACCENT = "#3f5359"   # dark teal/grey for headers
TEXT_COLOR = "#1f1f1f"
BG_COLOR = "#ffffff"
CARD_BG = "#ffffff"
FONT_FAMILY = "Arial, 'Helvetica Neue', sans-serif"

st.markdown(
    f"""
<style>
    html, body, [class*="css"]  {{
        font-family: {FONT_FAMILY};
        color: {TEXT_COLOR};
        background-color: {BG_COLOR};
    }}
    .confidence-high {{
        color: #1e8a3c;
        font-weight: 600;
    }}
    .confidence-medium {{
        color: #e2a400;
        font-weight: 600;
    }}
    .confidence-low {{
        color: {PRIMARY};
        font-weight: 600;
    }}
    .field-label {{
        font-weight: 600;
        color: {ACCENT};
    }}
    .stButton>button {{
        width: 100%;
        border-radius: 6px;
        border: 1px solid {ACCENT};
        background-color: {PRIMARY};
        color: white;
        font-weight: 600;
    }}
    .stButton>button:hover {{
        background-color: #a20d24;
        border-color: #a20d24;
    }}
    /* Section header underline */
    .section-title {{
        border-bottom: 3px solid {PRIMARY};
        padding-bottom: 4px;
        color: {ACCENT};
    }}
    /* Metric styling */
    .css-1ht1j8u, .css-12w0qpk {{
        color: {ACCENT} !important;
    }}
</style>
""",
    unsafe_allow_html=True,
)


def get_confidence_color(confidence: float) -> str:
    """Get CSS class for confidence level"""
    if confidence >= 0.9:
        return "confidence-high"
    elif confidence >= 0.7:
        return "confidence-medium"
    else:
        return "confidence-low"


def get_confidence_icon(confidence: float) -> str:
    """Get icon for confidence level"""
    if confidence >= 0.9:
        return "[OK]"
    elif confidence >= 0.7:
        return "[WARN]"
    else:
        return "[LOW]"


def format_confidence(confidence: float) -> str:
    """Format confidence as percentage"""
    return f"{confidence:.1%}"


@st.cache_data(ttl=60, show_spinner=False)
def load_invoice_list(status_filter: Optional[str] = None) -> list:
    """Load list of invoices from API"""
    try:
        params = {"limit": 100}
        if status_filter:
            params["status"] = status_filter
        
        response = requests.get(f"{API_BASE_URL}/api/hitl/invoices", params=params)
        if response.status_code == 200:
            data = response.json()
            invoices = data.get("invoices", [])
            # Sort newest first by upload_date if present
            def sort_key(inv):
                return inv.get("upload_date") or ""
            return sorted(invoices, key=sort_key, reverse=True)
        else:
            st.error(f"Error loading invoices: {response.status_code}")
            return []
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API. Make sure the API server is running.")
        return []
    except Exception as e:
        st.error(f"Error: {e}")
        return []


@st.cache_data(ttl=20, show_spinner=False)
def load_invoice(invoice_id: str) -> Optional[Dict[str, Any]]:
    """Load invoice details from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/hitl/invoice/{invoice_id}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error loading invoice: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def get_invoice_pdf(invoice_id: str) -> Optional[bytes]:
    """Get invoice PDF from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/hitl/invoice/{invoice_id}/pdf", timeout=30)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        st.error(f"Error loading PDF: {e}")
        return None


def submit_validation(invoice_id: str, field_validations: list, line_item_validations: list,
                     overall_status: str, reviewer: str, notes: str) -> bool:
    """Submit invoice validation"""
    try:
        payload = {
            "invoice_id": invoice_id,
            "field_validations": field_validations,
            "line_item_validations": line_item_validations,
            "overall_validation_status": overall_status,
            "reviewer": reviewer,
            "validation_notes": notes
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/hitl/invoice/validate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return True
        else:
            st.error(f"Validation failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        st.error(f"Error submitting validation: {e}")
        return False


def main():
    """Main Streamlit app"""
    
    # Optional logo if available (place file at ./assets/catsa_logo.png)
    logo_path = Path(__file__).parent / "assets" / "catsa_logo.png"
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        if logo_path.exists():
            st.image(str(logo_path), width=140)
    with col_title:
        st.title("Invoice Review & Validation")
        st.markdown(
            f'<div class="section-title">Human-in-the-Loop interface for reviewing extracted invoice data</div>',
            unsafe_allow_html=True,
        )
    
    # Sidebar
    with st.sidebar:
        st.title("Invoice Review")
        st.markdown("---")
        
        # Status filter
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "extracted", "in_review", "validated", "approved"],
            index=0
        )
        
        # Refresh button
        if st.button("Refresh Invoice List"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        # Instructions
        st.markdown("### How to Use")
        st.markdown("""
        1. Select an invoice from the list
        2. Review extracted fields
        3. Check confidence scores
        4. Correct any errors
        5. Submit validation
        """)
        
        st.markdown("---")
        st.markdown("### Confidence Levels")
        st.markdown("""
        - [OK] High (≥90%): Verified
        - [WARN] Medium (70-89%): Review
        - [LOW] Low (<70%): Requires correction
        """)

        st.markdown("---")
        st.markdown("### Upload & Extract")
        upload_file = st.file_uploader("Upload PDF", type=["pdf"])
        if upload_file is not None:
            if st.button("Upload and Extract"):
                try:
                    files = {"file": (upload_file.name, upload_file.getvalue(), "application/pdf")}
                    resp = requests.post(f"{API_BASE_URL}/api/ingestion/upload", files=files, timeout=120)
                    if resp.status_code == 201:
                        data = resp.json()
                        invoice_id = data.get("invoice_id")
                        file_path = data.get("file_path")
                        file_name = data.get("file_name") or upload_file.name
                        st.info("Uploaded. Triggering extraction...")
                        extract_resp = requests.post(
                            f"{API_BASE_URL}/api/extraction/extract/{invoice_id}",
                            params={"file_identifier": file_path, "file_name": file_name},
                            timeout=180,
                        )
                        if extract_resp.status_code == 200:
                            st.success("Extraction completed. Loading invoice...")
                            st.cache_data.clear()
                            st.session_state["selected_invoice_id"] = invoice_id
                            st.experimental_rerun()
                        else:
                            st.error(f"Extraction failed: {extract_resp.status_code} {extract_resp.text}")
                    else:
                        st.error(f"Upload failed: {resp.status_code} {resp.text}")
                except Exception as e:
                    st.error(f"Error during upload/extract: {e}")
    
    # Main content
    st.markdown("")

    # Load invoice list
    filter_status = None if status_filter == "All" else status_filter
    invoices = load_invoice_list(filter_status)
    
    if not invoices:
        st.info("No invoices found. Upload invoices using the API or demo scripts.")
        return
    
    # Invoice selector
    invoice_options = {
        f"{inv['invoice_number'] or 'N/A'} - {inv['vendor_name'] or 'Unknown'} - ${inv['total_amount'] or 0:,.2f}": inv['invoice_id']
        for inv in invoices
    }
    
    selected_invoice_label = st.selectbox(
        "Select Invoice",
        list(invoice_options.keys()),
        index=0
    )
    
    selected_invoice_id = invoice_options[selected_invoice_label]
    
    # Load invoice details
    with st.spinner("Loading invoice..."):
        invoice_data = load_invoice(selected_invoice_id)
    
    if not invoice_data:
        st.error("Could not load invoice details.")
        return
    
    # Display invoice information
    st.markdown("---")
    
    # Header info
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Invoice Number", invoice_data.get("fields", {}).get("invoice_number", {}).get("value", "N/A"))
    
    with col2:
        total_conf = invoice_data.get("extraction_confidence", 0.0)
        conf_icon = get_confidence_icon(total_conf)
        st.metric(
            "Overall Confidence",
            f"{conf_icon} {format_confidence(total_conf)}",
            help="Overall extraction confidence score"
        )
    
    with col3:
        st.metric("Status", invoice_data.get("status", "N/A"))
    
    with col4:
        total_val = invoice_data.get('fields', {}).get('total_amount', {}).get('value', None)
        try:
            total_val_num = float(total_val) if total_val is not None else 0.0
        except Exception:
            total_val_num = 0.0
        st.metric("Total Amount", f"${total_val_num:,.2f}")
    # Low confidence notice with emphasis
    if invoice_data.get("low_confidence_triggered"):
        lc_fields = invoice_data.get("low_confidence_fields", [])
        st.warning(f"Low confidence detected for: {', '.join(lc_fields) if lc_fields else 'multiple fields'}")

    # Layout: left persistent PDF, right tabs
    col_pdf, col_main = st.columns([1.1, 1.9])

    with col_pdf:
        st.subheader("Original Invoice PDF")
        pdf_url = f"{API_BASE_URL}/api/hitl/invoice/{selected_invoice_id}/pdf"
        st.markdown(f"[Open/Download PDF in new tab]({pdf_url})")
        pdf_content = get_invoice_pdf(selected_invoice_id)
        if pdf_content:
            base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
        else:
            st.warning("Could not inline-load the PDF. Use the link above to open/download.")

    with col_main:
        tab1, tab2, tab4 = st.tabs(["Fields", "Line Items", "Validation"])

        # Tab 1: Fields
        with tab1:
            st.subheader("Extracted Fields")
            
            fields = invoice_data.get("fields", {})
            
            # Group fields into sections
            header_fields = ["invoice_number", "invoice_date", "due_date", "po_number", "standing_offer_number"]
            vendor_fields = ["vendor_name", "vendor_id", "vendor_phone"]
            customer_fields = ["customer_name", "customer_id"]
            financial_fields = ["subtotal", "tax_amount", "total_amount", "currency", "payment_terms", "acceptance_percentage", "tax_registration_number"]
            
            # Header Information
            st.markdown("#### Header Information")
            header_cols = st.columns(3)
            
            for i, field_name in enumerate(header_fields):
                if field_name in fields:
                    field_data = fields[field_name]
                    value = field_data.get("value")
                    confidence = field_data.get("confidence", 0.0)
                    
                    with header_cols[i % 3]:
                        icon = get_confidence_icon(confidence)
                        conf_class = get_confidence_color(confidence)
                        
                        label = field_name.replace("_", " ").title()
                        st.text_input(
                            label,
                            value=str(value) if value else "",
                            key=f"field_{field_name}",
                            help=f"Confidence: {format_confidence(confidence)}"
                        )
                        st.markdown(f'<span class="{conf_class}">{icon} {format_confidence(confidence)}</span>', 
                                  unsafe_allow_html=True)
            
            # Vendor Information
            st.markdown("#### Vendor Information")
            vendor_cols = st.columns(2)
            
            for i, field_name in enumerate(vendor_fields):
                if field_name in fields:
                    field_data = fields[field_name]
                    value = field_data.get("value")
                    confidence = field_data.get("confidence", 0.0)
                    
                    with vendor_cols[i % 2]:
                        icon = get_confidence_icon(confidence)
                        conf_class = get_confidence_color(confidence)
                        
                        label = field_name.replace("_", " ").title()
                        st.text_input(
                            label,
                            value=str(value) if value else "",
                            key=f"field_{field_name}",
                            help=f"Confidence: {format_confidence(confidence)}"
                        )
                        st.markdown(f'<span class="{conf_class}">{icon} {format_confidence(confidence)}</span>', 
                                  unsafe_allow_html=True)
            
            # Customer Information
            st.markdown("#### Customer Information")
            customer_cols = st.columns(2)
            
            for i, field_name in enumerate(customer_fields):
                if field_name in fields:
                    field_data = fields[field_name]
                    value = field_data.get("value")
                    confidence = field_data.get("confidence", 0.0)
                    
                    with customer_cols[i % 2]:
                        icon = get_confidence_icon(confidence)
                        conf_class = get_confidence_color(confidence)
                        
                        label = field_name.replace("_", " ").title()
                        st.text_input(
                            label,
                            value=str(value) if value else "",
                            key=f"field_{field_name}",
                            help=f"Confidence: {format_confidence(confidence)}"
                        )
                        st.markdown(f'<span class="{conf_class}">{icon} {format_confidence(confidence)}</span>', 
                                  unsafe_allow_html=True)
            
            # Financial Information
            st.markdown("#### Financial Information")
            financial_cols = st.columns(3)
            
            for i, field_name in enumerate(financial_fields):
                if field_name in fields:
                    field_data = fields[field_name]
                    value = field_data.get("value")
                    confidence = field_data.get("confidence", 0.0)
                    
                    with financial_cols[i % 3]:
                        icon = get_confidence_icon(confidence)
                        conf_class = get_confidence_color(confidence)
                        
                        label = field_name.replace("_", " ").title()
                        if field_name in ["subtotal", "tax_amount", "total_amount", "acceptance_percentage"]:
                            st.number_input(
                                label,
                                value=float(value) if value else 0.0,
                                key=f"field_{field_name}",
                                format="%.2f",
                                help=f"Confidence: {format_confidence(confidence)}"
                            )
                        else:
                            st.text_input(
                                label,
                                value=str(value) if value else "",
                                key=f"field_{field_name}",
                                help=f"Confidence: {format_confidence(confidence)}"
                            )
                        st.markdown(f'<span class="{conf_class}">{icon} {format_confidence(confidence)}</span>', 
                                  unsafe_allow_html=True)
            
            # Addresses
            addresses = invoice_data.get("addresses", {})
            if addresses:
                st.markdown("#### Addresses")
                
                for addr_type, addr_data in addresses.items():
                    if addr_data.get("value"):
                        st.markdown(f"**{addr_type.replace('_', ' ').title()}:**")
                        addr = addr_data["value"]
                        st.text(f"{addr.get('street', '')}, {addr.get('city', '')}, {addr.get('province', '')} {addr.get('postal_code', '')}")
                        conf = addr_data.get("confidence", 0.0)
                        st.markdown(f'<span class="{get_confidence_color(conf)}">{get_confidence_icon(conf)} {format_confidence(conf)}</span>', unsafe_allow_html=True)

            # Re-run extraction for this invoice (uses existing file path/name)
            st.markdown("#### Re-run Extraction")
            if st.button("Re-run extraction for this invoice"):
                try:
                    file_path = invoice_data.get("file_path")
                    file_name = invoice_data.get("file_name", "invoice.pdf")
                    invoice_id = invoice_data.get("invoice_id")
                    if not file_path or not invoice_id:
                        st.error("Missing file path or invoice id; cannot re-run extraction.")
                    else:
                        resp = requests.post(
                            f"{API_BASE_URL}/api/extraction/extract/{invoice_id}",
                            params={"file_identifier": file_path, "file_name": file_name},
                            timeout=180,
                        )
                        if resp.status_code == 200:
                            st.success("Extraction re-run completed. Refreshing...")
                            st.cache_data.clear()
                            st.experimental_rerun()
                        else:
                            st.error(f"Extraction re-run failed: {resp.status_code} {resp.text}")
                except Exception as e:
                    st.error(f"Error re-running extraction: {e}")
    
        # Tab 2: Line Items
        with tab2:
            st.subheader("Line Items")
            
            line_items = invoice_data.get("line_items", [])
            
            if line_items:
                # Summary
                st.markdown(f"**Total Line Items:** {len(line_items)}")
                
                def safe_num(val, default=0.0):
                    try:
                        if val is None:
                            return default
                        return float(val)
                    except Exception:
                        return default

                # Line items table
                items_data = []
                for item in line_items:
                    items_data.append({
                        "Line": item.get("line_number"),
                        "Description": item.get("description", "")[:50],
                        "Qty": safe_num(item.get("quantity")),
                        "Unit Price": f"${safe_num(item.get('unit_price'), 0):,.2f}",
                        "Amount": f"${safe_num(item.get('amount'), 0):,.2f}",
                        "Confidence": format_confidence(item.get("confidence", 0.0))
                    })
                
                st.dataframe(items_data, use_container_width=True)
                
                # Detailed view
                st.markdown("#### Detailed View")
                for item in line_items:
                    with st.expander(f"Line {item.get('line_number')}: {item.get('description', '')[:50]}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.text_input("Description", value=item.get("description", ""), key=f"item_{item.get('line_number')}_desc")
                            st.number_input("Quantity", value=safe_num(item.get("quantity"), 0.0), key=f"item_{item.get('line_number')}_qty")
                            st.number_input("Amount", value=safe_num(item.get("amount"), 0.0), format="%.2f", key=f"item_{item.get('line_number')}_amount")
                        
                        with col2:
                            st.number_input("Unit Price", value=safe_num(item.get("unit_price"), 0.0), format="%.2f", key=f"item_{item.get('line_number')}_price")
                            conf = item.get("confidence", 0.0)
                            conf_class = get_confidence_color(conf)
                            st.markdown(f'<span class="{conf_class}">{get_confidence_icon(conf)} Confidence: {format_confidence(conf)}</span>', 
                                      unsafe_allow_html=True)
            else:
                st.info("No line items found.")
    
        # Tab 4: Validation
        with tab4:
            st.subheader("Submit Validation")
            
            reviewer_name = st.text_input("Reviewer Name", value="", placeholder="Enter your name")
            
            validation_status = st.selectbox(
                "Validation Status",
                ["pending", "validated", "needs_review"],
                index=0
            )
            
            validation_notes = st.text_area(
                "Validation Notes",
                placeholder="Add any notes or comments about this validation..."
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Submit Validation", type="primary"):
                    if not reviewer_name:
                        st.warning("Please enter your name as reviewer.")
                    else:
                        # Collect field validations (simplified - would collect from form in full implementation)
                        field_validations = []
                        line_item_validations = []
                        
                        # Submit validation
                        success = submit_validation(
                            selected_invoice_id,
                            field_validations,
                            line_item_validations,
                            validation_status,
                            reviewer_name,
                            validation_notes
                        )
                        
                        if success:
                            st.success("Validation submitted successfully!")
                            st.rerun()
            
            with col2:
                if st.button("Reset"):
                    st.rerun()
            
            # Review history
            st.markdown("---")
            st.markdown("#### Review History")
            
            if invoice_data.get("reviewer"):
                st.info(f"""
                **Reviewed by:** {invoice_data.get("reviewer")}  
                **Status:** {invoice_data.get("review_status", "N/A")}  
                **Date:** {invoice_data.get("review_timestamp", "N/A")}
                """)
            else:
                st.info("No review history available.")


if __name__ == "__main__":
    main()

