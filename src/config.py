"""
Central configuration. Loads secrets from environment (.env) so no keys are
ever hardcoded into source. Every value here has a safe default so the
pipeline still runs (at reduced rate limits / fewer sources) with zero
configuration — required for the "fully accessible without login" deployment
constraint downstream.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# --- API credentials (all optional; extractors degrade gracefully) ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()

# --- Networking ---
REQUEST_TIMEOUT = 15
USER_AGENT = "ai-orbit-ingestion-pipeline/1.0 (+github.com/graphone-trial)"
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2.0

# --- Data scope targets (spec section 3) ---
TARGET_TOTAL_RECORDS_MIN = 250
TARGET_TOTAL_RECORDS_MAX = 300

# --- Output files ---
ENTITIES_JSON = DATA_DIR / "entities.json"
RELATIONSHIPS_JSON = DATA_DIR / "relationships.json"
PIPELINE_LOG = DATA_DIR / "pipeline.log"
RUN_REPORT_JSON = DATA_DIR / "run_report.json"
