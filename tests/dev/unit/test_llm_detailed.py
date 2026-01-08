"""Detailed LLM connection test"""

import os
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("AOAI_ENDPOINT", "").rstrip('/')
key = os.getenv("AOAI_API_KEY", "")
deployment = os.getenv("AOAI_DEPLOYMENT_NAME", "")
api_version = os.getenv("AOAI_API_VERSION", "2024-11-20")

print("="*60)
print("DETAILED LLM CONNECTION TEST")
print("="*60)
print(f"Endpoint: {endpoint}")
print(f"Deployment: {deployment}")
print(f"API Version: {api_version}")
print(f"Key: {'SET' if key else 'NOT SET'} ({len(key) if key else 0} chars)")
print()

if not endpoint or not key or not deployment:
    print("Missing required configuration")
    exit(1)

try:
    from openai import AzureOpenAI
    
    client = AzureOpenAI(
        api_key=key,
        api_version=api_version,
        azure_endpoint=endpoint,
    )
    
    print("Client initialized successfully")
    print()
    
    # Show the exact URL that will be called
    test_url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    print(f"Test URL: {test_url}")
    print()
    
    # Try the request
    print("Attempting chat completion...")
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5,
            timeout=10
        )
        
        print("SUCCESS!")
        print(f"Response: {response.choices[0].message.content}")
        print(f"Model used: {response.model}")
        print(f"Finish reason: {response.choices[0].finish_reason}")
        
    except Exception as e:
        print(f"FAILED: {type(e).__name__}")
        print(f"Error: {e}")
        
        # Try to get more details
        if hasattr(e, 'response'):
            if hasattr(e.response, 'status_code'):
                print(f"HTTP Status: {e.response.status_code}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            if hasattr(e.response, 'url'):
                print(f"Request URL: {e.response.url}")
        
        print()
        print("Troubleshooting:")
        print("1. Verify the deployment name in Azure Portal:")
        print("   - Go to Azure Portal → Your OpenAI resource → Deployments")
        print("   - Check the exact deployment name (case-sensitive)")
        print("2. Verify the endpoint URL is correct")
        print("3. Check API version compatibility")
        print("4. Verify the API key has access to this resource")
        
except ImportError:
    print("ERROR: openai library not installed")
    print("Install with: pip install openai")
except Exception as e:
    print(f"ERROR: {e}")

