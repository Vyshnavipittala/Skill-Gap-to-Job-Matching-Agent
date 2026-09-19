import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

JOBS_FILE = os.path.join(DATA_DIR, "jobs.json")
COURSES_FILE = os.path.join(DATA_DIR, "courses.json")
TAXONOMY_FILE = os.path.join(DATA_DIR, "skills_taxonomy.json")

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.65
PARTIAL_THRESHOLD = 0.45
REQUIRED_WEIGHT = 0.80
NICE_TO_HAVE_WEIGHT = 0.20
STRONG_MATCH_THRESHOLD = 70.0
GEMINI_MODEL_NAME = "gemini-3.8-flash"

