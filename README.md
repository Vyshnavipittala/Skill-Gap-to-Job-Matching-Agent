# Skill-Gap-to-Job Matching Agent

An intelligent, multi-agent AI system built with **LangGraph**, **Sentence-Transformers**, and the **Gemini API** that evaluates job seeker profiles, matches them against local job opportunities, pinpoints precise skill gaps, and formulates an ROI-ranked training path.

---

> [!NOTE]
> **SAMPLE DATA NOTICE**: The postings in `data/jobs.json` are curated realistic sample postings across software, data, embedded/IoT, electronics, mechanical, business, and design across major Indian cities (Bengaluru, Hyderabad, Pune, Mumbai, Chennai, Delhi NCR). You can easily replace `data/jobs.json` with your own real postings as long as the JSON schema (`id`, `title`, `company`, `city`, `required_skills`, `nice_to_have_skills`, `education`, `experience_level`) is preserved.

---

## Key Features

1. **Profile Parsing Agent**:
   - Accepts free text, pasted resumes, or uploaded PDF/TXT files.
   - Leverages Gemini LLM to extract candidate metadata: Name, Education, Skills, Years of Experience, Location, and Career Interests.
   - Normalizes skills using a comprehensive synonym dictionary (`data/skills_taxonomy.json`) (e.g. `JS` -> `JavaScript`, `ML` -> `Machine Learning`, `K8s` -> `Kubernetes`).

2. **Job Matching Agent**:
   - Uses `sentence-transformers` (`all-MiniLM-L6-v2`) to embed candidate skills and job requirements.
   - Computes cosine similarity matching:
     - Similarity threshold >= 0.65 counts as a match.
     - Weighted scoring: **80% for required skills**, **20% for nice-to-have skills** (Score: 0 to 100).
   - Filters by user's location with an "Any Location" option.
   - Returns the Top 10 matching jobs.

3. **Gap Analysis Agent**:
   - For every top job, precisely categorizes skills into:
     - **Matched** (>= 0.65)
     - **Partially Matched** (0.45 <= score < 0.65)
     - **Missing Required** (< 0.45)
   - Uses Gemini LLM to generate concise, strictly factual 2-3 sentence assessments per job based solely on computed data.

4. **Training Recommendation & ROI Ranking Agent**:
   - Maps missing skills to 40+ verified courses from **NPTEL**, **Coursera**, and **Skill India Digital Hub** (`data/courses.json`).
   - Simulates skill acquisition and calculates the **Opportunity Unlocked**:
     - Number of top jobs that cross into strong match status (score > 70%).
     - Average match score gain across top jobs.
   - Ranks courses by unlocked jobs, score gain, and duration.
   - Generates a 1-line ROI justification per course and a recommended sequential learning roadmap.

5. **Streamlit Interactive UI**:
   - 2-column dashboard: profile input & resume upload on the left, tabbed results on the right.
   - Four dedicated tabs: **Parsed Profile**, **Job Matches**, **Gap Analysis**, and **Training Path**.

---

## Project Structure

```
skillGapChatbot/
├── app/
│   ├── config.py           # Central configuration constants and thresholds
│   ├── llm.py              # Centralized Gemini API calls and offline fallback
│   ├── profile_agent.py    # Profile parsing and skill taxonomy normalization
│   ├── matcher.py          # Embedding-based job matching and scoring
│   ├── gap_agent.py        # Gap analysis and LLM explanation generation
│   ├── recommender.py      # Course matching, score simulation, and ROI ranking
│   └── graph.py            # LangGraph state machine orchestrator
├── data/
│   ├── jobs.json           # 40 sample job postings across fields and cities
│   ├── courses.json        # 41 verified courses (Coursera, NPTEL, Skill India)
│   └── skills_taxonomy.json # 150+ synonym mappings for skill normalization
├── tests/
│   ├── test_profiles.json  # 10 benchmark candidate profiles with ground truth
│   ├── evaluate.py         # Accuracy, Top-3 hit rate, and course coverage checks
│   └── test_pipeline.py    # End-to-end LangGraph pipeline integration test
├── main.py                 # Streamlit web application
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment variables template
└── README.md               # Documentation and usage guide
```

---

## Setup and Installation

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.11)
- Git (optional)

### 2. Clone or Navigate to Directory
```bash
cd skillGapChatbot
```

### 3. Create and Activate Virtual Environment
Using standard Python `venv`:
```bash
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate
```

Or using `uv`:
```bash
uv venv .venv --python 3.11
.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure API Key
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Open `.env` and add your Google Gemini API key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```
*(Note: If no API key is provided, the agent will seamlessly use built-in keyword-and-taxonomy extraction and template-based factual gap summaries).*

---

## Running the Application

Launch the Streamlit web dashboard:
```bash
streamlit run main.py
```
Open your browser at `http://localhost:8501`.

---

## Running the Tests and Evaluation Suite

### 1. Run the Evaluation Benchmark
Measures direct skill-matching accuracy, Top-3 job recommendation hit rate across 10 distinct domains, and semantic integrity of course skill coverage:
```bash
python tests/evaluate.py
```

### 2. Run the End-to-End Pipeline Integration Test
Verifies the full LangGraph pipeline from raw text input through all 4 agents:
```bash
python tests/test_pipeline.py
```

