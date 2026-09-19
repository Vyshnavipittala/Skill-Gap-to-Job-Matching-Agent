import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import (
    JOBS_FILE,
    COURSES_FILE,
    SIMILARITY_THRESHOLD
)
from app.matcher import (
    match_jobs,
    evaluate_skills_match,
    load_jobs
)
from app.recommender import (
    recommend_training,
    load_courses
)

def evaluate_skill_matching_accuracy():
    jobs = load_jobs(JOBS_FILE)
    total_checks = 0
    correct_matches = 0

    for job in jobs[:10]:
        req_skills = job.get("required_skills", [])
        if not req_skills:
            continue

        test_user_skills = req_skills[:2]
        matched, partial, missing = evaluate_skills_match(
            test_user_skills,
            req_skills,
            sim_threshold=SIMILARITY_THRESHOLD
        )

        for s in test_user_skills:
            total_checks += 1
            if s in matched:
                correct_matches += 1

    accuracy = (correct_matches / total_checks) * 100 if total_checks else 0.0
    return round(accuracy, 2), total_checks, correct_matches

def evaluate_top3_hit_rate(profiles_path="tests/test_profiles.json"):
    with open(profiles_path, "r", encoding="utf-8") as f:
        profiles = json.load(f)

    total_expected = 0
    hits = 0

    print("\n--- Profile Job Matching Evaluation ---")
    for p in profiles:
        skills = p.get("skills", [])
        expected = p.get("expected_top_3_jobs", [])
        loc = p.get("location", "Any Location")

        predicted = match_jobs(skills, user_location="Any Location", top_n=3)
        pred_ids = [j["job_id"] for j in predicted]

        profile_hits = len(set(expected).intersection(set(pred_ids)))
        hits += profile_hits
        total_expected += len(expected)

        status = "PASS" if profile_hits >= 2 else "PARTIAL"
        print(f"[{status}] {p['name']} ({p['domain']}): Expected {expected} | Got {pred_ids} (Hits: {profile_hits}/{len(expected)})")

    hit_rate = (hits / total_expected) * 100 if total_expected else 0.0
    return round(hit_rate, 2), hits, total_expected

def evaluate_course_skill_coverage():
    courses = load_courses(COURSES_FILE)
    jobs = load_jobs(JOBS_FILE)

    all_missing_skills_sample = []
    for j in jobs:
        for s in j.get("required_skills", []):
            if s not in all_missing_skills_sample:
                all_missing_skills_sample.append(s)

    mock_user_skills = ["Python", "Git"]
    mock_top_jobs = match_jobs(mock_user_skills, "Any Location", top_n=5)

    recs = recommend_training(
        mock_user_skills,
        mock_top_jobs,
        all_missing_skills_sample
    )

    total_claimed_skills = 0
    verified_claimed_skills = 0

    courses_dict = {c["name"]: c for c in courses}

    for rec_course in recs.get("ranked_courses", []):
        name = rec_course.get("course_name")
        skills_closed = rec_course.get("skills_closed", [])
        raw_course = courses_dict.get(name)
        if not raw_course:
            continue

        raw_skills = raw_course.get("skills_covered", [])

        for closed_skill in skills_closed:
            total_claimed_skills += 1
            matched, _, _ = evaluate_skills_match(
                raw_skills,
                [closed_skill],
                sim_threshold=SIMILARITY_THRESHOLD
            )
            if closed_skill in matched:
                verified_claimed_skills += 1

    coverage_accuracy = (verified_claimed_skills / total_claimed_skills) * 100 if total_claimed_skills else 0.0
    return round(coverage_accuracy, 2), total_claimed_skills, verified_claimed_skills

def main():
    print("=" * 60)
    print("SKILL GAP MATCHING AGENT EVALUATION SUITE")
    print("=" * 60)

    match_acc, total_m, correct_m = evaluate_skill_matching_accuracy()
    print(f"\n1. Skill-Matching Direct Accuracy: {match_acc}% ({correct_m}/{total_m} verified matches)")

    hit_rate, total_hits, total_exp = evaluate_top3_hit_rate()
    print(f"\n2. Top-3 Job Recommendation Hit Rate: {hit_rate}% ({total_hits}/{total_exp} matched)")

    coverage_rate, total_claims, valid_claims = evaluate_course_skill_coverage()
    print(f"\n3. Course Coverage Semantic Integrity: {coverage_rate}% ({valid_claims}/{total_claims} verified)")

    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Direct Skill Match Accuracy:       {match_acc}%")
    print(f"Top-3 Job Recommendation Hit Rate: {hit_rate}%")
    print(f"Course Coverage Integrity:         {coverage_rate}%")

    assert match_acc >= 90.0, f"Skill matching accuracy {match_acc}% below 90%"
    assert hit_rate >= 80.0, f"Top-3 hit rate {hit_rate}% below 80%"
    assert coverage_rate == 100.0, f"Course coverage integrity {coverage_rate}% below 100%"

    print("\nALL EVALUATION CRITERIA PASSED SUCCESSFULLY!\n")

if __name__ == "__main__":
    main()

