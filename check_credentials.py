"""
Check credential status without exposing sensitive values
Run this to verify all required secrets are configured
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def mask_value(value):
    """Mask sensitive values showing only first/last few chars"""
    if not value:
        return "❌ NOT SET"
    if len(value) < 8:
        return "✓ SET (too short to mask)"
    return f"✓ SET ({value[:4]}...{value[-4:]})"

def check_credential(name, required=True):
    """Check if a credential is set"""
    value = os.getenv(name)
    status = "✓" if value else "❌"
    masked = mask_value(value)
    req_text = "REQUIRED" if required else "OPTIONAL"
    
    print(f"{status} {name:40} [{req_text:8}] {masked}")
    return bool(value)

print("=" * 80)
print("CREDENTIAL STATUS CHECK")
print("=" * 80)

print("\n🔐 AZURE DOCUMENT INTELLIGENCE (Required for extraction)")
print("-" * 80)
di_endpoint = check_credential("AZURE_FORM_RECOGNIZER_ENDPOINT", required=True)
di_key = check_credential("AZURE_FORM_RECOGNIZER_KEY", required=True)
di_model = check_credential("AZURE_FORM_RECOGNIZER_MODEL", required=False)

print("\n☁️  AZURE BLOB STORAGE (Optional - can use local storage)")
print("-" * 80)
storage_account = check_credential("AZURE_STORAGE_ACCOUNT_NAME", required=False)
storage_conn = check_credential("AZURE_STORAGE_CONNECTION_STRING", required=False)
check_credential("AZURE_STORAGE_CONTAINER_RAW", required=False)
check_credential("AZURE_STORAGE_CONTAINER_PROCESSED", required=False)

print("\n🤖 AZURE OPENAI (Optional - for LLM fallback)")
print("-" * 80)
use_llm = os.getenv("USE_LLM_FALLBACK", "False").lower() == "true"
print(f"   USE_LLM_FALLBACK: {use_llm}")
if use_llm:
    check_credential("AOAI_ENDPOINT", required=True)
    check_credential("AOAI_API_KEY", required=True)
    check_credential("AOAI_DEPLOYMENT_NAME", required=True)
    check_credential("AOAI_API_VERSION", required=False)
else:
    print("   (LLM fallback disabled - skipping AOAI credentials)")

print("\n💾 DATABASE")
print("-" * 80)
check_credential("DATABASE_URL", required=False)

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

# Check minimum requirements
can_extract = di_endpoint and di_key
can_use_azure_storage = storage_account and storage_conn
can_use_local_storage = True  # Always available

print(f"\n✓ Can extract invoices: {'YES ✅' if can_extract else 'NO ❌ (Missing DI credentials)'}")
print(f"✓ Can use Azure Storage: {'YES ✅' if can_use_azure_storage else 'NO (will use local storage)'}")
print(f"✓ Can use local storage: YES ✅")
print(f"✓ LLM fallback enabled: {'YES' if use_llm else 'NO'}")

print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)

if not can_extract:
    print("\n❌ CRITICAL: Document Intelligence credentials missing!")
    print("   → Set AZURE_FORM_RECOGNIZER_ENDPOINT and AZURE_FORM_RECOGNIZER_KEY")
    print("   → Without these, invoice extraction will fail")
    print("\n   To get credentials:")
    print("   1. Run: python scripts/fetch_credentials_from_keyvault.py")
    print("   2. Or manually copy from Azure Portal → Document Intelligence → Keys")
else:
    print("\n✅ All critical credentials configured!")
    print("   → You can extract invoices")
    
if not can_use_azure_storage:
    print("\n⚠️  Azure Storage not configured (using local storage)")
    print("   → This is OK for development/testing")
    print("   → Set AZURE_STORAGE_CONNECTION_STRING for Azure integration")

if use_llm and not (os.getenv("AOAI_ENDPOINT") and os.getenv("AOAI_API_KEY")):
    print("\n⚠️  LLM fallback enabled but AOAI credentials missing")
    print("   → Set USE_LLM_FALLBACK=False or configure AOAI credentials")

print("\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80)

if can_extract:
    print("\n✓ Ready to run operations!")
    print("  → Can run database migrations: alembic upgrade head")
    print("  → Can test extraction: pytest tests/unit/extraction/")
    print("  → Can start API: uvicorn api.main:app --reload")
    print("  → Can start HITL: streamlit run streamlit_app.py")
else:
    print("\n⚠️  Update credentials before running operations")
    print("  → Edit .env file with valid credentials")
    print("  → Or run: python scripts/fetch_credentials_from_keyvault.py")
    print("  → Then re-run this check: python check_credentials.py")

print("\n")
