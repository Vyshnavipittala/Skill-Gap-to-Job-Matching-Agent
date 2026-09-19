import json
from app.config import (
    COURSES_FILE,
    JOBS_FILE,
    STRONG_MATCH_THRESHOLD,
    SIMILARITY_THRESHOLD
)
from app.matcher import (
    evaluate_skills_match,
    calculate_job_score,
    load_jobs
)

def load_courses(courses_path=COURSES_FILE):
    with open(courses_path, "r", encoding="utf-8") as f:
        return json.load(f)

def find_skills_closed_by_course(course_skills, missing_skills, threshold=SIMILARITY_THRESHOLD):
    if not course_skills or not missing_skills:
        return []
    matched, _, _ = evaluate_skills_match(course_skills, missing_skills, sim_threshold=threshold)
    return matched

def recommend_training(user_skills, top_jobs, all_missing_skills, courses_path=COURSES_FILE, jobs_path=JOBS_FILE):
    courses = load_courses(courses_path)
    all_jobs = {j["id"]: j for j in load_jobs(jobs_path)}

    candidate_courses = []

    for course in courses:
        course_name = course.get("name")
        course_skills = course.get("skills_covered", [])
        platform = course.get("platform", "Online")
        duration = course.get("duration_hours", 0)
        cost = course.get("cost", "Paid")
        url = course.get("url", "")
        verify_url = course.get("verify_url", False)

        skills_closed = find_skills_closed_by_course(course_skills, all_missing_skills)
        if not skills_closed:
            continue

        simulated_skills = list(set(user_skills + skills_closed))

        unlocked_jobs = []
        score_deltas = []
        score_comparisons = []

        for job_summary in top_jobs:
            job_id = job_summary.get("job_id")
            original_job = all_jobs.get(job_id)
            if not original_job:
                continue

            score_before = job_summary.get("match_score", 0.0)
            recalculated = calculate_job_score(simulated_skills, original_job)
            score_after = recalculated.get("match_score", 0.0)
            gain = round(max(0.0, score_after - score_before), 1)

            score_deltas.append(gain)
            score_comparisons.append({
                "job_title": original_job.get("title"),
                "company": original_job.get("company"),
                "score_before": score_before,
                "score_after": score_after,
                "score_gain": gain
            })

            if score_before <= STRONG_MATCH_THRESHOLD and score_after > STRONG_MATCH_THRESHOLD:
                unlocked_jobs.append(f"{original_job.get('title')} ({original_job.get('company')})")

        avg_gain = round(sum(score_deltas) / len(score_deltas), 1) if score_deltas else 0.0

        if unlocked_jobs:
            roi_reason = f"Closes {', '.join(skills_closed[:2])} to unlock {len(unlocked_jobs)} strong job match(es) with an avg +{avg_gain}% score boost."
        elif avg_gain > 0:
            roi_reason = f"Boosts top role alignment by +{avg_gain}% on average by mastering {', '.join(skills_closed[:2])}."
        else:
            roi_reason = f"Provides foundational proficiency in {', '.join(skills_closed[:2])}."

        candidate_courses.append({
            "course_name": course_name,
            "platform": platform,
            "skills_closed": skills_closed,
            "jobs_unlocked": unlocked_jobs,
            "num_unlocked": len(unlocked_jobs),
            "avg_gain": avg_gain,
            "duration_hours": duration,
            "cost": cost,
            "url": url,
            "verify_url": verify_url,
            "score_comparisons": score_comparisons,
            "roi_reason": roi_reason
        })

    candidate_courses.sort(
        key=lambda c: (c["num_unlocked"], c["avg_gain"], -c["duration_hours"]),
        reverse=True
    )

    ranked_courses = candidate_courses[:8]

    learning_order = []
    for step_num, course in enumerate(ranked_courses, 1):
        learning_order.append({
            "step": step_num,
            "course_name": course["course_name"],
            "platform": course["platform"],
            "duration_hours": course["duration_hours"],
            "skills_covered": course["skills_closed"],
            "impact_summary": f"Unlocks {course['num_unlocked']} jobs (+{course['avg_gain']}% avg score)"
        })

    return {
        "ranked_courses": ranked_courses,
        "learning_order": learning_order
    }

