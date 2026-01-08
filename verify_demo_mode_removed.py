"""Verify that DEMO_MODE no longer disables DI OCR or LLM"""

import re
from pathlib import Path

def check_file(file_path, patterns_to_find, patterns_to_avoid):
    """Check if file contains patterns we want and doesn't contain patterns we don't want"""
    content = Path(file_path).read_text(encoding='utf-8')
    
    found_good = []
    found_bad = []
    
    for pattern, description in patterns_to_find:
        if re.search(pattern, content, re.IGNORECASE):
            found_good.append(f"  [OK] {description}")
        else:
            found_good.append(f"  [MISSING] {description}")
    
    for pattern, description in patterns_to_avoid:
        if re.search(pattern, content, re.IGNORECASE):
            found_bad.append(f"  [ERROR] {description}")
    
    return found_good, found_bad

print("=" * 70)
print("Verifying DEMO_MODE Changes")
print("=" * 70)
print()

# Check document_intelligence_client.py
print("1. Checking src/extraction/document_intelligence_client.py...")
good_patterns = [
    (r'DocumentAnalysisClient', 'Uses real Document Intelligence client'),
]
bad_patterns = [
    (r'if.*DEMO_MODE.*MockDocumentIntelligenceClient', 'DEMO_MODE check for mock client'),
    (r'MockDocumentIntelligenceClient', 'Mock client import/usage'),
    (r'if.*settings\.DEMO_MODE.*analyze_invoice', 'DEMO_MODE check in analyze method'),
]

good, bad = check_file('src/extraction/document_intelligence_client.py', good_patterns, bad_patterns)
for item in good:
    print(item)
for item in bad:
    print(item)
print()

# Check extraction_service.py
print("2. Checking src/extraction/extraction_service.py...")
good_patterns = [
    (r'AsyncAzureOpenAI', 'Uses async Azure OpenAI client'),
    (r'await.*_run_low_confidence_fallback', 'Calls LLM fallback asynchronously'),
]
bad_patterns = [
    (r'if.*settings\.DEMO_MODE.*skip.*LLM', 'DEMO_MODE skips LLM'),
    (r'use_demo_llm', 'use_demo_llm variable'),
    (r'if.*use_demo_llm.*_run_mock_llm_fallback', 'Mock LLM fallback call (conditional)'),
    (r'if.*use_demo_llm', 'Conditional mock LLM usage'),
]

good, bad = check_file('src/extraction/extraction_service.py', good_patterns, bad_patterns)
for item in good:
    print(item)
for item in bad:
    print(item)
print()

# Summary
print("=" * 70)
if not any('[ERROR]' in item for item in bad):
    print("[SUCCESS] All DEMO_MODE checks that disable DI/LLM have been removed!")
    print("Real Document Intelligence and LLM will be used when configured.")
else:
    print("[WARNING] Some DEMO_MODE checks may still be present.")
print("=" * 70)

