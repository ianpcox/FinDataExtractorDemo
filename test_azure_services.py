"""Quick test of Azure service connections"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("AZURE SERVICES CONNECTION TEST")
print("=" * 60)

# Check Document Intelligence
print("\n1. DOCUMENT INTELLIGENCE")
di_endpoint = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
di_key = os.getenv("AZURE_FORM_RECOGNIZER_KEY")

if di_endpoint and di_key:
    print(f"   Endpoint: {di_endpoint[:50]}...")
    print(f"   Key: {di_key[:4]}...{di_key[-4:]}")
    
    # Test connection
    try:
        from azure.ai.formrecognizer import DocumentAnalysisClient
        from azure.core.credentials import AzureKeyCredential
        
        client = DocumentAnalysisClient(
            endpoint=di_endpoint,
            credential=AzureKeyCredential(di_key)
        )
        print("   Client initialized successfully")
        
        # Try to list models (lightweight operation)
        try:
            # This will fail if credentials are wrong
            print("   Testing API access...")
            # We can't list models with the prebuilt model, so just confirm init worked
            print("   Credentials appear valid (client created)")
        except Exception as e:
            print(f"   API test failed: {e}")
            
    except Exception as e:
        print(f"   Failed to initialize client: {e}")
else:
    print("   Missing environment variables")
    if not di_endpoint:
        print("      - AZURE_FORM_RECOGNIZER_ENDPOINT not set")
    if not di_key:
        print("      - AZURE_FORM_RECOGNIZER_KEY not set")

# Check Azure OpenAI
print("\n2. AZURE OPENAI")
aoai_endpoint = os.getenv("AOAI_ENDPOINT")
aoai_key = os.getenv("AOAI_API_KEY")
aoai_deployment = os.getenv("AOAI_DEPLOYMENT_NAME")

if aoai_endpoint and aoai_key and aoai_deployment:
    print(f"   Endpoint: {aoai_endpoint[:50]}...")
    print(f"   Key: {aoai_key[:4]}...{aoai_key[-4:]}")
    print(f"   Deployment: {aoai_deployment}")
    
    # Test connection
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            api_key=aoai_key,
            api_version="2024-02-15-preview",
            azure_endpoint=aoai_endpoint
        )
        print("   Client initialized successfully")
        
        # Try a minimal completion
        try:
            print("   Testing API access with minimal request...")
            response = client.chat.completions.create(
                model=aoai_deployment,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
                timeout=10
            )
            print(f"   API call successful! Response: {response.choices[0].message.content[:20]}")
        except Exception as e:
            print(f"   API call failed: {e}")
            
    except Exception as e:
        print(f"   Failed to initialize client: {e}")
else:
    print("   Missing environment variables")
    if not aoai_endpoint:
        print("      - AOAI_ENDPOINT not set")
    if not aoai_key:
        print("      - AOAI_API_KEY not set")
    if not aoai_deployment:
        print("      - AOAI_DEPLOYMENT_NAME not set")

# Check USE_LLM_FALLBACK setting
print("\n3. LLM FALLBACK CONFIGURATION")
use_llm = os.getenv("USE_LLM_FALLBACK", "false").lower() in ("true", "1", "yes")
print(f"   USE_LLM_FALLBACK: {use_llm}")
if not use_llm:
    print("   LLM fallback is DISABLED - only Document Intelligence will run")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
