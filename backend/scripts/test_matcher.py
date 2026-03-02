
import sys
import os
import argparse
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared import config, storage
from resume_matcher.llm_matcher import match_resume_to_jd

def run_test(jd_path, limit=None):
    # 1. Load JD
    print(f"--- Loading JD from {jd_path} ---")
    if jd_path.startswith("s3://"):
        # Handle S3 path (bucket/key)
        parts = jd_path.replace("s3://", "").split("/")
        bucket = parts[0]
        key = "/".join(parts[1:])
        jd_text = storage.download_text(key)
    else:
        with open(jd_path, "r", encoding="utf-8") as f:
            jd_text = f.read()

    # 2. Get Base Resumes
    print("--- Loading Base Resumes and Summaries ---")
    summaries = storage.load_resume_summaries()
    summary_map = {s["resume_name"]: s for s in summaries}
    
    resume_keys = storage.list_base_resumes()
    if limit:
        resume_keys = resume_keys[:limit]

    # 3. Match
    print(f"Starting matching against {len(resume_keys)} resumes...")
    results = []
    
    # Simple meta for testing
    job_meta = {
        "job_title": "Test Role",
        "company": "Test Company",
        "location": "Remote"
    }

    for key in resume_keys:
        resume_name = key.split("/")[-1]
        print(f"Matching: {resume_name}...")
        
        # Try to use summary first for speed/cost if available
        if resume_name in summary_map:
            s = summary_map[resume_name]
            resume_text = f"Headline: {s.get('headline')}\nSkills: {', '.join(s.get('skills', []))}\nSummary: {s.get('summary_text')}"
            print(f"  (Using summary for {resume_name})")
        else:
            file_bytes = storage.download_file(key)
            # In a real test we'd need a parser, but let's assume summaries exist for now
            # or try to extract if it's text
            resume_text = file_bytes.decode("utf-8", errors="ignore")

        try:
            result = match_resume_to_jd(resume_name, resume_text, jd_text, job_meta)
            results.append(result)
            print(f"  Score: {result.overall_score}/100")
        except Exception as e:
            print(f"  Error matching {resume_name}: {e}")

    # 4. Sort and Display
    results.sort(key=lambda x: x.overall_score, reverse=True)
    
    print("\n" + "="*50)
    print("MATCHING RESULTS")
    print("="*50)
    for r in results:
        print(f"[{r.overall_score}] {r.resume_name}")
        print(f"   Scores: Keyword={r.keyword_score}, Semantic={r.semantic_score}")
        print(f"   Matched: {', '.join(r.matched_skills[:5])}...")
        print(f"   Missing: {', '.join(r.missing_skills[:5])}...")
        if r.recommendation:
            print(f"   Recommendation: {r.recommendation}")
        print("-" * 30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--jd", required=True, help="Path to JD file (local or s3://bucket/key)")
    parser.add_argument("--limit", type=int, help="Limit number of resumes to test")
    parser.add_argument("--provider", help="Force LLM provider (gemini, openai, huggingface)")
    args = parser.parse_args()
    
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider

    # Set AWS profile for the session if not set
    if not os.environ.get("AWS_PROFILE"):
        os.environ["AWS_PROFILE"] = "superclub-dev"
    if not os.environ.get("AWS_DEFAULT_REGION"):
        os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"

    run_test(args.jd, args.limit)
