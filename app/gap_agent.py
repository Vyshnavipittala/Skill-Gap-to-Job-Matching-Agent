from app.llm import generate_gap_explanation

def analyze_job_gaps(top_jobs, user_skills):
    job_gaps = []
    all_missing_skills = []
    seen_missing = set()

    for job in top_jobs:
        job_title = job.get("title", "Role")
        company = job.get("company", "Company")
        matched_req = job.get("matched_required", [])
        partial_req = job.get("partial_required", [])
        missing_req = job.get("missing_required", [])
        matched_nice = job.get("matched_nice", [])
        partial_nice = job.get("partial_nice", [])
        missing_nice = job.get("missing_nice", [])

        explanation = generate_gap_explanation(
            job_title,
            company,
            matched_req,
            missing_req,
            partial_req
        )

        for skill in missing_req + missing_nice:
            s_clean = skill.strip()
            if s_clean and s_clean.lower() not in seen_missing:
                seen_missing.add(s_clean.lower())
                all_missing_skills.append(s_clean)

        gap_entry = {
            "job_id": job.get("job_id"),
            "title": job_title,
            "company": company,
            "city": job.get("city"),
            "match_score": job.get("match_score", 0.0),
            "matched_required": matched_req,
            "partial_required": partial_req,
            "missing_required": missing_req,
            "matched_nice": matched_nice,
            "partial_nice": partial_nice,
            "missing_nice": missing_nice,
            "explanation": explanation
        }
        job_gaps.append(gap_entry)

    return {
        "job_gaps": job_gaps,
        "all_missing_skills": all_missing_skills
    }

