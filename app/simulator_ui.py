import os
import streamlit as st
import pandas as pd
from app.config import STUDY_HOURS_PER_WEEK
from app.simulator import (
    get_baseline,
    missing_skill_options,
    simulate_scenario,
    find_best_paths
)
from app.llm import generate_scenario_summary

SLOTS = ["A", "B", "C"]
BUDGET_OPTIONS = [4, 8, 12]

def reset_simulator_state():
    for key in ["sim_skills", "saved_scenarios", "best_paths", "sim_summary", "weekly_outlook"]:
        if key in st.session_state:
            del st.session_state[key]

def load_scenario(skills):
    st.session_state["sim_skills"] = list(skills)

def save_scenario(slot, result):
    saved = st.session_state.get("saved_scenarios", {})
    saved[slot] = result
    st.session_state["saved_scenarios"] = saved

def format_money(amount):
    return f"₹{int(amount):,}"

def format_weeks(weeks):
    return f"{weeks} weeks"

def metric_card(value, label):
    return f'<div class="metric-box"><div class="metric-val">{value}</div><div class="metric-lbl">{label}</div></div>'

def comparison_rows(baseline_metrics, columns):
    rows = {
        "Skills to learn": [],
        "Strong job matches": [],
        "Possible roles": [],
        "Average skill coverage": [],
        "Learning time": [],
        "Learning cost": [],
        "Jobs improved": [],
        "Jobs unlocked": []
    }
    labels = ["Baseline"]
    rows["Skills to learn"].append("—")
    rows["Strong job matches"].append(str(baseline_metrics["strong_matches"]))
    rows["Possible roles"].append(str(baseline_metrics["possible_roles"]))
    rows["Average skill coverage"].append(f"{baseline_metrics['avg_coverage']}%")
    rows["Learning time"].append("—")
    rows["Learning cost"].append("—")
    rows["Jobs improved"].append("—")
    rows["Jobs unlocked"].append("—")

    for label, result in columns:
        labels.append(label)
        rows["Skills to learn"].append(", ".join(result["skills_learned"]) or "—")
        rows["Strong job matches"].append(str(result["after"]["strong_matches"]))
        rows["Possible roles"].append(str(result["after"]["possible_roles"]))
        rows["Average skill coverage"].append(f"{result['after']['avg_coverage']}%")
        rows["Learning time"].append(format_weeks(result["weeks"]))
        rows["Learning cost"].append(format_money(result["cost_inr"]))
        rows["Jobs improved"].append(str(result["jobs_improved"]))
        rows["Jobs unlocked"].append(str(result["jobs_unlocked"]))

    return pd.DataFrame(rows, index=labels).T

def before_after_table(result):
    before = result["before"]
    after = result["after"]
    data = {
        "Metric": [
            "Strong job matches",
            "Possible roles",
            "Average skill coverage",
            "Learning time",
            "Learning cost",
            "Jobs improved",
            "Jobs unlocked"
        ],
        "Before": [
            str(before["strong_matches"]),
            str(before["possible_roles"]),
            f"{before['avg_coverage']}%",
            "—",
            "—",
            "—",
            "—"
        ],
        "After": [
            str(after["strong_matches"]),
            str(after["possible_roles"]),
            f"{after['avg_coverage']}%",
            format_weeks(result["weeks"]),
            format_money(result["cost_inr"]),
            str(result["jobs_improved"]),
            str(result["jobs_unlocked"])
        ]
    }
    return pd.DataFrame(data)

def show_profile_summary(profile, baseline, skills):
    st.markdown(f"**👤 {profile.get('name', 'Candidate')}** · 🎓 {profile.get('education', 'Education Not Specified')} · 📍 {profile.get('location', 'Any Location')}")
    chips = " ".join([f'<span class="badge-skill">✓ {s}</span>' for s in skills])
    st.markdown(f"<div style='margin-bottom:0.75rem;'>{chips}</div>", unsafe_allow_html=True)

    metrics = baseline["metrics"]
    cols = st.columns(4)
    cards = [
        (metrics["strong_matches"], "Strong Matches Now"),
        (metrics["possible_roles"], "Possible Roles"),
        (f"{metrics['avg_coverage']}%", "Avg Skill Coverage"),
        (len(baseline["scored"]), "Jobs Analysed")
    ]
    for col, (value, label) in zip(cols, cards):
        with col:
            st.markdown(metric_card(value, label), unsafe_allow_html=True)

def gap_summary_line(result):
    closed = set()
    for change in result["job_changes"]:
        closed.update(change["closed_required"])
    return f"Improves {len(result['job_changes'])} of {result['jobs_analysed']} jobs by closing {len(closed)} required skill gap(s)."

