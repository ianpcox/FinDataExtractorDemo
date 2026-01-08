"""Fetch all Azure credentials from Key Vault"""

import os
from pathlib import Path
from dotenv import load_dotenv, set_key

# Load existing .env
env_file = Path(".env")
load_dotenv(env_file)

print("="*70)
print("FETCH ALL AZURE CREDENTIALS FROM KEY VAULT")
print("="*70)

# Get Key Vault URL
kv_url = "https://kvdiofindataextractor.vault.azure.net/"
print(f"\nKey Vault: {kv_url}")

try:
    from azure.keyvault.secrets import SecretClient
    from azure.identity import DefaultAzureCredential
    
    print("\n1. Connecting to Azure Key Vault...")
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=kv_url, credential=credential)
    print("   Connected successfully")
    
    # Map of Key Vault secret names to .env variable names
    secrets_map = {
        # Document Intelligence
        "document-intelligence-endpoint": "AZURE_FORM_RECOGNIZER_ENDPOINT",
        "document-intelligence-key": "AZURE_FORM_RECOGNIZER_KEY",
        
        # Azure OpenAI
        "aoai-endpoint": "AOAI_ENDPOINT",
        "aoai-api-key": "AOAI_API_KEY",
        "aoai-deployment-name": "AOAI_DEPLOYMENT_NAME",
        
        # Alternative names that might be used
        "azure-openai-endpoint": "AOAI_ENDPOINT",
        "azure-openai-key": "AOAI_API_KEY",
        "azure-openai-deployment": "AOAI_DEPLOYMENT_NAME",
    }
    
    print("\n2. Fetching secrets from Key Vault...")
    updated_count = 0
    for secret_name, env_var in secrets_map.items():
        try:
            secret = client.get_secret(secret_name)
            set_key(env_file, env_var, secret.value)
            print(f"   {env_var}: {secret.value[:10]}...{secret.value[-4:]}")
            updated_count += 1
        except Exception as e:
            if "not found" not in str(e).lower():
                print(f"   {secret_name}: {e}")
    
    if updated_count > 0:
        print(f"\nUpdated {updated_count} credentials in .env file")
        print("\nPlease restart the API server and Streamlit for changes to take effect:")
        print("  1. Stop current terminals (Ctrl+C)")
        print("  2. Restart API: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload")
        print("  3. Restart Streamlit: streamlit run streamlit_app.py --server.port 8501")
    else:
        print("\nNo credentials were updated")
        print("\nTroubleshooting:")
        print("  1. Verify you're logged in: az login")
        print("  2. Check your Azure role: az role assignment list --assignee <your-email>")
        print("  3. List available secrets: az keyvault secret list --vault-name kvdiofindataextractor")
        print("\nAlternatively, you can manually update .env with values from Azure Portal:")
        print("  - Document Intelligence: https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/FormRecognizer")
        print("  - Azure OpenAI: https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/OpenAI")
    
except ImportError:
    print("\nAzure libraries not installed")
    print("Install with: pip install azure-keyvault-secrets azure-identity")
except Exception as e:
    print(f"\nError: {e}")
    print("\nManual Update Instructions:")
    print("="*70)
    print("Go to Azure Portal and get the credentials:")
    print("\n1. Document Intelligence:")
    print("   Navigate to: https://portal.azure.com -> fr-dio-findataextractor-cace")
    print("   Get: Endpoint and Key")
    print("   Update in .env: AZURE_FORM_RECOGNIZER_ENDPOINT and AZURE_FORM_RECOGNIZER_KEY")
    print("\n2. Azure OpenAI:")
    print("   Navigate to: https://portal.azure.com -> aoai-dio-findataextract-east")
    print("   Get: Endpoint and Key")
    print("   Update in .env: AOAI_ENDPOINT and AOAI_API_KEY")
    print("   Check deployment name: AOAI_DEPLOYMENT_NAME (should be gpt-4 or similar)")
