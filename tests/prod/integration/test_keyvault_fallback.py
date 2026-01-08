"""Test Key Vault fallback mechanism"""

import logging
logging.basicConfig(level=logging.DEBUG)

print("="*60)
print("TESTING KEY VAULT FALLBACK")
print("="*60)

# Import settings - this will trigger Key Vault check
from src.config import settings

print("\nAzure OpenAI Configuration:")
print(f"  AOAI_ENDPOINT: {settings.AOAI_ENDPOINT[:50] if settings.AOAI_ENDPOINT else 'None'}...")
print(f"  AOAI_DEPLOYMENT_NAME: {settings.AOAI_DEPLOYMENT_NAME}")
print(f"  AOAI_API_KEY: {'SET' if settings.AOAI_API_KEY else 'NOT SET'}")

print("\nDocument Intelligence Configuration:")
print(f"  AZURE_FORM_RECOGNIZER_ENDPOINT: {settings.AZURE_FORM_RECOGNIZER_ENDPOINT[:50] if settings.AZURE_FORM_RECOGNIZER_ENDPOINT else 'None'}...")
print(f"  AZURE_FORM_RECOGNIZER_KEY: {'SET' if settings.AZURE_FORM_RECOGNIZER_KEY else 'NOT SET'}")

print("\nKey Vault Configuration:")
import os
kv_url = os.getenv("AZURE_KEY_VAULT_URL")
kv_name = os.getenv("AZURE_KEY_VAULT_NAME")
print(f"  AZURE_KEY_VAULT_URL: {kv_url or 'Not set'}")
print(f"  AZURE_KEY_VAULT_NAME: {kv_name or 'Not set (using default: kvdiofindataextractor)'}")

