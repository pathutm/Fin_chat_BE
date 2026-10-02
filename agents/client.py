from anthropic import Anthropic, AsyncAnthropic
from core.config import ANTHROPIC_API_KEY

# Synchronous client — used ONLY for agent/session creation (setup operations)
client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Async client — used for all FastAPI request-path operations (A2)
async_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
