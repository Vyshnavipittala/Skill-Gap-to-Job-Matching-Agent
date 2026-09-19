import os
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types
from app.config import GEMINI_MODEL_NAME

load_dotenv()

def get_gemini_client():
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

def fallback_extract_profile(raw_text):
    text_lower = raw_text.lower()
    from app.config import TAXONOMY_FILE
    synonyms = {}
    try:
        with open(TAXONOMY_FILE, "r", encoding="utf-8") as f:
            synonyms = json.load(f).get("synonyms", {})
    except Exception:
        pass

    extracted_skills = []
    seen = set()
    for phrase, canonical in synonyms.items():
        pattern = r"\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, text_lower):
            can_lower = canonical.lower()
            if can_lower not in seen:
                seen.add(can_lower)
                extracted_skills.append(canonical)

    exp_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+|-\d+)?\s*(?:years|yrs)", text_lower)
    exp = float(exp_match.group(1)) if exp_match else 0.0

    cities = ["Bengaluru", "Hyderabad", "Pune", "Mumbai", "Chennai", "Delhi NCR", "Delhi", "Noida", "Gurugram"]
    user_city = "Any Location"
    for city in cities:
        if city.lower() in text_lower:
            user_city = city
            break

    name = "Candidate"
    lines = [line.strip() for line in raw_text.strip().split("\n") if line.strip()]
    if lines:
        first_line = lines[0]
        comma_part = first_line.split(",")[0].strip()
        if len(comma_part.split()) <= 4 and not any(char.isdigit() for char in comma_part):
            name = comma_part

    education = "Bachelor's Degree"
    if "m.tech" in text_lower or "master" in text_lower or "ms " in text_lower:
        education = "Master's Degree"
    elif "b.tech" in text_lower or "bachelor" in text_lower or "b.e" in text_lower:
        education = "B.Tech / B.E."
    elif "diploma" in text_lower:
        education = "Diploma"

    return {
        "name": name,
        "education": education,
        "skills": extracted_skills,
        "years_of_experience": exp,
        "location": user_city,
        "interests": []
    }

def extract_profile_with_llm(raw_text):
    client = get_gemini_client()
    if not client:
        return fallback_extract_profile(raw_text)

    prompt = f"""
Extract candidate information from the following text into valid JSON format.
Keys required:
- "name": string (candidate name or "Candidate")
- "education": string (highest qualification or degree)
- "skills": list of strings (all technical and functional skills mentioned)
- "years_of_experience": number (total years of experience as float/int)
- "location": string (city name or "Any Location")
- "interests": list of strings (career or technical interests)

Candidate text:
{raw_text}

Return only valid JSON.
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        parsed = json.loads(clean_json_text(response.text))
        return {
            "name": str(parsed.get("name", "Candidate")),
            "education": str(parsed.get("education", "Not specified")),
            "skills": [str(s) for s in parsed.get("skills", [])],
            "years_of_experience": float(parsed.get("years_of_experience", 0)),
            "location": str(parsed.get("location", "Any Location")),
            "interests": [str(i) for i in parsed.get("interests", [])]
        }
    except Exception:
        return fallback_extract_profile(raw_text)

def extract_profile_from_multimodal(media_bytes, mime_type, text_context=""):
    client = get_gemini_client()
    if not client:
        if text_context:
            return fallback_extract_profile(text_context)
        return {
            "name": "Candidate",
            "education": "Not specified",
            "skills": [],
            "years_of_experience": 0.0,
            "location": "Any Location",
            "interests": []
        }

    part = types.Part.from_bytes(
        data=media_bytes,
        mime_type=mime_type
    )

    prompt = f"""
Carefully inspect the provided audio or image media (such as a spoken resume intro, an audio recording, a scanned resume, or certificate).
Extract candidate profile details into valid JSON.
Keys required:
- "name": string (candidate name or "Candidate")
- "education": string (highest qualification or degree)
- "skills": list of strings (all technical and functional skills mentioned or shown)
- "years_of_experience": number (total years of experience as float or int)
- "location": string (city name or "Any Location")
- "interests": list of strings (career or technical interests)

Additional text context: {text_context}

Return only valid JSON.
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=[part, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        parsed = json.loads(clean_json_text(response.text))
        return {
            "name": str(parsed.get("name", "Candidate")),
            "education": str(parsed.get("education", "Not specified")),
            "skills": [str(s) for s in parsed.get("skills", [])],
            "years_of_experience": float(parsed.get("years_of_experience", 0)),
            "location": str(parsed.get("location", "Any Location")),
            "interests": [str(i) for i in parsed.get("interests", [])]
        }
    except Exception:
        if text_context:
            return fallback_extract_profile(text_context)
        return {
            "name": "Candidate",
            "education": "Not specified",
            "skills": [],
            "years_of_experience": 0.0,
            "location": "Any Location",
            "interests": []
        }


def generate_gap_explanation(job_title, company, matched_skills, missing_skills, partial_skills):
    client = get_gemini_client()
    matched_str = ", ".join(matched_skills) if matched_skills else "None"
    missing_str = ", ".join(missing_skills) if missing_skills else "None"
    partial_str = ", ".join(partial_skills) if partial_skills else "None"

    if not client:
        if missing_skills:
            return f"The candidate matches {matched_str} for the {job_title} role at {company}. However, required skills such as {missing_str} are missing, while {partial_str} are partially aligned. Closing these missing skills will significantly improve match suitability."
        else:
            return f"The candidate is a strong fit for the {job_title} role at {company}, matching key requirements including {matched_str}."

    prompt = f"""
Write a short, professional, specific 2 to 3 sentence explanation of the candidate's skill gaps for the following job.
Role: {job_title} at {company}
Fully Matched Skills: {matched_str}
Missing Required Skills: {missing_str}
Partially Matched Skills: {partial_str}

Rules:
1. Rely ONLY on the skills provided above. Do NOT invent skills, experience, or facts.
2. Keep it to exactly 2 or 3 sentences.
3. Keep the tone constructive and professional.
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt
        )
        return response.text.strip()
    except Exception:
        return f"The candidate matches {matched_str} for the {job_title} role at {company}, but is missing {missing_str}. Focusing on {missing_str} will close the critical gaps for this role."