def show_justification(result):
    st.markdown("##### 🧠 Why this works (based on your gaps)")
    for skill, count in result["skill_demand"].items():
        st.markdown(f"- **{skill}** is a missing skill in **{count} of {result['jobs_analysed']}** jobs.")

    if not result["job_changes"]:
        st.caption("These skills do not close any required gap in your current job list, so no job score improves.")
        return

    rows = [
        {
            "Role": change["title"],
            "Company": change["company"],
            "Score": f"{change['score_before']}% → {change['score_after']}%",
            "Gaps closed": ", ".join(change["closed_required"] + change["closed_nice"]) or "—",
            "Still missing (required)": ", ".join(change["still_missing_required"]) or "None",
            "Result": change["status"]
        }
        for change in result["job_changes"][:8]
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if result["remaining_gaps"]:
        st.caption("Biggest gaps still left after this scenario: " + ", ".join(result["remaining_gaps"]))

def show_courses(result):
    if result["skills_without_course"]:
        st.warning("No course found in the catalog for: " + ", ".join(result["skills_without_course"]) + ". These skills are not counted in the simulation.")
    if result["skills_already_known"]:
        st.info("Already in your profile: " + ", ".join(result["skills_already_known"]))
    if not result["courses"]:
        return
    st.markdown("##### 🎓 Courses chosen for this scenario")
    rows = []
    for course in result["courses"]:
        link = course["url"] + (" (verify link)" if course["verify_url"] else "")
        rows.append({
            "Skills covered": ", ".join(course["covers"]),
            "Course": course["course_name"],
            "Platform": course["platform"],
            "Hours": course["duration_hours"],
            "Cost": "Free" if course["cost_inr"] == 0 else f"{course['cost']} (~{format_money(course['cost_inr'])})",
            "Link": link
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

def show_unlocked_jobs(result):
    st.markdown("##### 🔓 Newly unlocked jobs")
    if not result["unlocked_jobs"]:
        st.caption("No job crosses into a strong match with this scenario.")
        return
    rows = [
        {
            "Role": job["title"],
            "Company": job["company"],
            "City": job["city"],
            "Score Before": f"{job['score_before']}%",
            "New Score": f"{job['score_after']}%"
        }
        for job in result["unlocked_jobs"]
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

def show_saved_scenarios(baseline):
    saved = st.session_state.get("saved_scenarios", {})
    if not saved:
        st.caption("Save up to three scenarios (A, B, C) to compare them side by side.")
        return
    st.markdown("##### 📊 Scenario comparison")
    columns = [(slot, saved[slot]) for slot in SLOTS if slot in saved]
    st.dataframe(comparison_rows(baseline["metrics"], columns), use_container_width=True)

    labels = ["Baseline"] + [label for label, _ in columns]
    strong_values = [baseline["metrics"]["strong_matches"]] + [r["after"]["strong_matches"] for _, r in columns]
    coverage_values = [baseline["metrics"]["avg_coverage"]] + [r["after"]["avg_coverage"] for _, r in columns]
    if max(strong_values) > 0:
        chart_data = pd.DataFrame({"Strong job matches": strong_values}, index=labels)
    else:
        st.caption("No scenario reaches a strong match yet, so the chart shows average skill coverage (%) instead.")
        chart_data = pd.DataFrame({"Average skill coverage (%)": coverage_values}, index=labels)
    st.bar_chart(chart_data)

def show_best_paths(user_skills, location, baseline):
    st.markdown("##### 🧭 Best path finder")
    budget = st.session_state.get("sim_budget", 8)
    max_cost = st.session_state.get("sim_max_cost", 3000)
    hours = st.session_state.get("sim_hours", STUDY_HOURS_PER_WEEK)

    if st.button("🔎 Find my best path", key="find_best_path", type="primary"):
        with st.spinner("Trying skill combinations..."):
            paths = find_best_paths(user_skills, location, budget, max_cost, hours, baseline)
        st.session_state["best_paths"] = {
            "paths": paths,
            "budget": budget,
            "max_cost": max_cost,
            "hours": hours
        }

    found = st.session_state.get("best_paths")
    if not found:
        return

    st.caption(f"Searched for {found['budget']} weeks, up to {format_money(found['max_cost'])}, at {found['hours']} hours per week.")
    if not found["paths"]:
        st.warning("No skill combination fits this time and cost budget and improves your matches. Try more weeks, a higher cost limit, or more hours per week.")
        return

    for index, path in enumerate(found["paths"], 1):
        with st.container():
            st.markdown(f"**#{index} · Learn {', '.join(path['skills_learned'])}**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Strong matches", f"{path['before']['strong_matches']} → {path['after']['strong_matches']}")
            c2.metric("Time", format_weeks(path["weeks"]))
            c3.metric("Cost", format_money(path["cost_inr"]))
            c4.metric("Jobs improved", f"{path['jobs_improved']} ({path['jobs_unlocked']} unlocked)")
            st.caption(gap_summary_line(path))
            st.button("Try this scenario", key=f"try_path_{index}", on_click=load_scenario, args=(path["skills_learned"],))

def show_explanation(result):
    key = (tuple(result["skills_learned"]), result["hours_per_week"])
    if st.button("✨ Explain this scenario in plain language", key="sim_explain"):
        text = generate_scenario_summary(result)
        st.session_state["sim_summary"] = {"key": key, "text": text}
    summary = st.session_state.get("sim_summary")
    if summary and summary["key"] == key:
        if summary["text"]:
            st.success(summary["text"])
        else:
            st.info("No AI summary available right now (check GEMINI_API_KEY). The numbers above are complete.")

def render_simulator(res):
    profile = res.get("user_profile", {})
    skills = profile.get("skills", [])
    location = res.get("selected_location") or profile.get("location", "Any Location")

    st.markdown("#### 🧪 Career Skill Investment Simulator")
    st.caption("Try different learning choices and see how your job matches would change. A learned skill is treated as fully acquired.")

    if not skills:
        st.warning("No skills were found in the profile yet. Analyze a profile with at least one skill to use the simulator.")
        return

    baseline = get_baseline(skills, location)
    show_profile_summary(profile, baseline, skills)
    st.markdown("---")

    options = missing_skill_options(baseline["scored"], skills)
    if not options:
        st.success("No missing skills found in your top jobs. Nothing left to simulate.")
        return

    current = st.session_state.get("sim_skills", [])
    st.session_state["sim_skills"] = [s for s in current if s in options]

    # --- Step 1: settings + Best path finder, shown first ---
    hours_col, budget_col, cost_col = st.columns(3)
    with hours_col:
        st.slider("Study hours per week", 2, 40, STUDY_HOURS_PER_WEEK, key="sim_hours")
    with budget_col:
        st.radio("Time budget (for best path finder)", BUDGET_OPTIONS, index=1, horizontal=True, format_func=lambda w: f"{w} weeks", key="sim_budget")
    with cost_col:
        st.number_input("Max cost in ₹ (0 = free courses only)", min_value=0, value=3000, step=500, key="sim_max_cost")

    hours = st.session_state.get("sim_hours", STUDY_HOURS_PER_WEEK)

    show_best_paths(skills, location, baseline)
    st.markdown("---")

    # --- Step 2: manual scenario builder, shown after / below Best path finder ---
    st.markdown("##### 🛠️ Build your own scenario")
    st.caption("Pick skills yourself, or click \"Try this scenario\" above to load one here.")
    selected = st.multiselect("➕ Add skills to learn", options, key="sim_skills")

    if not selected:
        st.info("Pick at least one skill above (or try a path above) to see how your job matches would change.")
    else:
        result = simulate_scenario(skills, selected, location, hours, baseline)
        st.markdown("##### 🔁 Before vs After")
        st.dataframe(before_after_table(result), use_container_width=True, hide_index=True)
        show_justification(result)
        show_courses(result)
        show_unlocked_jobs(result)
        show_explanation(result)

        save_col, save_btn_col = st.columns([1, 1])
        with save_col:
            slot = st.selectbox("Save this scenario as", SLOTS, key="sim_slot")
        with save_btn_col:
            st.markdown("<div style='height:1.9rem;'></div>", unsafe_allow_html=True)
            st.button("💾 Save scenario", key="sim_save", on_click=save_scenario, args=(slot, result))

    st.markdown("---")
    show_saved_scenarios(baseline)

def render_weekly_outlook(res):
    profile = res.get("user_profile", {})
    skills = profile.get("skills", [])
    location = res.get("selected_location") or profile.get("location", "Any Location")
    if not skills:
        return

    st.markdown("#### 🔮 What if you invest the next 4, 8 or 12 weeks?")
    st.caption("Instead of only asking what skills are missing, see how your job opportunities change with the best learning combination for each time budget.")

    if st.button("Show my 4 / 8 / 12 week outlook", key="weekly_outlook_btn", type="primary"):
        hours = st.session_state.get("sim_hours", STUDY_HOURS_PER_WEEK)
        max_cost = st.session_state.get("sim_max_cost", 3000)
        with st.spinner("Trying learning combinations for each time budget..."):
            baseline = get_baseline(skills, location)
            outlook = {}
            for weeks in BUDGET_OPTIONS:
                paths = find_best_paths(skills, location, weeks, max_cost, hours, baseline)
                outlook[weeks] = paths[0] if paths else None
        st.session_state["weekly_outlook"] = {"data": outlook, "hours": hours, "max_cost": max_cost}

    found = st.session_state.get("weekly_outlook")
    if not found:
        return

    st.caption(f"Best combination for each budget, at {found['hours']} hours per week and up to {format_money(found['max_cost'])}.")
    cols = st.columns(3)
    for col, weeks in zip(cols, BUDGET_OPTIONS):
        path = found["data"][weeks]
        with col:
            st.markdown(f"**⏳ {weeks} weeks**")
            if path is None:
                st.info("No combination fits this budget and improves your matches.")
                continue
            st.markdown("Learn: " + ", ".join(path["skills_learned"]))
            st.metric("Strong job matches", f"{path['before']['strong_matches']} → {path['after']['strong_matches']}")
            st.metric("Possible roles", f"{path['before']['possible_roles']} → {path['after']['possible_roles']}")
            st.metric("Avg skill coverage", f"{path['before']['avg_coverage']}% → {path['after']['avg_coverage']}%")
            st.caption(f"⏱️ {format_weeks(path['weeks'])} · 💰 {format_money(path['cost_inr'])}")
            st.caption(gap_summary_line(path))
    st.caption("Open the Career Simulator tab to try your own combinations.")