import os
import streamlit as st
import pandas as pd
from app.graph import run_skill_gap_pipeline

st.set_page_config(
    page_title="Skill-Gap-to-Job Matching Agent",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
}

.main-title {
    font-size: 2.3rem;
    font-weight: 800;
    background: linear-gradient(135deg, #2563eb 0%, #7c3aed 50%, #db2777 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}

.sub-title {
    font-size: 1.05rem;
    color: #64748b;
    margin-bottom: 1.5rem;
    font-weight: 500;
}

.hero-card {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 15px -2px rgba(0, 0, 0, 0.05);
}

.metric-box {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    text-align: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.02);
}

.metric-val {
    font-size: 1.7rem;
    font-weight: 800;
    color: #1e293b;
    line-height: 1.2;
}

.metric-lbl {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #64748b;
    margin-top: 0.25rem;
}

.badge-matched {
    background-color: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 600;
    display: inline-block;
    margin: 3px;
}

.badge-partial {
    background-color: #fffbeb;
    color: #92400e;
    border: 1px solid #fde68a;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 600;
    display: inline-block;
    margin: 3px;
}

.badge-missing {
    background-color: #fef2f2;
    color: #991b1b;
    border: 1px solid #fecaca;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 600;
    display: inline-block;
    margin: 3px;
}

.badge-skill {
    background-color: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    display: inline-block;
    margin: 3px;
}

.step-card {
    background: #ffffff;
    border-left: 5px solid #3b82f6;
    border: 1px solid #e2e8f0;
    border-left-width: 5px;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.85rem;
    box-shadow: 0 2px 5px rgba(0,0,0,0.03);
}

.job-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.roi-pill {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 700;
    display: inline-block;
}

.gain-pill {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 700;
    display: inline-block;
}

.stButton>button {
    border-radius: 10px;
    font-weight: 600;
    transition: all 0.2s ease;
}

.stButton>button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown('<div class="main-title">🎯 Skill-Gap-to-Job Matching Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Multi-Agent Career Intelligence: Convert unstructured input (Voice, Images, Documents, Free-text) into precision job matches, gap diagnostics, and an ROI-ranked training path.</div>', unsafe_allow_html=True)

CITIES = [
    "Any Location",
    "Bengaluru",
    "Hyderabad",
    "Pune",
    "Mumbai",
    "Chennai",
    "Delhi NCR"
]

SAMPLE_PROFILES = {
    "Backend Engineer": {
        "text": "Aarav Sharma, B.Tech in CSE with 2 years of experience in Bengaluru. Core skills: Python, FastAPI, PostgreSQL, REST API, Git. Looking for backend or distributed systems engineering roles.",
        "location": "Bengaluru",
        "interests": "Backend Development, Distributed Systems"
    },
    "Data Analyst": {
        "text": "Rohan Deshmukh, Bachelor in Statistics with 1 year experience in Bengaluru. Skills: SQL, Python, Microsoft Excel, Tableau. Passionate about business intelligence and product analytics.",
        "location": "Bengaluru",
        "interests": "Business Intelligence, Data Analytics"
    },
    "Embedded / IoT": {
        "text": "Karthik Nair, B.Tech in Electronics with 2 years experience in Bengaluru. Core competencies: Embedded C, C++, Microcontrollers, RTOS, Git, IoT. Interested in firmware and robotics.",
        "location": "Bengaluru",
        "interests": "Embedded Systems, Robotics, IoT"
    },
    "UI/UX Designer": {
        "text": "Tanvi Joshi, Degree in Design with 2 years experience in Bengaluru. Skilled in Figma, UI/UX Design, Wireframing, Prototyping, User Research. Enthusiastic about user-centric product design.",
        "location": "Bengaluru",
        "interests": "Product Design, Design Systems"
    }
}

if "input_text" not in st.session_state:
    st.session_state["input_text"] = ""
if "input_location" not in st.session_state:
    st.session_state["input_location"] = "Any Location"
if "input_interests" not in st.session_state:
    st.session_state["input_interests"] = ""

left_col, right_col = st.columns([1, 1.35], gap="large")

with left_col:
    st.markdown("### 📋 Candidate Profile Intake")

    st.markdown("**⚡ Quick Demo Profiles:**")
    quick_cols = st.columns(4)
    for idx, (label, sample_data) in enumerate(SAMPLE_PROFILES.items()):
        with quick_cols[idx]:
            if st.button(label, key=f"quick_{label}", use_container_width=True):
                st.session_state["input_text"] = sample_data["text"]
                st.session_state["input_location"] = sample_data["location"]
                st.session_state["input_interests"] = sample_data["interests"]
                st.rerun()

    input_tab1, input_tab2, input_tab3, input_tab4 = st.tabs([
        "✍️ Free Text",
        "🎙️ Voice Input",
        "📄 Document (PDF/TXT)",
        "🖼️ Image Scan"
    ])

    audio_bytes = None
    audio_mime_type = "audio/wav"
    image_bytes = None
    image_mime_type = "image/jpeg"
    file_bytes = None
    file_name = None

    with input_tab1:
        profile_text = st.text_area(
            "Paste Resume or Profile Summary",
            value=st.session_state.get("input_text", ""),
            height=170,
            placeholder="e.g. Software engineer with 2 years experience in Python, FastAPI, and PostgreSQL. Familiar with Docker and Git..."
        )

    with input_tab2:
        st.markdown("**Speak your profile intro or upload an audio recording:**")
        recorded_audio = st.audio_input("Record via Microphone")
        if recorded_audio is not None:
            audio_bytes = recorded_audio.getvalue()
            audio_mime_type = recorded_audio.type or "audio/wav"
            st.success("🎙️ Voice recorded successfully!")

        audio_file = st.file_uploader(
            "Or upload audio recording (.wav, .mp3, .m4a)",
            type=["wav", "mp3", "m4a", "ogg", "webm"],
            key="audio_upload"
        )
        if audio_file is not None:
            audio_bytes = audio_file.getvalue()
            audio_mime_type = audio_file.type or "audio/wav"
            st.success(f"🎙️ Uploaded: {audio_file.name}")

    with input_tab3:
        uploaded_doc = st.file_uploader(
            "Upload Resume Document (.pdf or .txt)",
            type=["pdf", "txt"],
            key="doc_upload"
        )
        if uploaded_doc is not None:
            file_bytes = uploaded_doc.getvalue()
            file_name = uploaded_doc.name
            st.success(f"📄 Uploaded: {uploaded_doc.name}")

    with input_tab4:
        uploaded_img = st.file_uploader(
            "Upload Scanned Resume or Certificate (.png, .jpg, .jpeg)",
            type=["png", "jpg", "jpeg", "webp"],
            key="img_upload"
        )
        if uploaded_img is not None:
            image_bytes = uploaded_img.getvalue()
            image_mime_type = uploaded_img.type or "image/jpeg"
            st.image(image_bytes, caption="Uploaded Document Preview", use_container_width=True)

    loc_index = CITIES.index(st.session_state.get("input_location", "Any Location")) if st.session_state.get("input_location") in CITIES else 0
    selected_location = st.selectbox(
        "📍 Target Location",
        CITIES,
        index=loc_index
    )

    interests_text = st.text_input(
        "💡 Career Interests & Target Domains",
        value=st.session_state.get("input_interests", ""),
        placeholder="e.g. Backend Engineering, Distributed Systems, Cloud"
    )

    run_btn = st.button("🚀 Analyze Skill Gaps & Match Jobs", type="primary", use_container_width=True)

    if not os.getenv("GEMINI_API_KEY"):
        st.warning("⚠️ GEMINI_API_KEY is not set in `.env`. The system is using the built-in intelligent taxonomy fallback engine.")

with right_col:
    if run_btn:
        has_input = bool(profile_text.strip() or file_bytes or audio_bytes or image_bytes)
        if not has_input:
            st.error("Please provide profile information via text, voice, document, or image.")
        else:
            with st.spinner("🤖 Running LangGraph Multi-Agent Pipeline..."):
                result = run_skill_gap_pipeline(
                    raw_text=profile_text,
                    file_bytes=file_bytes,
                    file_name=file_name,
                    audio_bytes=audio_bytes,
                    audio_mime_type=audio_mime_type,
                    image_bytes=image_bytes,
                    image_mime_type=image_mime_type,
                    selected_location=selected_location,
                    selected_interests=interests_text
                )

            if result.get("error"):
                st.error(result["error"])
            else:
                st.session_state["result"] = result

    if "result" in st.session_state:
        res = st.session_state["result"]
        profile = res.get("user_profile", {})
        matched_jobs = res.get("matched_jobs", [])
        gap_data = res.get("gap_analysis", {})
        rec_data = res.get("recommendations", {})

        top_score = matched_jobs[0]["match_score"] if matched_jobs else 0.0
        top_role = matched_jobs[0]["title"] if matched_jobs else "N/A"

        st.markdown(f"""
        <div class="hero-card">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
                <div>
                    <h3 style="margin:0; color:#0f172a; font-weight:800;">👤 {profile.get('name', 'Candidate')}</h3>
                    <p style="margin:0.2rem 0 0 0; color:#64748b; font-size:0.95rem;">
                        🎓 {profile.get('education', 'Education Not Specified')} · 📍 {profile.get('location', 'Any Location')}
                    </p>
                </div>
                <div style="text-align:right;">
                    <span style="font-size:0.8rem; color:#64748b; font-weight:600; text-transform:uppercase;">Top Match Readiness</span>
                    <div style="font-size:1.8rem; font-weight:800; color:{'#059669' if top_score >= 70 else '#d97706'};">{top_score}%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.markdown(f"""<div class="metric-box"><div class="metric-val">{profile.get('years_of_experience', 0)} yrs</div><div class="metric-lbl">Experience</div></div>""", unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"""<div class="metric-box"><div class="metric-val">{len(profile.get('skills', []))}</div><div class="metric-lbl">Skills Found</div></div>""", unsafe_allow_html=True)
        with m_col3:
            st.markdown(f"""<div class="metric-box"><div class="metric-val">{len(matched_jobs)}</div><div class="metric-lbl">Jobs Matched</div></div>""", unsafe_allow_html=True)
        with m_col4:
            st.markdown(f"""<div class="metric-box"><div class="metric-val">{len(rec_data.get('ranked_courses', []))}</div><div class="metric-lbl">ROI Courses</div></div>""", unsafe_allow_html=True)

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        tab_profile, tab_matches, tab_gaps, tab_training = st.tabs([
            "👤 Candidate Profile",
            "💼 Job Matches",
            "🔍 Skill Gap Analysis",
            "🚀 Training Roadmap"
        ])

        with tab_profile:
            st.markdown("#### 🛠️ Normalized Technical & Functional Skills")
            skills_list = profile.get("skills", [])
            if skills_list:
                chips_html = " ".join([f'<span class="badge-skill">✓ {s}</span>' for s in skills_list])
                st.markdown(f"<div style='margin-bottom:1rem;'>{chips_html}</div>", unsafe_allow_html=True)
            else:
                st.info("No specific technical skills extracted yet.")

            interests = profile.get("interests", [])
            if interests:
                st.markdown("#### 🎯 Career Aspirations")
                for item in interests:
                    st.markdown(f"- **{item}**")

        with tab_matches:
            st.markdown("#### 🏆 Ranked Job Opportunities")
            for idx, job in enumerate(matched_jobs[:5], 1):
                score = job.get("match_score", 0.0)
                score_color = "#10b981" if score >= 70 else ("#f59e0b" if score >= 50 else "#ef4444")

                with st.container():
                    st.markdown(f"""
                    <div class="job-card">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                            <div>
                                <span style="background:#f1f5f9; color:#475569; padding:2px 8px; border-radius:6px; font-size:0.75rem; font-weight:700;">#{idx} RANKED</span>
                                <h4 style="margin:0.3rem 0 0.1rem 0; color:#0f172a;">{job.get('title')}</h4>
                                <span style="color:#64748b; font-size:0.9rem; font-weight:500;">🏢 {job.get('company')} · 📍 {job.get('city')} · ⏳ {job.get('experience_level')}</span>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-size:1.6rem; font-weight:800; color:{score_color};">{score}%</div>
                                <span style="font-size:0.75rem; color:#64748b; font-weight:600;">MATCH SCORE</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.progress(min(1.0, score / 100.0))

            if len(matched_jobs) > 5:
                with st.expander("View All 10 Matched Jobs in Tabular View"):
                    df_jobs = pd.DataFrame([
                        {
                            "Rank": i,
                            "Role": j.get("title"),
                            "Company": j.get("company"),
                            "Location": j.get("city"),
                            "Score (%)": j.get("match_score"),
                            "Matched Required": ", ".join(j.get("matched_required", [])),
                            "Missing Required": ", ".join(j.get("missing_required", []))
                        }
                        for i, j in enumerate(matched_jobs, 1)
                    ])
                    st.dataframe(df_jobs, use_container_width=True, hide_index=True)

        with tab_gaps:
            st.markdown("#### 🔬 Detailed Missing Skills per Role")
            job_gaps = gap_data.get("job_gaps", [])

            for gap in job_gaps:
                score = gap.get("match_score", 0.0)
                with st.expander(f"{gap.get('title')} at {gap.get('company')} — {score}% Match", expanded=(score >= 60.0)):
                    st.info(f"💡 **AI Diagnostic:** {gap.get('explanation')}")

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown("**✅ Fully Matched**")
                        matched = gap.get("matched_required", []) + gap.get("matched_nice", [])
                        if matched:
                            chips = "".join([f'<span class="badge-matched">{s}</span>' for s in matched])
                            st.markdown(chips, unsafe_allow_html=True)
                        else:
                            st.caption("None")

                    with c2:
                        st.markdown("**⚠️ Partially Matched**")
                        partial = gap.get("partial_required", []) + gap.get("partial_nice", [])
                        if partial:
                            chips = "".join([f'<span class="badge-partial">{s}</span>' for s in partial])
                            st.markdown(chips, unsafe_allow_html=True)
                        else:
                            st.caption("None")

                    with c3:
                        st.markdown("**❌ Missing Required**")
                        missing = gap.get("missing_required", [])
                        if missing:
                            chips = "".join([f'<span class="badge-missing">{s}</span>' for s in missing])
                            st.markdown(chips, unsafe_allow_html=True)
                        else:
                            st.caption("No missing required skills!")

        with tab_training:
            st.markdown("#### 📈 Priority Training Roadmap")
            learning_order = rec_data.get("learning_order", [])
            ranked_courses = rec_data.get("ranked_courses", [])

            if learning_order:
                st.markdown("##### 🧭 Suggested Sequential Learning Path")
                for step in learning_order:
                    st.markdown(f"""
                    <div class="step-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:800; color:#1d4ed8; font-size:0.95rem;">MILESTONE {step['step']}: {step['course_name']}</span>
                            <span style="background:#f1f5f9; padding:2px 8px; border-radius:12px; font-size:0.8rem; font-weight:600; color:#475569;">⏱️ {step['duration_hours']} hrs · {step['platform']}</span>
                        </div>
                        <div style="margin-top:0.4rem; font-size:0.88rem; color:#334155;">
                            <b>Target Skills Closed:</b> {', '.join(step['skills_covered'])}
                        </div>
                        <div style="margin-top:0.2rem; font-size:0.85rem; color:#059669; font-weight:600;">
                            ✨ {step['impact_summary']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("---")
                st.markdown("##### 🎓 Recommended Courses with ROI Impact")

                for c in ranked_courses:
                    unlocked_count = c.get("num_unlocked", 0)
                    avg_gain = c.get("avg_gain", 0.0)

                    with st.container():
                        st.markdown(f"""
                        <div class="job-card">
                            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap;">
                                <div style="max-width:70%;">
                                    <h4 style="margin:0 0 0.3rem 0; color:#0f172a;">
                                        <a href="{c.get('url')}" target="_blank" style="text-decoration:none; color:#1d4ed8;">{c.get('course_name')} ↗</a>
                                    </h4>
                                    <span style="color:#64748b; font-size:0.85rem; font-weight:500;">
                                        🏛️ <b>{c.get('platform')}</b> · ⏱️ {c.get('duration_hours')} hrs · 💰 {c.get('cost')}
                                    </span>
                                </div>
                                <div style="text-align:right;">
                                    {f'<span class="roi-pill">🔥 Unlocks {unlocked_count} Jobs</span>' if unlocked_count > 0 else f'<span class="gain-pill">📈 +{avg_gain}% Match Gain</span>'}
                                </div>
                            </div>
                            <div style="margin-top:0.75rem; font-size:0.9rem; color:#1e293b; background:#f8fafc; padding:0.6rem 0.9rem; border-radius:8px;">
                                🎯 <b>ROI Analysis:</b> {c.get('roi_reason')}
                            </div>
                            <div style="margin-top:0.5rem; font-size:0.85rem;">
                                <b>Skills Taught:</b> {", ".join(c.get('skills_closed', []))}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        with st.expander("📊 View Projected Score Boost Across Target Roles"):
                            gain_rows = [
                                {
                                    "Role": sc.get("job_title"),
                                    "Company": sc.get("company"),
                                    "Before": f"{sc.get('score_before')}%",
                                    "After": f"{sc.get('score_after')}%",
                                    "Gain": f"+{sc.get('score_gain')}%"
                                }
                                for sc in c.get("score_comparisons", [])
                            ]
                            st.dataframe(pd.DataFrame(gain_rows), use_container_width=True, hide_index=True)
            else:
                st.info("No urgent training gaps identified for current profile matches.")
    else:
        st.markdown("""
        <div style="background:#f8fafc; border:2px dashed #cbd5e1; border-radius:16px; padding:3rem 2rem; text-align:center;">
            <div style="font-size:3rem; margin-bottom:1rem;">🚀</div>
            <h3 style="color:#1e293b; font-weight:700; margin-bottom:0.5rem;">Ready to Analyze Your Career Readiness</h3>
            <p style="color:#64748b; max-width:500px; margin:0 auto 1.5rem auto; font-size:0.95rem;">
                Select a quick demo profile on the left or provide your own via text, voice, PDF resume, or image scan. Then click <b>Analyze Skill Gaps & Match Jobs</b>.
            </p>
        </div>
        """, unsafe_allow_html=True)
