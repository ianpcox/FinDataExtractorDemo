"""Fetch Azure Document Intelligence credentials from Key Vault and update .env"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv, set_key

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load existing .env
env_file = project_root / ".env"
load_dotenv(env_file)

print("="*70)
print("Fetch Azure Document Intelligence Credentials from Key Vault")
print("="*70)
print()

# Get Key Vault configuration
kv_name = os.getenv("AZURE_KEY_VAULT_NAME")
kv_url = os.getenv("AZURE_KEY_VAULT_URL")

# Try common Key Vault names if not set
if not kv_url and not kv_name:
    # Try to detect from common patterns
    common_names = [
        "kvdiofindataextractor",  # From .env file
        "kvdiofindataextractcace",
        "findataextractor-kv"
    ]
    print("[INFO] Key Vault not configured in .env, trying common names...")
    for name in common_names:
        kv_url = f"https://{name}.vault.azure.net/"
        print(f"  Trying: {kv_url}")
        # Will test connection below
        break

if not kv_url and kv_name:
    kv_url = f"https://{kv_name}.vault.azure.net/"

if not kv_url:
    print("[ERROR] Key Vault not configured")
    print("Please set AZURE_KEY_VAULT_NAME or AZURE_KEY_VAULT_URL in .env")
    print("Or update this script with your Key Vault name")
    sys.exit(1)

print(f"Key Vault URL: {kv_url}")
print()

try:
    from azure.keyvault.secrets import SecretClient
    from azure.identity import DefaultAzureCredential
    
    print("Connecting to Key Vault...")
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=kv_url, credential=credential)
    
    # Fetch Document Intelligence secrets
    secrets_to_fetch = {
        "document-intelligence-endpoint": "AZURE_FORM_RECOGNIZER_ENDPOINT",
        "document-intelligence-key": "AZURE_FORM_RECOGNIZER_KEY"
    }
    
    updated = False
    for secret_name, env_var_name in secrets_to_fetch.items():
        try:
            print(f"Fetching secret: {secret_name}...")
            secret = client.get_secret(secret_name)
            
            # Update .env file
            set_key(env_file, env_var_name, secret.value)
            print(f"[OK] Updated {env_var_name} in .env")
            updated = True
            
        except Exception as e:
            print(f"[WARN] Could not fetch {secret_name}: {e}")
    
    if updated:
        print()
        print("[SUCCESS] Credentials updated in .env file")
        print("You can now run the demo script or use Document Intelligence features")
    else:
        print()
        print("[ERROR] No credentials were updated")
        print("Please check:")
        print("  1. You're logged in to Azure CLI: az login")
        print("  2. You have access to the Key Vault")
        print("  3. The secrets exist in Key Vault:")
        for secret_name in secrets_to_fetch.keys():
            print(f"     - {secret_name}")
    
except ImportError:
    print("[ERROR] Azure Key Vault libraries not installed")
    print("Install with: pip install azure-keyvault-secrets azure-identity")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Failed to connect to Key Vault: {e}")
    print()
    print("Troubleshooting:")
    print("  1. Make sure you're logged in: az login")
    print("  2. Check you have access to the Key Vault")
    print("  3. Verify the Key Vault URL is correct")
    sys.exit(1)

