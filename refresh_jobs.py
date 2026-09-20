import os
import json
import shutil
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from app.config import JOBS_FILE
from app.live_jobs import fetch_live_jobs, save_jobs

PARTIAL_SAVE_EVERY = 15
_partial_jobs = []


def backup_existing(jobs_path):
    if not os.path.exists(jobs_path):
        return
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{jobs_path}.backup_{stamp}.json"
    shutil.copy(jobs_path, backup_path)
    print(f"Backed up old jobs file to {backup_path}")


def make_progress_callback(jobs_path):
    def callback(done, total, kept):
        print(f"  [{done}/{total}] postings processed, {kept} kept so far")
    return callback


def main():
    print("Fetching live job postings from Adzuna (India) and extracting skills with Gemini...")
    print("This can take a while since each posting is read individually by the LLM.")

    jobs = fetch_live_jobs(progress_callback=make_progress_callback(JOBS_FILE))
    print(f"Done. Fetched {len(jobs)} jobs with skills extracted from their real posting text.")

    if not jobs:
        print("No jobs fetched. Keeping the existing jobs.json unchanged.")
        return

    backup_existing(JOBS_FILE)
    save_jobs(jobs, JOBS_FILE)
    print(f"Saved {len(jobs)} live jobs to {JOBS_FILE}")
    print("Restart the Streamlit app to use the refreshed data.")


if __name__ == "__main__":
    main()