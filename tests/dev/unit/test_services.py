"""Test script to ping all services and verify configuration"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src.models.database import AsyncSessionLocal, engine
from sqlalchemy import text

async def test_sqlite_db():
    """Test SQLite database connection"""
    print("\n" + "="*60)
    print("TESTING SQLITE DATABASE")
    print("="*60)
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1 as test"))
            row = result.scalar()
            if row == 1:
                print("SQLite DB: Connected successfully")
                
                # Check if invoices table exists
                result = await session.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='invoices'
                """))
                table_exists = result.scalar()
                if table_exists:
                    # Count invoices
                    result = await session.execute(text("SELECT COUNT(*) FROM invoices"))
                    count = result.scalar()
                    print(f"   Table 'invoices' exists with {count} records")
                else:
                    print("   Table 'invoices' does not exist yet (will be created on first use)")
                return True
            else:
                print("SQLite DB: Connection test failed")
                return False
    except Exception as e:
        print(f"SQLite DB: Connection failed - {e}")
        return False

def test_document_intelligence():
    """Test Document Intelligence service"""
    print("\n" + "="*60)
    print("TESTING DOCUMENT INTELLIGENCE SERVICE")
    print("="*60)
    
    endpoint = settings.AZURE_FORM_RECOGNIZER_ENDPOINT
    key = settings.AZURE_FORM_RECOGNIZER_KEY
    model = settings.AZURE_FORM_RECOGNIZER_MODEL
    
    if not endpoint or not key:
        print("Document Intelligence: Missing configuration")
        print(f"   Endpoint: {'Set' if endpoint else 'NOT SET'}")
        print(f"   Key: {'Set' if key else 'NOT SET'}")
        return False
    
    print(f"Configuration found:")
    print(f"   Endpoint: {endpoint[:50]}...")
    print(f"   Key: {'*' * 4}...{key[-4:] if len(key) > 4 else '****'}")
    print(f"   Model: {model}")
    
    try:
        from azure.ai.formrecognizer import DocumentAnalysisClient
        from azure.core.credentials import AzureKeyCredential
        
        client = DocumentAnalysisClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )
        print("Document Intelligence: Client initialized successfully")
        
        # Try to get account info (this will verify the connection)
        # Note: There's no direct "ping" endpoint, but we can verify the client works
        print("   Service is ready (client initialized)")
        return True
    except Exception as e:
        print(f"Document Intelligence: Failed to initialize - {e}")
        return False

def test_llm():
    """Test Azure OpenAI LLM service"""
    print("\n" + "="*60)
    print("TESTING AZURE OPENAI LLM SERVICE")
    print("="*60)
    
    endpoint = settings.AOAI_ENDPOINT
    key = settings.AOAI_API_KEY
    deployment = settings.AOAI_DEPLOYMENT_NAME
    api_version = settings.AOAI_API_VERSION
    
    if not endpoint or not key or not deployment:
        print("Azure OpenAI: Missing configuration")
        print(f"   Endpoint: {'Set' if endpoint else 'NOT SET'}")
        print(f"   Key: {'Set' if key else 'NOT SET'}")
        print(f"   Deployment: {'Set' if deployment else 'NOT SET'}")
        print(f"   API Version: {api_version}")
        return False
    
    # Normalize endpoint
    endpoint = endpoint.rstrip('/')
    
    print(f"Configuration found:")
    print(f"   Endpoint: {endpoint}")
    print(f"   Key: {'*' * 4}...{key[-4:] if len(key) > 4 else '****'}")
    print(f"   Deployment: {deployment}")
    print(f"   API Version: {api_version}")
    
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            api_key=key,
            api_version=api_version,
            azure_endpoint=endpoint,
        )
        print("Azure OpenAI: Client initialized successfully")
        
        # Try a minimal completion to verify the deployment exists
        print(f"   Testing deployment '{deployment}'...")
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=5,
            timeout=10
        )
        
        if response.choices and response.choices[0].message:
            content = response.choices[0].message.content
            print(f"Azure OpenAI: Deployment '{deployment}' is accessible")
            print(f"   Test response: {content}")
            return True
        else:
            print(f"Azure OpenAI: Deployment '{deployment}' returned empty response")
            return False
            
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            error_msg = f"HTTP {e.response.status_code}: {error_msg}"
        if hasattr(e, 'response') and hasattr(e.response, 'url'):
            error_msg += f" (URL: {e.response.url})"
        print(f"Azure OpenAI: Failed to connect - {error_msg}")
        return False

def test_llm_fallback_setting():
    """Check LLM fallback setting"""
    print("\n" + "="*60)
    print("LLM FALLBACK CONFIGURATION")
    print("="*60)
    
    use_llm = bool(getattr(settings, "USE_LLM_FALLBACK", False))
    demo_mode = settings.DEMO_MODE
    
    print(f"   USE_LLM_FALLBACK: {use_llm}")
    print(f"   DEMO_MODE: {demo_mode}")
    
    if use_llm:
        print("LLM fallback is ENABLED")
    else:
        print("LLM fallback is DISABLED - only Document Intelligence will run")
    
    if demo_mode:
        print("DEMO_MODE is enabled - will use mock services if real ones aren't configured")

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("SERVICE HEALTH CHECK")
    print("="*60)
    
    results = {}
    
    # Test SQLite DB
    results['sqlite'] = await test_sqlite_db()
    
    # Test Document Intelligence
    results['di'] = test_document_intelligence()
    
    # Test LLM
    results['llm'] = test_llm()
    
    # Check LLM fallback setting
    test_llm_fallback_setting()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"SQLite DB: {'OK' if results['sqlite'] else 'FAILED'}")
    print(f"Document Intelligence: {'OK' if results['di'] else 'FAILED'}")
    print(f"Azure OpenAI LLM: {'OK' if results['llm'] else 'FAILED'}")
    
    if all(results.values()):
        print("\nAll services are ready!")
    else:
        print("\nSome services are not ready. Check the errors above.")
    
    return all(results.values())

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

