from anthropic import AsyncAnthropic
from core.config import ANTHROPIC_API_KEY

# Async client — used for all FastAPI request-path operations (A2).
# Agent creation is not done in code; see agents/setup.py.
async_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
