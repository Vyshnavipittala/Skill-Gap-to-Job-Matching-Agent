import itertools
from app.config import (
    STRONG_MATCH_THRESHOLD,
    STUDY_HOURS_PER_WEEK,
    DEFAULT_PAID_COURSE_COST_INR,
    SIM_TOP_JOBS_FOR_COVERAGE,
    SIM_TOP_JOBS_FOR_CANDIDATES,
    SIM_MAX_CANDIDATE_SKILLS,
    SIM_MAX_COMBO_SIZE,
    SIM_TOP_PATHS
)
from app.matcher import match_jobs
from app.recommender import load_courses, find_skills_closed_by_course

ALL_JOBS = 100000
_coverage_cache = {}

def score_all_jobs(skills, location="Any Location"):
    return match_jobs(skills, user_location=location, top_n=ALL_JOBS)

def required_coverage(job):
    total = len(job["matched_required"]) + len(job["partial_required"]) + len(job["missing_required"])
    if total == 0:
        return 100.0
    return len(job["matched_required"]) / total * 100

def compute_metrics(scored_jobs):
    strong = [j for j in scored_jobs if j["match_score"] >= STRONG_MATCH_THRESHOLD]
    top_jobs = scored_jobs[:SIM_TOP_JOBS_FOR_COVERAGE]
    if top_jobs:
        coverage = round(sum(required_coverage(j) for j in top_jobs) / len(top_jobs), 1)
    else:
        coverage = 0.0
    return {
        "strong_matches": len(strong),
        "possible_roles": len({j["title"] for j in strong}),
        "avg_coverage": coverage
    }


def count_improved_jobs(before_scored, after_scored):
    before_by_id = {j["job_id"]: j for j in before_scored}
    return sum(
        1 for j in after_scored
        if j["job_id"] in before_by_id and j["match_score"] > before_by_id[j["job_id"]]["match_score"]
    )

def get_baseline(user_skills, location="Any Location"):
    scored = score_all_jobs(user_skills, location)
    return {"scored": scored, "metrics": compute_metrics(scored)}

def missing_skill_options(scored_jobs, user_skills, top_n=SIM_TOP_JOBS_FOR_CANDIDATES):
    counts = {}
    names = {}
    for job in scored_jobs[:top_n]:
        for skill in job["all_missing"]:
            key = skill.strip().lower()
            if key:
                counts[key] = counts.get(key, 0) + 1
                names.setdefault(key, skill.strip())
    known = {s.strip().lower() for s in user_skills}
    ordered = sorted(counts, key=lambda k: (-counts[k], k))
    return [names[k] for k in ordered if k not in known]

def is_free(course):
    return str(course.get("cost", "")).strip().lower() == "free"

def course_cost_inr(course):
    if is_free(course):
        return 0
    return course.get("cost_inr", DEFAULT_PAID_COURSE_COST_INR)

def course_covers(course, skill):
    key = (course["name"], skill.strip().lower())
    if key not in _coverage_cache:
        covered = find_skills_closed_by_course(course.get("skills_covered", []), [skill])
        _coverage_cache[key] = bool(covered)
    return _coverage_cache[key]

def choose_courses(skills, courses, budget_left_inr=None):
    remaining = list(skills)
    chosen = []
    without_course = []
    spent = 0
    while remaining:
        best_course = None
        best_key = None
        best_covered = []
        for course in courses:
            covered = [s for s in remaining if course_covers(course, s)]
            if not covered:
                continue
            price = course_cost_inr(course)
            affordable = budget_left_inr is None or spent + price <= budget_left_inr
            key = (
                1 if affordable else 0,
                len(covered),
                1 if is_free(course) else 0,
                -price,
                -course.get("duration_hours", 0)
            )
            if best_key is None or key > best_key:
                best_course = course
                best_key = key
                best_covered = covered
        if best_course is None:
            without_course.extend(remaining)
            break
        spent += course_cost_inr(best_course)
        chosen.append({"course": best_course, "covers": best_covered})
        remaining = [s for s in remaining if s not in best_covered]
    return chosen, without_course

def build_course_rows(chosen):
    rows = []
    for item in chosen:
        course = item["course"]
        rows.append({
            "course_name": course["name"],
            "platform": course.get("platform", "Online"),
            "duration_hours": course.get("duration_hours", 0),
            "cost": course.get("cost", "Paid"),
            "cost_inr": course_cost_inr(course),
            "url": course.get("url", ""),
            "verify_url": course.get("verify_url", False),
            "covers": item["covers"]
        })
    return rows

def unique_skills(skills):
    seen = set()
    result = []
    for skill in skills:
        key = skill.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(skill.strip())
    return result

def find_unlocked_jobs(before_scored, after_scored):
    before_by_id = {j["job_id"]: j for j in before_scored}
    unlocked = []
    for job in after_scored:
        before = before_by_id.get(job["job_id"])
        if before is None:
            continue
        was_weak = before["match_score"] < STRONG_MATCH_THRESHOLD
        is_strong = job["match_score"] >= STRONG_MATCH_THRESHOLD
        if was_weak and is_strong:
            unlocked.append({
                "job_id": job["job_id"],
                "title": job["title"],
                "company": job["company"],
                "city": job["city"],
                "score_before": before["match_score"],
                "score_after": job["match_score"]
            })
    return unlocked

def count_skill_demand(scored_jobs, skills):
    demand = {}
    for skill in skills:
        key = skill.strip().lower()
        demand[skill] = sum(1 for job in scored_jobs if key in [m.strip().lower() for m in job["all_missing"]])
    return demand

