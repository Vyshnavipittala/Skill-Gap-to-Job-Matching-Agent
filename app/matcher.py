import json
import numpy as np
from sentence_transformers import SentenceTransformer
from app.config import (
    JOBS_FILE,
    EMBEDDING_MODEL_NAME,
    SIMILARITY_THRESHOLD,
    PARTIAL_THRESHOLD,
    REQUIRED_WEIGHT,
    NICE_TO_HAVE_WEIGHT
)

_model = None
_embedding_cache = {}

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model

def load_jobs(jobs_path=JOBS_FILE):
    with open(jobs_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_embeddings(skills_list):
    if not skills_list:
        return np.empty((0, 384))

    model = get_model()
    needed = [s for s in skills_list if s not in _embedding_cache]
    if needed:
        encoded = model.encode(needed, convert_to_numpy=True, normalize_embeddings=True)
        for skill, emb in zip(needed, encoded):
            _embedding_cache[skill] = emb

    return np.array([_embedding_cache[s] for s in skills_list])

def compute_similarity_matrix(user_skills, job_skills):
    if not user_skills or not job_skills:
        return np.zeros((len(user_skills), len(job_skills)))

    user_embs = get_embeddings(user_skills)
    job_embs = get_embeddings(job_skills)
    return np.dot(user_embs, job_embs.T)

def evaluate_skills_match(user_skills, target_skills, sim_threshold=SIMILARITY_THRESHOLD, partial_threshold=PARTIAL_THRESHOLD):
    if not target_skills:
        return [], [], []

    if not user_skills:
        return [], [], list(target_skills)

    sim_matrix = compute_similarity_matrix(user_skills, target_skills)
    max_sims = np.max(sim_matrix, axis=0)

    matched = []
    partial = []
    missing = []

    for skill, sim in zip(target_skills, max_sims):
        if sim >= sim_threshold:
            matched.append(skill)
        elif sim >= partial_threshold:
            partial.append(skill)
        else:
            missing.append(skill)

    return matched, partial, missing

def calculate_job_score(user_skills, job, sim_threshold=SIMILARITY_THRESHOLD, partial_threshold=PARTIAL_THRESHOLD):
    req_skills = job.get("required_skills", [])
    nice_skills = job.get("nice_to_have_skills", [])

    matched_req, partial_req, missing_req = evaluate_skills_match(
        user_skills, req_skills, sim_threshold, partial_threshold
    )
    matched_nice, partial_nice, missing_nice = evaluate_skills_match(
        user_skills, nice_skills, sim_threshold, partial_threshold
    )

    if req_skills:
        req_score = (len(matched_req) / len(req_skills)) * (REQUIRED_WEIGHT * 100)
    else:
        req_score = REQUIRED_WEIGHT * 100

    if nice_skills:
        nice_score = (len(matched_nice) / len(nice_skills)) * (NICE_TO_HAVE_WEIGHT * 100)
    else:
        nice_score = NICE_TO_HAVE_WEIGHT * 100

    total_score = round(req_score + nice_score, 1)
    total_score = max(0.0, min(100.0, total_score))

    return {
        "job_id": job.get("id"),
        "title": job.get("title"),
        "company": job.get("company"),
        "city": job.get("city"),
        "education": job.get("education"),
        "experience_level": job.get("experience_level"),
        "match_score": total_score,
        "matched_required": matched_req,
        "partial_required": partial_req,
        "missing_required": missing_req,
        "matched_nice": matched_nice,
        "partial_nice": partial_nice,
        "missing_nice": missing_nice,
        "all_matched": matched_req + matched_nice,
        "all_missing": missing_req + missing_nice,
        "all_partial": partial_req + partial_nice
    }

def match_jobs(user_skills, user_location="Any Location", top_n=10, jobs_path=JOBS_FILE):
    jobs = load_jobs(jobs_path)

    filtered_jobs = jobs
    if user_location and user_location.lower() not in ["any location", "any", "all"]:
        loc_clean = user_location.strip().lower()
        matched_loc_jobs = [j for j in jobs if j.get("city", "").strip().lower() == loc_clean]
        if matched_loc_jobs:
            filtered_jobs = matched_loc_jobs

    results = []
    for job in filtered_jobs:
        score_data = calculate_job_score(user_skills, job)
        results.append(score_data)

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:top_n]

