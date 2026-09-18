import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_ENVIRONMENT_ID = os.getenv("ANTHROPIC_ENVIRONMENT_ID")
SUPABASE_PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF")
SUPABASE_ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")


if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY is missing")

if not ANTHROPIC_ENVIRONMENT_ID:
    raise ValueError("ANTHROPIC_ENVIRONMENT_ID is missing")

if not SUPABASE_PROJECT_REF:
    raise ValueError("SUPABASE_PROJECT_REF is missing")

if not SUPABASE_ACCESS_TOKEN:
    raise ValueError("SUPABASE_ACCESS_TOKEN is missing")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is not set in the .env file")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_SERVICE_ROLE_KEY is not set in the .env file")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in the .env file")
