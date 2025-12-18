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
from copy import deepcopy

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


def load_invoice(invoice_id: str) -> Optional[Dict[str, Any]]:
    """Load invoice details from API (cache-busted to avoid stale data)."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/hitl/invoice/{invoice_id}",
            params={"_ts": time.time()},
        )
        if response.status_code == 200:
            invoice_data = response.json()
            # Store review_version in session state for optimistic locking
            if "invoice_review_version" not in st.session_state:
                st.session_state["invoice_review_version"] = {}
            review_version = int(invoice_data.get("review_version", 0))
            st.session_state["invoice_review_version"][invoice_id] = review_version
            return invoice_data
        else:
            st.error(f"Error loading invoice: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def list_blobs(container: str, prefix: Optional[str] = None) -> list:
    """List blobs from Azure storage via API."""
    try:
        params = {"container": container}
        if prefix:
            params["prefix"] = prefix
        resp = requests.get(f"{API_BASE_URL}/api/ingestion/blobs", params=params, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("blobs", [])
        st.error(f"Error listing blobs: {resp.status_code} {resp.text}")
        return []
    except Exception as e:
        st.error(f"Error listing blobs: {e}")
        return []


def ingest_blob(container: str, blob_name: str) -> Optional[Dict[str, Any]]:
    """Trigger ingestion for an existing blob."""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/ingestion/extract-blob",
            params={"container": container, "blob_name": blob_name},
            timeout=180,
        )
        if resp.status_code in (200, 201):
            return resp.json()
        st.error(f"Blob ingestion failed: {resp.status_code} {resp.text}")
        return None
    except Exception as e:
        st.error(f"Error ingesting blob: {e}")
        return None


def check_db_health() -> bool:
    """Ping DB health endpoint."""
    try:
        resp = requests.get(f"{API_BASE_URL}/api/ingestion/health/db", timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def _post_validation_payload(payload: dict) -> tuple[bool, Optional[dict]]:
    """
    POST validation payload.
    Returns: (success: bool, error_detail: Optional[dict])
    - On 200: (True, None)
    - On 409 STALE_WRITE: (False, error_detail_dict)
    - On other errors: (False, None)
    """
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/hitl/invoice/validate",
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            return (True, None)
        elif resp.status_code == 409:
            # Optimistic locking conflict - someone else updated the invoice
            try:
                resp_json = resp.json()
                # Handle both {"detail": {...}} and flat dict formats
                if "detail" in resp_json and isinstance(resp_json["detail"], dict):
                    detail = resp_json["detail"]
                else:
                    detail = resp_json
                
                error_code = detail.get("error_code", "CONFLICT")
                message = detail.get("message", "Invoice was updated by someone else.")
                current_version = detail.get("current_review_version")
                
                # Return error detail for caller to handle
                return (False, {
                    "error_code": error_code,
                    "message": message,
                    "current_review_version": current_version,
                    "invoice_id": detail.get("invoice_id"),
                })
            except Exception as parse_err:
                st.error(f"Conflict (409): {resp.text}")
                return (False, None)
        else:
            st.error(f"Validation failed: {resp.status_code} - {resp.text}")
            return (False, None)
    except Exception as e:
        st.error(f"Error submitting validation: {e}")
        return (False, None)


def _enqueue_pending(payload: dict):
    queue = st.session_state.get("pending_validations", [])
    queue.append(payload)
    st.session_state["pending_validations"] = queue


def _retry_pending_queue():
    queue = st.session_state.get("pending_validations", [])
    if not queue:
        st.info("No queued saves.")
        return
    succeeded = []
    failed = []
    for idx, payload in enumerate(list(queue)):
        ok, _ = _post_validation_payload(payload)  # Ignore error_detail for retries
        if ok:
            succeeded.append(idx)
        else:
            failed.append(idx)
    # remove succeeded in reverse order
    for idx in sorted(succeeded, reverse=True):
        queue.pop(idx)
    st.session_state["pending_validations"] = queue
    if succeeded:
        st.success(f"Pushed {len(succeeded)} queued save(s).")
    if failed:
        st.warning(f"{len(failed)} queued save(s) still pending.")


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


def load_validation_history(invoice_id: str) -> list:
    """Fetch validation/review history."""
    try:
        resp = requests.get(f"{API_BASE_URL}/api/hitl/invoice/{invoice_id}/history", timeout=15)
        if resp.status_code == 200:
            return resp.json() or []
        return []
    except Exception:
        return []


def reset_invoice_state(invoice_id: str, invoice_data: dict):
    """Reset edit buffers and validation history for the given invoice."""
    st.session_state["current_invoice_id"] = invoice_id
    st.session_state["edited_fields"] = invoice_data.get("fields", {}) or {}
    st.session_state["edited_addresses"] = invoice_data.get("addresses", {}) or {}
    st.session_state["edited_line_items"] = invoice_data.get("line_items", []) or []
    st.session_state["validation_history"] = load_validation_history(invoice_id)

    # Clear per-field widgets for this invoice
    for key in list(st.session_state.keys()):
        if key.startswith("field_"):
            del st.session_state[key]
        elif key.startswith(f"item_{invoice_id}_"):
            del st.session_state[key]
        elif key.startswith(f"{invoice_id}_"):
            del st.session_state[key]


def submit_validation(invoice_id: str, field_validations: list, line_item_validations: list,
                     overall_status: str, reviewer: str, notes: str) -> bool:
    """Submit invoice validation (legacy/helper function)"""
    payload = {
        "invoice_id": invoice_id,
        "field_validations": field_validations,
        "line_item_validations": line_item_validations,
        "overall_validation_status": overall_status,
        "reviewer": reviewer,
        "validation_notes": notes
    }
    success, _ = _post_validation_payload(payload)
    return success


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
                            st.rerun()
                        else:
                            st.error(f"Extraction failed: {extract_resp.status_code} {extract_resp.text}")
                    else:
                        try:
                            err_json = resp.json()
                            detail = err_json.get("detail") or err_json
                            msg = detail.get("message") if isinstance(detail, dict) else detail
                            errs = detail.get("errors") if isinstance(detail, dict) else None
                            if errs and isinstance(errs, list):
                                msg = f"{msg}: {', '.join(errs)}"
                            st.error(f"Upload failed: {msg}")
                        except Exception:
                            st.error(f"Upload failed: {resp.status_code} {resp.text}")
                except Exception as e:
                    st.error(f"Error during upload/extract: {e}")

        st.markdown("---")
        st.markdown("### Backend Health")
        db_ok = check_db_health()
        if db_ok:
            st.success("DB: reachable")
        else:
            st.error("DB: unreachable (will queue saves locally)")
        if st.button("Recheck DB"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Blob Browser (invoices-raw)")
        default_container = "invoices-raw"
        blob_prefix = st.text_input("Prefix (optional)", value="", placeholder="e.g., folder/")
        if st.button("List Blobs"):
            st.session_state["blob_list"] = list_blobs(default_container, blob_prefix or None)
        blobs = st.session_state.get("blob_list") or []
        blob_names = [b.get("name") for b in blobs if b.get("name")]
        selected_blob = st.selectbox("Select Blob", ["-- choose --"] + blob_names)
        if st.button("Ingest Selected Blob"):
            if selected_blob and selected_blob != "-- choose --":
                st.info(f"Ingesting blob: {selected_blob}")
                ingest_result = ingest_blob(default_container, selected_blob)
                if ingest_result:
                    new_invoice_id = ingest_result.get("invoice_id")
                    if new_invoice_id:
                        st.success(f"Ingested blob to invoice {new_invoice_id}. Loading...")
                        st.session_state["selected_invoice_id"] = new_invoice_id
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.warning("Please select a blob first.")
    
    # Main content
    st.markdown("")

    # Load invoice list
    filter_status = None if status_filter == "All" else status_filter
    invoices = load_invoice_list(filter_status)
    
    if not invoices:
        st.info("No invoices found. Upload invoices using the API or demo scripts.")
        return
    
    # Invoice selector with null default
    invoice_options = {
        f"{inv['invoice_number'] or 'N/A'} - {inv['vendor_name'] or 'Unknown'} - ${inv['total_amount'] or 0:,.2f}": inv['invoice_id']
        for inv in invoices
    }
    placeholder_label = "— Select an invoice —"
    option_labels = [placeholder_label] + list(invoice_options.keys())
    
    selected_invoice_label = st.selectbox(
        "Select Invoice",
        option_labels,
        index=0
    )
    
    if selected_invoice_label == placeholder_label:
        st.info("Please select an invoice to begin review.")
        return
    
    selected_invoice_id = invoice_options[selected_invoice_label]
    
    # Load invoice details
    with st.spinner("Loading invoice..."):
        invoice_data = load_invoice(selected_invoice_id)
    if not invoice_data:
        st.error("Could not load invoice details.")
        return
    # Initialize session state for the currently selected invoice (edit buffers and history)
    if st.session_state.get("current_invoice_id") != selected_invoice_id or "edited_line_items" not in st.session_state:
        reset_invoice_state(selected_invoice_id, invoice_data)
    elif "validation_history" not in st.session_state:
        st.session_state["validation_history"] = load_validation_history(selected_invoice_id)
    
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
        # Show edited total if present so the metric reflects pending changes
        edited_total = st.session_state.get(f"field_{selected_invoice_id}_total_amount")
        total_val = edited_total if edited_total is not None else invoice_data.get('fields', {}).get('total_amount', {}).get('value', None)
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
        with st.form("invoice_review_form"):
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["Company and Vendor", "Financial", "Line Items", "Addresses", "Validation"])

        # Tab 1: Company and Vendor
            with tab1:
                st.subheader("Company and Vendor")
                
                fields = invoice_data.get("fields", {})
                
                # Group fields into sections
                header_fields = ["invoice_number", "invoice_date", "due_date", "po_number", "standing_offer_number"]
                vendor_fields = ["vendor_name", "vendor_id", "vendor_phone"]
                customer_fields = ["customer_name", "customer_id"]
                
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
                                key=f"field_{selected_invoice_id}_{field_name}",
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
                                key=f"field_{selected_invoice_id}_{field_name}",
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
                                key=f"field_{selected_invoice_id}_{field_name}",
                                help=f"Confidence: {format_confidence(confidence)}"
                            )
                            st.markdown(f'<span class="{conf_class}">{icon} {format_confidence(confidence)}</span>', 
                                      unsafe_allow_html=True)
                
                # (Addresses moved to tab4)

    
            # Tab 2: Financial
            with tab2:
                st.subheader("Financial Information")
                fields = invoice_data.get("fields", {}) or {}
                financial_fields = [
                    "subtotal",
                    "tax_amount",
                    "total_amount",
                    "currency",
                    "payment_terms",
                    "acceptance_percentage",
                    "tax_registration_number",
                    "federal_tax",
                    "provincial_tax",
                    "combined_tax",
                ]
                financial_cols = st.columns(3)
                tax_breakdown = invoice_data.get("tax_breakdown", {}) or {}

                for i, field_name in enumerate(financial_fields):
                    field_data = fields.get(field_name) or {"value": tax_breakdown.get(field_name), "confidence": 0.0}
                    value = field_data.get("value")
                    confidence = field_data.get("confidence", 0.0)

                    with financial_cols[i % 3]:
                        icon = get_confidence_icon(confidence)
                        conf_class = get_confidence_color(confidence)

                        label = field_name.replace("_", " ").title()
                        if field_name in ["subtotal", "tax_amount", "total_amount", "acceptance_percentage", "federal_tax", "provincial_tax", "combined_tax"]:
                            st.number_input(
                                label,
                                value=float(value) if value else 0.0,
                                key=f"field_{selected_invoice_id}_{field_name}",
                                format="%.2f",
                                help=f"Confidence: {format_confidence(confidence)}"
                            )
                        else:
                            st.text_input(
                                label,
                                value=str(value) if value else "",
                                key=f"field_{selected_invoice_id}_{field_name}",
                                help=f"Confidence: {format_confidence(confidence)}"
                            )
                        st.markdown(
                            f'<span class="{conf_class}">{icon} {format_confidence(confidence)}</span>',
                            unsafe_allow_html=True,
                        )

            # Tab 3: Line Items
        with tab3:
            st.subheader("Line Items")
            
            line_items = st.session_state.get("edited_line_items", [])
            
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
                def current_line_value(ln: int, key: str, fallback):
                    return st.session_state.get(f"item_{selected_invoice_id}_{ln}_{key}", fallback)

                def compute_display_values(item):
                    ln = item.get("line_number")
                    qty = current_line_value(ln, "qty", item.get("quantity"))
                    unit_price = current_line_value(ln, "price", item.get("unit_price"))
                    gst = current_line_value(ln, "gst", item.get("gst_amount"))
                    pstqst = current_line_value(
                        ln,
                        "pstqst",
                        item.get("pst_amount") if item.get("pst_amount") is not None else item.get("qst_amount"),
                    )
                    combined = current_line_value(ln, "combined", item.get("combined_tax"))
                    tax_amount = current_line_value(ln, "tax_amount", item.get("tax_amount"))
                    amt = current_line_value(ln, "amount", item.get("amount"))
                    line_total = None
                    try:
                        if amt is not None:
                            line_total = float(amt)
                        elif qty is not None and unit_price is not None:
                            line_total = float(qty) * float(unit_price)
                    except Exception:
                        line_total = safe_num(amt, 0.0)
                    if line_total is None:
                        line_total = safe_num(amt, 0.0)
                    # allow editable subtotal override
                    subtotal_override = current_line_value(ln, "subtotal", None)
                    subtotal = safe_num(subtotal_override, line_total) if subtotal_override is not None else line_total
                    try:
                        if subtotal_override is None:
                            if tax_amount not in [None, ""]:
                                subtotal = line_total - float(tax_amount)
                            elif combined not in [None, ""]:
                                subtotal = line_total - float(combined)
                            else:
                                parts = [gst, pstqst]
                                if any(p is not None for p in parts):
                                    subtotal = line_total - sum(float(p) for p in parts if p is not None)
                    except Exception:
                        subtotal = line_total
                    return line_total, subtotal

                # Line items table
                items_data = []
                for item in line_items:
                    ln = item.get("line_number")
                    line_total, subtotal = compute_display_values(item)
                    items_data.append({
                        "Line": ln,
                        "Description": item.get("description", "")[:50],
                        "Qty": safe_num(current_line_value(ln, "qty", item.get("quantity"))),
                        "Unit Price": f"${safe_num(current_line_value(ln, 'price', item.get('unit_price')), 0):,.2f}",
                        "Subtotal": f"${subtotal:,.2f}",
                        "Line Total": f"${line_total:,.2f}",
                        "GST": f"${safe_num(current_line_value(ln, 'gst', item.get('gst_amount')), 0):,.2f}" if item.get("gst_amount") is not None or st.session_state.get(f"item_{selected_invoice_id}_{ln}_gst") is not None else "",
                        "PST/QST": f"${safe_num(current_line_value(ln, 'pstqst', item.get('pst_amount') if item.get('pst_amount') is not None else item.get('qst_amount')), 0):,.2f}" if (item.get("pst_amount") is not None or item.get("qst_amount") is not None or st.session_state.get(f"item_{selected_invoice_id}_{ln}_pstqst") is not None) else "",
                        "Combined Tax": f"${safe_num(current_line_value(ln, 'combined', item.get('combined_tax')), 0):,.2f}" if item.get("combined_tax") is not None or st.session_state.get(f"item_{selected_invoice_id}_{ln}_combined") is not None else "",
                        "Confidence": format_confidence(item.get("confidence", 0.0))
                    })
                
                st.dataframe(items_data, use_container_width=True)
                
                # Detailed view
                st.markdown("#### Detailed View")
                for item in line_items:
                    ln = item.get("line_number")
                    line_total, subtotal = compute_display_values(item)
                    with st.expander(f"Line {ln}: {item.get('description', '')[:50]}"):
                        delete_key = f"item_{selected_invoice_id}_{ln}_delete"
                        delete_flag = st.checkbox("Delete (X)", key=delete_key, value=bool(st.session_state.get(delete_key, False)))
                        if delete_flag:
                            st.warning("Marked for deletion; will be removed on save/submit.")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.text_input("Description", value=item.get("description", ""), key=f"item_{selected_invoice_id}_{ln}_desc")
                            st.number_input("Quantity", value=safe_num(item.get("quantity"), 0.0), key=f"item_{selected_invoice_id}_{ln}_qty")
                            st.number_input("GST", value=safe_num(item.get("gst_amount"), 0.0), format="%.2f", key=f"item_{selected_invoice_id}_{ln}_gst")
                            st.number_input(
                                "PST/QST",
                                value=safe_num(
                                    item.get("pst_amount") if item.get("pst_amount") is not None else item.get("qst_amount"),
                                    0.0,
                                ),
                                format="%.2f",
                                key=f"item_{selected_invoice_id}_{ln}_pstqst",
                            )

                        with col2:
                            st.number_input("Unit Price", value=safe_num(item.get("unit_price"), 0.0), format="%.2f", key=f"item_{selected_invoice_id}_{ln}_price")
                            st.number_input("Combined Tax", value=safe_num(item.get("combined_tax"), 0.0), format="%.2f", key=f"item_{selected_invoice_id}_{ln}_combined")
                            st.number_input("Line Total", value=safe_num(line_total, 0.0), format="%.2f", key=f"item_{selected_invoice_id}_{ln}_amount")
                            st.number_input("Subtotal", value=safe_num(subtotal, 0.0), format="%.2f", key=f"item_{selected_invoice_id}_{ln}_subtotal")
                            conf = item.get("confidence", 0.0)
                            conf_class = get_confidence_color(conf)
                            st.markdown(f'<span class="{conf_class}">{get_confidence_icon(conf)} Confidence: {format_confidence(conf)}</span>', 
                                      unsafe_allow_html=True)
            else:
                st.info("No line items found.")
    
        # Tab 4: Addresses
        with tab4:
            addresses = st.session_state.get("edited_addresses", {})
            if addresses:
                st.subheader("Addresses")
                for addr_type, addr_data in addresses.items():
                    st.markdown(f"**{addr_type.replace('_', ' ').title()}:**")
                    addr_val = (addr_data or {}).get("value") or {}
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.text_input("Street", value=addr_val.get("street", "") or "", key=f"{selected_invoice_id}_{addr_type}_street")
                        st.text_input("City", value=addr_val.get("city", "") or "", key=f"{selected_invoice_id}_{addr_type}_city")
                        st.text_input("Province", value=addr_val.get("province", "") or "", key=f"{selected_invoice_id}_{addr_type}_province")
                    with col_b:
                        st.text_input("Postal Code", value=addr_val.get("postal_code", "") or "", key=f"{selected_invoice_id}_{addr_type}_postal_code")
                        st.text_input("Country", value=addr_val.get("country", "") or "", key=f"{selected_invoice_id}_{addr_type}_country")
                        conf = addr_data.get("confidence", 0.0)
                        st.markdown(
                            f'<span class="{get_confidence_color(conf)}">{get_confidence_icon(conf)} {format_confidence(conf)}</span>',
                            unsafe_allow_html=True,
                        )
            else:
                st.info("No addresses available.")
    
        # Tab 5: Validation
        with tab5:
            with tab5:
                st.subheader("Submit Validation")
                
                reviewer_name = st.text_input("Reviewer Name", value="", placeholder="Enter your name", key="reviewer_name")
                
                validation_status = st.selectbox(
                    "Validation Status",
                    ["pending", "validated", "needs_review"],
                    index=0,
                    key="validation_status"
                )
                
                validation_notes = st.text_area(
                    "Validation Notes",
                    placeholder="Add any notes or comments about this validation...",
                    key="validation_notes"
                )

                def _build_validation_payload():
                    field_validations = []
                    line_item_validations = []

                    # Header/vendor/customer/financial fields diff
                    fields_data = invoice_data.get("fields", {}) or {}
                    tax_breakdown = invoice_data.get("tax_breakdown", {}) or {}
                    header_fields = ["invoice_number", "invoice_date", "due_date", "po_number", "standing_offer_number"]
                    vendor_fields = ["vendor_name", "vendor_id", "vendor_phone"]
                    customer_fields = ["customer_name", "customer_id"]
                    financial_fields = [
                        "subtotal",
                        "tax_amount",
                        "total_amount",
                        "currency",
                        "payment_terms",
                        "acceptance_percentage",
                        "tax_registration_number",
                        "federal_tax",
                        "provincial_tax",
                        "combined_tax",
                    ]
                    for fname in header_fields + vendor_fields + customer_fields + financial_fields:
                        field_data = fields_data.get(fname) or {"value": tax_breakdown.get(fname), "confidence": 0.0}
                        orig_val = field_data.get("value")
                        new_val = st.session_state.get(f"field_{selected_invoice_id}_{fname}")
                        if new_val is not None and str(new_val) != str(orig_val or ""):
                            field_validations.append({
                                "field_name": fname,
                                "value": orig_val,
                                # Manual correction => treat as confident
                                "confidence": 1.0,
                                "validated": True,
                                "corrected_value": new_val,
                                "validation_notes": "",
                            })

                    # Addresses
                    edited_addresses = st.session_state.get("edited_addresses", {})
                    for addr_key, addr_data in edited_addresses.items():
                        value = {
                            "street": st.session_state.get(f"{selected_invoice_id}_{addr_key}_street") or "",
                            "city": st.session_state.get(f"{selected_invoice_id}_{addr_key}_city") or "",
                            "province": st.session_state.get(f"{selected_invoice_id}_{addr_key}_province") or "",
                            "postal_code": st.session_state.get(f"{selected_invoice_id}_{addr_key}_postal_code") or "",
                            "country": st.session_state.get(f"{selected_invoice_id}_{addr_key}_country") or "",
                        }
                        field_validations.append({
                            "field_name": addr_key,
                            "value": None,
                            "confidence": 1.0,
                            "validated": True,
                            "corrected_value": value,
                            "validation_notes": ""
                        })

                    # Line items
                    original_items = {li.get("line_number"): li for li in invoice_data.get("line_items", [])}
                    for item in st.session_state.get("edited_line_items", []):
                        ln = item.get("line_number")
                        orig = original_items.get(ln, {}) or {}
                        corrections = {}
                        delete_flag = st.session_state.get(f"item_{selected_invoice_id}_{ln}_delete", False)

                        def _safe_float(val):
                            try:
                                return float(val)
                            except Exception:
                                return None

                        qty_val = st.session_state.get(f"item_{selected_invoice_id}_{ln}_qty", item.get("quantity"))
                        price_val = st.session_state.get(f"item_{selected_invoice_id}_{ln}_price", item.get("unit_price"))
                        gst_val = st.session_state.get(f"item_{selected_invoice_id}_{ln}_gst", item.get("gst_amount"))
                        pstqst_val = st.session_state.get(f"item_{selected_invoice_id}_{ln}_pstqst", item.get("pst_amount") if item.get("pst_amount") is not None else item.get("qst_amount"))
                        combined_val = st.session_state.get(f"item_{selected_invoice_id}_{ln}_combined", item.get("combined_tax"))
                        tax_amount_val = st.session_state.get(f"item_{selected_invoice_id}_{ln}_tax_amount", item.get("tax_amount"))
                        amount_val = st.session_state.get(f"item_{selected_invoice_id}_{ln}_amount", item.get("amount"))
                        desc_val = st.session_state.get(f"item_{selected_invoice_id}_{ln}_desc", item.get("description") or "") or ""

                        numeric_values = [
                            _safe_float(qty_val),
                            _safe_float(price_val),
                            _safe_float(gst_val),
                            _safe_float(pstqst_val),
                            _safe_float(combined_val),
                            _safe_float(tax_amount_val),
                            _safe_float(amount_val),
                        ]
                        all_zero_numeric = all(v in (None, 0.0) for v in numeric_values)
                        should_delete = delete_flag or (all_zero_numeric and desc_val.strip() == "")
                        if should_delete:
                            line_item_validations.append({
                                "line_number": ln,
                                "validated": True,
                                "corrections": {"delete": True},
                                "validation_notes": ""
                            })
                            continue

                        def maybe_add(key_short: str, canon_key: str):
                            new_val = st.session_state.get(f"item_{selected_invoice_id}_{ln}_{key_short}")
                            old_val = orig.get(canon_key)
                            if new_val is not None and new_val != old_val:
                                corrections[canon_key] = new_val

                        # text
                        desc_new = st.session_state.get(f"item_{selected_invoice_id}_{ln}_desc")
                        if desc_new is not None and desc_new != orig.get("description"):
                            corrections["description"] = desc_new

                        # numerics
                        maybe_add("qty", "quantity")
                        maybe_add("price", "unit_price")
                        maybe_add("gst", "gst_amount")
                        # PST/QST combined input (store as pst_amount only)
                        pstqst_val = st.session_state.get(f"item_{selected_invoice_id}_{ln}_pstqst")
                        if pstqst_val is not None and pstqst_val != orig.get("pst_amount"):
                            corrections["pst_amount"] = pstqst_val
                            # clear qst_amount if present
                            corrections["qst_amount"] = None
                        maybe_add("combined", "combined_tax")

                        # derive line_total (amount) for submission if changed
                        line_total_val = st.session_state.get(f"item_{selected_invoice_id}_{ln}_amount")
                        subtotal_input = st.session_state.get(f"item_{selected_invoice_id}_{ln}_subtotal")
                        if line_total_val is None:
                            qty_val = st.session_state.get(f"item_{selected_invoice_id}_{ln}_qty")
                            price_val = st.session_state.get(f"item_{selected_invoice_id}_{ln}_price")
                            try:
                                if qty_val is not None and price_val is not None:
                                    line_total_val = float(qty_val) * float(price_val)
                            except Exception:
                                line_total_val = None
                        # if user edited subtotal, back-calc line total using taxes
                        if line_total_val is None and subtotal_input is not None:
                            try:
                                base = float(subtotal_input)
                                tax_components = []
                                for key in [
                                    f"item_{selected_invoice_id}_{ln}_tax_amount",
                                    f"item_{selected_invoice_id}_{ln}_combined",
                                    f"item_{selected_invoice_id}_{ln}_gst",
                                    f"item_{selected_invoice_id}_{ln}_pstqst",
                                ]:
                                    val = st.session_state.get(key)
                                    if val not in [None, ""]:
                                        tax_components.append(float(val))
                                if tax_components:
                                    line_total_val = base + sum(tax_components)
                                else:
                                    line_total_val = base
                            except Exception:
                                line_total_val = None
                        if line_total_val is not None and line_total_val != orig.get("amount"):
                            corrections["amount"] = line_total_val

                        if corrections:
                            line_item_validations.append({
                                "line_number": ln,
                                "validated": True,
                                "corrections": corrections,
                                "validation_notes": ""
                            })

                    return field_validations, line_item_validations

                def _persist_changes(status_value: str, reviewer_value: str, notes_value: str):
                    if not reviewer_value:
                        st.warning("Please enter your name as reviewer.")
                        return False
                    field_validations, line_item_validations = _build_validation_payload()
                    # Get current review_version from session state (updated on load)
                    expected_version = st.session_state.get("invoice_review_version", {}).get(
                        selected_invoice_id, 
                        invoice_data.get("review_version", 0)
                    )
                    payload = {
                        "invoice_id": selected_invoice_id,
                        "expected_review_version": int(expected_version),
                        "field_validations": field_validations,
                        "line_item_validations": line_item_validations,
                        "overall_validation_status": status_value,
                        "reviewer": reviewer_value,
                        "validation_notes": notes_value,
                    }
                    # DEBUG: Log payload to verify expected_review_version is included
                    st.write(f"DEBUG: Sending expected_review_version={payload['expected_review_version']}")
                    success, error_detail = _post_validation_payload(payload)
                    
                    if success:
                        # Success: reload normally
                        st.cache_data.clear()
                        st.success("Changes saved to database.")
                        updated_invoice = load_invoice(selected_invoice_id)
                        if updated_invoice:
                            reset_invoice_state(selected_invoice_id, updated_invoice)
                        st.rerun()
                    elif error_detail and error_detail.get("error_code") == "STALE_WRITE":
                        # 409 Conflict: auto-reload invoice with latest version
                        st.error(
                            f"**Concurrent Edit Detected**: {error_detail.get('message', 'Invoice was updated by someone else.')}"
                        )
                        st.warning(
                            f"**Reloading latest version** (version {error_detail.get('current_review_version', 'unknown')}).\n\n"
                            f"Please review the changes made by the other user and re-apply your edits if still needed."
                        )
                        
                        # Clear cache and reload invoice
                        st.cache_data.clear()
                        updated_invoice = load_invoice(selected_invoice_id)
                        if updated_invoice:
                            reset_invoice_state(selected_invoice_id, updated_invoice)
                            # review_version already updated by load_invoice()
                        
                        # Trigger rerun to refresh UI with new data
                        st.rerun()
                    else:
                        # Network/other error: queue for retry
                        st.warning("Save failed; queued locally. Retry when DB is reachable.")
                        _enqueue_pending(payload)
                    
                    return success

                # Primary submit
                submitted = st.form_submit_button("Submit Validation", type="primary")
                if submitted:
                    _persist_changes(
                        st.session_state.get("validation_status", "pending"),
                        st.session_state.get("reviewer_name", ""),
                        st.session_state.get("validation_notes", ""),
                    )

        # Explicit save button outside the form to persist edits without re-filling the form
        st.markdown("---")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Save Changes (persist to DB)", type="primary"):
                _persist_changes(
                    st.session_state.get("validation_status", "pending"),
                    st.session_state.get("reviewer_name", ""),
                    st.session_state.get("validation_notes", ""),
                )
        
        with col2:
            # Show reload button if there was a conflict
            if st.session_state.get("last_conflict"):
                if st.button("🔄 Reload Invoice (Get Latest)", type="secondary"):
                    # Clear conflict and reload
                    st.session_state.pop("last_conflict", None)
                    st.cache_data.clear()
                    updated_invoice = load_invoice(selected_invoice_id)
                    if updated_invoice:
                        reset_invoice_state(selected_invoice_id, updated_invoice)
                    st.success("Invoice reloaded with latest changes.")
                    st.rerun()

        # Review history
        st.markdown("---")
        st.markdown("#### Review History")
        history = st.session_state.get("validation_history") or []
        if history:
            for entry in reversed(history):
                st.info(
                    f"**Status:** {entry.get('status')} | "
                    f"**Reviewer:** {entry.get('reviewer')} | "
                    f"**When:** {entry.get('timestamp')} \n\n"
                    f"**Notes:** {entry.get('notes') or 'None'}"
                )
        else:
            st.info("No review history available.")

        # Queued saves (offline/fallback)
        st.markdown("---")
        st.markdown("#### Queued Saves (offline fallback)")
        pending = st.session_state.get("pending_validations", [])
        st.markdown(f"Queued items: **{len(pending)}**")
        if pending:
            if st.button("Retry queued saves now"):
                _retry_pending_queue()
            with st.expander("View queued payloads"):
                for idx, item in enumerate(pending, start=1):
                    st.json({"idx": idx, **item})

    # Re-run extraction outside the form
    st.markdown("#### Re-run Extraction (DI + LLM Assist)")
    st.caption("Runs Document Intelligence and the LLM fallback for low-confidence fields.")
    if st.button("Re-run Extraction with AI Assist"):
        try:
            file_path = invoice_data.get("file_path")
            file_name = invoice_data.get("file_name", "invoice.pdf")
            invoice_id = invoice_data.get("invoice_id")

            if not file_path or not invoice_id:
                st.error("Missing file path or invoice id; cannot re-run extraction.")
            else:
                resp = requests.post(
                    f"{API_BASE_URL}/api/hitl/invoice/{invoice_id}/reextract",
                    timeout=180,
                )
                if resp.status_code == 200:
                    st.success("Extraction re-run completed. Refreshing...")

                    # Re-load invoice data and reset edit state
                    new_invoice = load_invoice(invoice_id)
                    if new_invoice:
                        reset_invoice_state(invoice_id, new_invoice)

                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Re-extraction failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            st.error(f"Error re-running extraction: {e}")


if __name__ == "__main__":
    main()

