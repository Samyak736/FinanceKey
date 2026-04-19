import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "data" / "copilot.db"))

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "pytsk-proj-jZZTevgc_SnTXYiQZ_1G_Okfitycrz90zp_PuETCoUEVBSVssui_8ISb4I4d6bzDzoNsbpOcdnT3BlbkFJhgwOQbsKO57P2AzcX8QXtIWQrElWbDesAUsG-NgVx8escmn6he7R-CSKPjU1O3sHuh-Cawh5oA")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyB0NLcyLnEllYyh1VVVrhfDObbydmYYt3M")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").lower()

DEFAULT_USER_ID = 1
