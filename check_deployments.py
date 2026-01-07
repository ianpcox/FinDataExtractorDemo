"""Check available Azure OpenAI deployments"""

import os
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("AOAI_ENDPOINT", "").rstrip('/')
key = os.getenv("AOAI_API_KEY", "")
deployment = os.getenv("AOAI_DEPLOYMENT_NAME", "")
api_version = os.getenv("AOAI_API_VERSION", "2024-11-20")

print("="*60)
print("AZURE OPENAI DEPLOYMENT CHECK")
print("="*60)
print(f"Endpoint: {endpoint}")
print(f"Deployment (from .env): {deployment}")
print(f"API Version: {api_version}")
print()

if not endpoint or not key:
    print("Missing endpoint or key")
    exit(1)

try:
    from openai import AzureOpenAI
    
    client = AzureOpenAI(
        api_key=key,
        api_version=api_version,
        azure_endpoint=endpoint,
    )
    
    print("Attempting to list deployments...")
    try:
        # Try to list deployments (if supported)
        deployments = client.models.list()
        print("\nAvailable models/deployments:")
        for model in deployments:
            print(f"  - {model.id}")
    except Exception as e:
        print(f"Cannot list deployments: {e}")
        print("\nTrying alternative: Testing the configured deployment...")
        
        # Try the configured deployment
        try:
            response = client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": "Say OK"}],
                max_tokens=5,
                timeout=10
            )
            print(f"SUCCESS: Deployment '{deployment}' is accessible")
            print(f"Response: {response.choices[0].message.content}")
        except Exception as e2:
            print(f"FAILED: Deployment '{deployment}' is not accessible")
            print(f"Error: {e2}")
            print("\nPossible issues:")
            print("  1. Deployment name might be incorrect")
            print("  2. Deployment might not exist at this endpoint")
            print("  3. API version might be incompatible")
            print("  4. Endpoint URL might be incorrect")
            
except Exception as e:
    print(f"Error: {e}")

