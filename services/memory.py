import os
import logging
from datetime import datetime

from supabase import create_client, Client

logger = logging.getLogger("finance_memory")

# In-memory stores (used as temporary cache, never silent authoritative store)
conversation_history: dict[str, list[dict]] = {}
last_finance_dataset: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# A5: Persistent Supabase-backed conversation session storage
# Stores session_id, last_dataset, created_at, conversation_id
# ---------------------------------------------------------------------------

_supabase_client: Client | None = None

def get_supabase() -> Client:
    """Retrieve or initialize Supabase client for authoritative session persistence."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment.")

    _supabase_client = create_client(url, key)
    return _supabase_client


async def persist_session(
    conversation_id: str,
    session_id: str,
    last_dataset: str | None = None
):
    """Persist or update a conversation session authoritatively in Supabase (A5)."""
    sb = get_supabase()
    record = {
        "conversation_id": conversation_id,
        "session_id": session_id,
        "last_dataset": last_dataset,
        "updated_at": datetime.utcnow().isoformat()
    }
    # Authoritative upsert on conversation_id
    sb.table("conversation_sessions").upsert(
        record, on_conflict="conversation_id"
    ).execute()


async def load_session(conversation_id: str) -> dict | None:
    """Load an authoritative persisted session for a conversation (A5)."""
    sb = get_supabase()
    result = (
        sb.table("conversation_sessions")
        .select("session_id, last_dataset, created_at")
        .eq("conversation_id", conversation_id)
        .limit(1)
        .execute()
    )
    if result.data and len(result.data) > 0:
        return result.data[0]
    return None


def get_bounded_conversation_context(conversation_id: str, max_messages: int = 3) -> str:
    """
    T7: Bounded Conversation Context Strategy (Strict Maximum 3 Previous Messages).
    
    Rules:
    - Include at most the 3 most recent previous messages (0–3 retains all; 4+ retains only last 3).
    - The current user message is NOT counted in the 3.
    - Prevents unbounded token growth across long multi-turn sessions.
    - Preserves follow-up resolution (pronouns, 'that vendor', 'this quarter').
    """
    history = conversation_history.get(conversation_id, [])
    if not history:
        return ""

    # Strictly cap to the last max_messages (3) previous entries
    recent_entries = history[-max_messages:]

    history_lines = []
    for item in recent_entries:
        role = "User" if item.get("role") == "user" else "Assistant"
        content = str(item.get("content", "")).strip()
        if len(content) > 300:
            content = content[:300] + "..."
        history_lines.append(f"{role}: {content}")

    if not history_lines:
        return ""

    return (
        "\n[Recent Conversation Context (Last 3 Previous Messages Only)]:\n"
        + "\n".join(history_lines)
        + "\n[End of Recent Context — Follow-up References Apply to Above]\n"
    )

