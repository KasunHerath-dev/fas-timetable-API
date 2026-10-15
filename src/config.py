"""Configuration settings and defaults for timetable downloader."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root .env if present
load_dotenv()

DEFAULT_BASE_URL = "https://fas.wyb.ac.lk/timetables/"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Relative to current working directory or absolute
DEFAULT_DOWNLOADS_DIR = Path("downloads")
DEFAULT_MANIFEST_PATH = Path("metadata/manifest.json")
DEFAULT_PARSED_DIR = Path("data/parsed")
DEFAULT_MAX_PAGES = 5
REQUEST_TIMEOUT = 30

# MongoDB Configuration Defaults
DEFAULT_MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "fas_timetable")
DEFAULT_MONGODB_COLLECTION = "timetables"
DEFAULT_SESSIONS_COLLECTION = "timetable_sessions"
MONGODB_TIMEOUT_MS = 5000