def build_job_changes(before_scored, after_scored):
    before_by_id = {j["job_id"]: j for j in before_scored}
    changes = []
    for job in after_scored:
        before = before_by_id.get(job["job_id"])
        if before is None or job["match_score"] <= before["match_score"]:
            continue
        closed_required = [s for s in before["missing_required"] + before["partial_required"] if s in job["matched_required"]]
        closed_nice = [s for s in before["missing_nice"] + before["partial_nice"] if s in job["matched_nice"]]
        if job["match_score"] >= STRONG_MATCH_THRESHOLD and before["match_score"] < STRONG_MATCH_THRESHOLD:
            status = "Unlocked"
        elif job["match_score"] >= STRONG_MATCH_THRESHOLD:
            status = "Already strong, now stronger"
        else:
            status = "Improved, still below strong"
        changes.append({
            "job_id": job["job_id"],
            "title": job["title"],
            "company": job["company"],
            "city": job["city"],
            "score_before": before["match_score"],
            "score_after": job["match_score"],
            "closed_required": closed_required,
            "closed_nice": closed_nice,
            "still_missing_required": job["missing_required"],
            "status": status
        })
    changes.sort(key=lambda c: c["score_after"], reverse=True)
    return changes

def simulate_scenario(user_skills, skills_to_learn, location="Any Location", hours_per_week=STUDY_HOURS_PER_WEEK, baseline=None, courses=None):
    if hours_per_week <= 0:
        raise ValueError("hours_per_week must be greater than 0")
    if courses is None:
        courses = load_courses()
    if baseline is None:
        baseline = get_baseline(user_skills, location)

    known = {s.strip().lower() for s in user_skills}
    requested = unique_skills(skills_to_learn)
    already_known = [s for s in requested if s.lower() in known]
    to_learn = [s for s in requested if s.lower() not in known]

    chosen, without_course = choose_courses(to_learn, courses)
    learned = [s for s in to_learn if s not in without_course]
    course_rows = build_course_rows(chosen)

    total_hours = sum(row["duration_hours"] for row in course_rows)
    total_cost = sum(row["cost_inr"] for row in course_rows)

    if learned:
        after_scored = score_all_jobs(list(user_skills) + learned, location)
    else:
        after_scored = baseline["scored"]

    before_metrics = baseline["metrics"]
    after_metrics = compute_metrics(after_scored)
    unlocked = find_unlocked_jobs(baseline["scored"], after_scored)

    job_changes = build_job_changes(baseline["scored"], after_scored)
    skill_demand = count_skill_demand(baseline["scored"], learned)
    remaining_gaps = missing_skill_options(after_scored, list(user_skills) + learned)[:3]

    exact_weeks = total_hours / hours_per_week
    if exact_weeks > 0:
        jobs_per_week = round(len(unlocked) / exact_weeks, 2)
    else:
        jobs_per_week = 0.0

    return {
        "skills_requested": requested,
        "skills_learned": learned,
        "skills_already_known": already_known,
        "skills_without_course": without_course,
        "courses": course_rows,
        "total_hours": total_hours,
        "hours_per_week": hours_per_week,
        "weeks": round(exact_weeks, 1),
        "cost_inr": total_cost,
        "before": before_metrics,
        "after": after_metrics,
        "strong_gain": after_metrics["strong_matches"] - before_metrics["strong_matches"],
        "unlocked_jobs": unlocked,
        "jobs_unlocked": len(unlocked),
        "jobs_improved": len(job_changes),
        "jobs_unlocked_per_week": jobs_per_week,
        "job_changes": job_changes,
        "skill_demand": skill_demand,
        "jobs_analysed": len(baseline["scored"]),
        "remaining_gaps": remaining_gaps
    }

def fits_budget(total_hours, total_cost, budget_weeks, max_cost_inr, hours_per_week):
    return total_hours <= budget_weeks * hours_per_week and total_cost <= max_cost_inr

def candidate_skills_for_search(scored_jobs, user_skills, courses):
    candidates = []
    skipped = []
    for skill in missing_skill_options(scored_jobs, user_skills):
        chosen, without_course = choose_courses([skill], courses)
        if not without_course:
            candidates.append(skill)
        else:
            skipped.append(skill)
        if len(candidates) == SIM_MAX_CANDIDATE_SKILLS:
            break
    if not candidates:
        candidates = skipped[:SIM_MAX_CANDIDATE_SKILLS]
    return candidates

def path_rank_key(result):
    coverage_gain = result["after"]["avg_coverage"] - result["before"]["avg_coverage"]
    return (
        result["strong_gain"],
        result["jobs_improved"],
        round(coverage_gain, 2),
        -result["cost_inr"],
        -result["total_hours"]
    )

def find_best_paths(user_skills, location, budget_weeks, max_cost_inr, hours_per_week=STUDY_HOURS_PER_WEEK, baseline=None, courses=None):
    if courses is None:
        courses = load_courses()
    if baseline is None:
        baseline = get_baseline(user_skills, location)

    candidates = candidate_skills_for_search(baseline["scored"], user_skills, courses)
    results = []

    for size in range(1, SIM_MAX_COMBO_SIZE + 1):
        for combo in itertools.combinations(candidates, size):
            chosen, without_course = choose_courses(list(combo), courses, max_cost_inr)
            if without_course:
                continue
            rows = build_course_rows(chosen)
            hours = sum(row["duration_hours"] for row in rows)
            cost = sum(row["cost_inr"] for row in rows)
            if not fits_budget(hours, cost, budget_weeks, max_cost_inr, hours_per_week):
                continue
            result = simulate_scenario(user_skills, list(combo), location, hours_per_week, baseline, courses)
            coverage_gain = result["after"]["avg_coverage"] - result["before"]["avg_coverage"]
            if result["strong_gain"] > 0 or coverage_gain > 0:
                results.append(result)

    results.sort(key=path_rank_key, reverse=True)
    return results[:SIM_TOP_PATHS]