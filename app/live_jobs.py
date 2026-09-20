import os
import re
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
ADZUNA_COUNTRY = "in"
ADZUNA_URL = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search"

# Broad set of titles across many fields, not limited to the sample
# dataset that shipped with this project earlier.
SEARCH_QUERIES = [
    "python developer",
    "react developer",
    "java developer",
    "data analyst",
    "data scientist",
    "data engineer",
    "devops engineer",
    "cloud engineer",
    "android developer",
    "ios developer",
    "machine learning engineer",
    "qa automation engineer",
    "ui ux designer",
    "business analyst",
    "product manager",
    "project manager",
    "mechanical engineer",
    "electrical engineer",
    "embedded systems engineer",
    "civil engineer",
    "supply chain analyst",
    "digital marketing executive",
    "network engineer",
    "cybersecurity analyst",
]

RESULTS_PER_QUERY = 20
MAX_PAGES_PER_QUERY = 2
LLM_CALL_DELAY_SECONDS = 4.2  # keep under free-tier rate limits


def get_gemini_client():
    try:
        from google import genai
    except ImportError:
        return None
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def clean_json_text(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def extract_job_facts_with_llm(client, model_name, title, description, company):
    prompt = f"""
You are reading one real, live job posting scraped from a job board. Extract facts
using ONLY what is stated or clearly implied in this specific posting's text below.
Do not invent skills that are not mentioned or clearly implied by the responsibilities
described. Do not use any external assumptions about what this job title "usually" needs.

Job title: {title}
Company: {company}
Full posting text:
\"\"\"{description}\"\"\"

Return valid JSON with these keys only:
- "required_skills": list of 3 to 8 short skill/tool/technology names explicitly needed for this role, based on this posting's text
- "nice_to_have_skills": list of 0 to 5 short skill names mentioned as a bonus/preferred, based on this posting's text
- "education": string, the qualification stated in the posting, or "Not specified by employer" if none is stated
- "experience_level": string, the experience range stated in the posting (e.g. "2-4 years"), or "Not specified" if none is stated

Return only the JSON object, nothing else.
"""
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
    )
    parsed = json.loads(clean_json_text(response.text))
    return {
        "required_skills": [str(s).strip() for s in parsed.get("required_skills", []) if str(s).strip()],
        "nice_to_have_skills": [str(s).strip() for s in parsed.get("nice_to_have_skills", []) if str(s).strip()],
        "education": str(parsed.get("education", "Not specified by employer")),
        "experience_level": str(parsed.get("experience_level", "Not specified")),
    }


def fetch_page(query, page, api_id, api_key):
    params = {
        "app_id": api_id,
        "app_key": api_key,
        "results_per_page": RESULTS_PER_QUERY,
        "what": query,
        "content-type": "application/json",
    }
    url = f"{ADZUNA_URL}/{page}"
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json().get("results", [])


def normalize_job(raw, index, client, model_name):
    title = raw.get("title", "").strip() or "Untitled Role"
    company = (raw.get("company") or {}).get("display_name", "Unknown Company")
    location = (raw.get("location") or {}).get("display_name", "India")
    description = raw.get("description", "")

    try:
        facts = extract_job_facts_with_llm(client, model_name, title, description, company)
    except Exception as exc:
        print(f"  LLM extraction failed for '{title}' at {company}: {exc}")
        return None

    if not facts["required_skills"]:
        return None

    return {
        "id": f"live_{index:03d}",
        "title": title,
        "company": company,
        "city": location.split(",")[0].strip(),
        "required_skills": facts["required_skills"],
        "nice_to_have_skills": facts["nice_to_have_skills"],
        "education": facts["education"],
        "experience_level": facts["experience_level"],
        "source_url": raw.get("redirect_url", ""),
        "source": "adzuna_live_llm_extracted",
    }


def fetch_live_jobs(app_id=None, app_key=None, progress_callback=None):
    from app.config import GEMINI_MODEL_NAME

    api_id = app_id or ADZUNA_APP_ID
    api_key = app_key or ADZUNA_APP_KEY
    if not api_id or not api_key:
        raise RuntimeError(
            "Missing Adzuna credentials. Set ADZUNA_APP_ID and ADZUNA_APP_KEY "
            "in your .env file (free keys at https://developer.adzuna.com)."
        )

    client = get_gemini_client()
    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY is missing or the google-genai package is not installed. "
            "Skill extraction for live jobs requires Gemini so that required/nice-to-have "
            "skills come from each posting's real text, not a hardcoded list."
        )

    raw_pool = []
    seen_titles_companies = set()

    for query in SEARCH_QUERIES:
        for page in range(1, MAX_PAGES_PER_QUERY + 1):
            try:
                raw_results = fetch_page(query, page, api_id, api_key)
            except requests.RequestException as exc:
                print(f"Skipping '{query}' page {page}: {exc}")
                continue
            for raw in raw_results:
                title = raw.get("title", "").strip()
                company = (raw.get("company") or {}).get("display_name", "")
                dedup_key = (title.lower(), company.lower())
                if dedup_key in seen_titles_companies or not title:
                    continue
                seen_titles_companies.add(dedup_key)
                raw_pool.append(raw)
            time.sleep(0.3)

    print(f"Found {len(raw_pool)} unique live postings. Extracting skills with Gemini "
          f"(about {LLM_CALL_DELAY_SECONDS:.0f}s per posting, this will take a while)...")

    jobs = []
    for i, raw in enumerate(raw_pool, 1):
        job = normalize_job(raw, i, client, GEMINI_MODEL_NAME)
        if job is not None:
            jobs.append(job)
        if progress_callback:
            progress_callback(i, len(raw_pool), len(jobs))
        else:
            print(f"  [{i}/{len(raw_pool)}] kept so far: {len(jobs)}")
        time.sleep(LLM_CALL_DELAY_SECONDS)

    return jobs


def save_jobs(jobs, jobs_path):
    with open(jobs_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
