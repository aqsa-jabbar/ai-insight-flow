"""
config.py
---------
Centralizes environment variables and tunable constants so tools.py (and
anything else) can just do `import config` instead of scattering
os.getenv() calls everywhere.

Locally, these values come from your .env file (loaded via python-dotenv).
On Hugging Face Spaces, they come from Repository Secrets instead - the
os.getenv() calls below work identically in both cases.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- API keys ---
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- Serper search settings ---
SERPER_URL = "https://google.serper.dev/search"
SERPER_MAX_RESULTS = 5          # how many search results to feed the agent

# --- Scraper settings ---
MAX_SCRAPE_CHARS = 6000         # cap so we don't blow past the LLM context window

# --- Shared ---
REQUEST_TIMEOUT_SECONDS = 15