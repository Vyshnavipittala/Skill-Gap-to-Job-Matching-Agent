import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.graph import run_skill_gap_pipeline

def test_full_pipeline_end_to_end():
    sample_text = """
    Ravi Kumar
    Education: B.Tech in Information Technology
    Experience: 2 years
    Location: Hyderabad
    Skills: Python, FastAPI, PostgreSQL, REST API, Git, Docker
    Interests: Backend Engineering, Cloud Systems
    """

    result = run_skill_gap_pipeline(
        raw_text=sample_text,
        selected_location="Any Location",
        selected_interests="Backend Development"
    )

    assert "error" not in result or result["error"] is None

    profile = result.get("user_profile")
    assert profile is not None
    assert "skills" in profile
    assert len(profile["skills"]) >= 5
    assert "Python" in profile["skills"]
    assert "FastAPI" in profile["skills"]

    matched_jobs = result.get("matched_jobs")
    assert matched_jobs is not None
    assert len(matched_jobs) > 0
    top_job = matched_jobs[0]
    assert "match_score" in top_job
    assert top_job["match_score"] > 50.0

    gap_analysis = result.get("gap_analysis")
    assert gap_analysis is not None
    job_gaps = gap_analysis.get("job_gaps", [])
    assert len(job_gaps) > 0
    first_gap = job_gaps[0]
    assert "explanation" in first_gap
    assert len(first_gap["explanation"]) > 10

    recommendations = result.get("recommendations")
    assert recommendations is not None
    ranked_courses = recommendations.get("ranked_courses", [])
    assert len(ranked_courses) > 0
    first_course = ranked_courses[0]
    assert "course_name" in first_course
    assert "roi_reason" in first_course
    assert "duration_hours" in first_course

    learning_order = recommendations.get("learning_order", [])
    assert len(learning_order) > 0

    print("END-TO-END LANGGRAPH PIPELINE TEST PASSED!")
    print(f"Top Matched Job: {top_job['title']} at {top_job['company']} (Score: {top_job['match_score']}%)")
    print(f"Top Recommendation: {first_course['course_name']} ({first_course['platform']})")
    print(f"ROI Justification: {first_course['roi_reason']}")

if __name__ == "__main__":
    test_full_pipeline_end_to_end()

