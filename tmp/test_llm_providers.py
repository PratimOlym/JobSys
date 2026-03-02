import os
import sys
import logging
import json

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from shared import config, llm_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_providers():
    providers = ["gemini", "openai", "huggingface"]
    results = {}
    
    for provider in providers:
        print(f"\n--- Testing Provider: {provider} ---")
        os.environ["LLM_PROVIDER"] = provider
        # Force rebuild of provider singleton
        llm_client._provider = None 
        
        try:
            # Simple test case: summarize a minimal resume
            test_resume = "John Doe\nSoftware Engineer\n5 years of Python experience."
            summary = llm_client.summarize_resume("test_resume.txt", test_resume)
            
            if "Summary generation failed" in summary.get("headline", ""):
                print(f"FAILED: {summary.get('summary_text', 'Unknown error')}")
                results[provider] = {"status": "FAILED", "error": summary.get("summary_text")}
            else:
                print("SUCCESS")
                results[provider] = {"status": "SUCCESS"}
        except Exception as e:
            print(f"ERROR: {str(e)}")
            results[provider] = {"status": "ERROR", "error": str(e)}
            
    return results

if __name__ == "__main__":
    test_results = test_providers()
    print("\n--- Final Results ---")
    print(json.dumps(test_results, indent=2))
