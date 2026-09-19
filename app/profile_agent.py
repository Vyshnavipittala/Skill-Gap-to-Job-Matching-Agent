import io
import json
import pypdf
from app.config import TAXONOMY_FILE
from app.llm import extract_profile_with_llm, extract_profile_from_multimodal

def load_taxonomy(taxonomy_path=TAXONOMY_FILE):
    try:
        with open(taxonomy_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("synonyms", {})
    except Exception:
        return {}

def normalize_skills(skills, synonyms_map=None):
    if synonyms_map is None:
        synonyms_map = load_taxonomy()

    normalized = []
    seen = set()

    for skill in skills:
        cleaned = skill.strip()
        if not cleaned:
            continue
        lookup_key = cleaned.lower()
        canonical = synonyms_map.get(lookup_key, cleaned)
        canonical_key = canonical.lower()
        if canonical_key not in seen:
            seen.add(canonical_key)
            normalized.append(canonical)

    return normalized

def extract_text_from_file(file_bytes, file_name):
    if not file_bytes:
        return ""
    name_lower = file_name.lower() if file_name else ""
    if name_lower.endswith(".pdf"):
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            return "\n".join(pages_text)
        except Exception:
            return ""
    else:
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="ignore")

def parse_profile(raw_text="", file_bytes=None, file_name=None, override_location=None, override_interests=None, audio_bytes=None, audio_mime_type="audio/wav", image_bytes=None, image_mime_type="image/jpeg"):
    combined_text = raw_text or ""
    if file_bytes:
        extracted = extract_text_from_file(file_bytes, file_name)
        if extracted:
            combined_text = f"{combined_text}\n{extracted}".strip()

    if audio_bytes:
        profile = extract_profile_from_multimodal(audio_bytes, audio_mime_type, text_context=combined_text)
    elif image_bytes:
        profile = extract_profile_from_multimodal(image_bytes, image_mime_type, text_context=combined_text)
    else:
        profile = extract_profile_with_llm(combined_text)

    synonyms_map = load_taxonomy()
    profile["skills"] = normalize_skills(profile.get("skills", []), synonyms_map)

    if override_location:
        profile["location"] = override_location

    if override_interests:
        if isinstance(override_interests, list):
            profile["interests"] = override_interests
        elif isinstance(override_interests, str) and override_interests.strip():
            profile["interests"] = [i.strip() for i in override_interests.split(",") if i.strip()]

    return profile
