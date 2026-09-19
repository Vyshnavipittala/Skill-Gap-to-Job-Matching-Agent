from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from app.profile_agent import parse_profile
from app.matcher import match_jobs
from app.gap_agent import analyze_job_gaps
from app.recommender import recommend_training

class AgentState(TypedDict, total=False):
    raw_text: str
    file_bytes: Optional[bytes]
    file_name: Optional[str]
    audio_bytes: Optional[bytes]
    audio_mime_type: Optional[str]
    image_bytes: Optional[bytes]
    image_mime_type: Optional[str]
    selected_location: Optional[str]
    selected_interests: Optional[str]
    user_profile: Dict[str, Any]
    matched_jobs: List[Dict[str, Any]]
    gap_analysis: Dict[str, Any]
    recommendations: Dict[str, Any]
    error: Optional[str]

def node_parse_profile(state: AgentState) -> Dict[str, Any]:
    try:
        profile = parse_profile(
            raw_text=state.get("raw_text", ""),
            file_bytes=state.get("file_bytes"),
            file_name=state.get("file_name"),
            override_location=state.get("selected_location"),
            override_interests=state.get("selected_interests"),
            audio_bytes=state.get("audio_bytes"),
            audio_mime_type=state.get("audio_mime_type", "audio/wav"),
            image_bytes=state.get("image_bytes"),
            image_mime_type=state.get("image_mime_type", "image/jpeg")
        )
        return {"user_profile": profile}
    except Exception as e:
        return {"error": f"Profile parsing error: {str(e)}"}

def node_match_jobs(state: AgentState) -> Dict[str, Any]:
    if state.get("error"):
        return {}
    profile = state.get("user_profile", {})
    skills = profile.get("skills", [])
    location = state.get("selected_location") or profile.get("location", "Any Location")
    try:
        matched = match_jobs(user_skills=skills, user_location=location, top_n=10)
        return {"matched_jobs": matched}
    except Exception as e:
        return {"error": f"Job matching error: {str(e)}"}

def node_analyze_gaps(state: AgentState) -> Dict[str, Any]:
    if state.get("error"):
        return {}
    matched = state.get("matched_jobs", [])
    profile = state.get("user_profile", {})
    skills = profile.get("skills", [])
    try:
        gaps = analyze_job_gaps(top_jobs=matched, user_skills=skills)
        return {"gap_analysis": gaps}
    except Exception as e:
        return {"error": f"Gap analysis error: {str(e)}"}

def node_recommend_training(state: AgentState) -> Dict[str, Any]:
    if state.get("error"):
        return {}
    profile = state.get("user_profile", {})
    skills = profile.get("skills", [])
    matched = state.get("matched_jobs", [])
    gaps = state.get("gap_analysis", {})
    missing = gaps.get("all_missing_skills", [])
    try:
        recs = recommend_training(
            user_skills=skills,
            top_jobs=matched,
            all_missing_skills=missing
        )
        return {"recommendations": recs}
    except Exception as e:
        return {"error": f"Recommendation error: {str(e)}"}

def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("parse_profile", node_parse_profile)
    builder.add_node("match_jobs", node_match_jobs)
    builder.add_node("analyze_gaps", node_analyze_gaps)
    builder.add_node("recommend_training", node_recommend_training)

    builder.add_edge(START, "parse_profile")
    builder.add_edge("parse_profile", "match_jobs")
    builder.add_edge("match_jobs", "analyze_gaps")
    builder.add_edge("analyze_gaps", "recommend_training")
    builder.add_edge("recommend_training", END)

    return builder.compile()

app_graph = build_graph()

def run_skill_gap_pipeline(raw_text="", file_bytes=None, file_name=None, selected_location="Any Location", selected_interests="", audio_bytes=None, audio_mime_type="audio/wav", image_bytes=None, image_mime_type="image/jpeg"):
    initial_state = {
        "raw_text": raw_text,
        "file_bytes": file_bytes,
        "file_name": file_name,
        "audio_bytes": audio_bytes,
        "audio_mime_type": audio_mime_type,
        "image_bytes": image_bytes,
        "image_mime_type": image_mime_type,
        "selected_location": selected_location,
        "selected_interests": selected_interests
    }
    return app_graph.invoke(initial_state)
