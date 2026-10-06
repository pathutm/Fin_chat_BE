import asyncio
import os
import logging
import re
from datetime import datetime, timezone

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
    record = {
        "conversation_id": conversation_id,
        "session_id": session_id,
        "last_dataset": last_dataset,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    def _upsert():
        get_supabase().table("conversation_sessions").upsert(
            record, on_conflict="conversation_id"
        ).execute()

    # supabase-py is synchronous - run it off the event loop (A2)
    try:
        await asyncio.to_thread(_upsert)
    except Exception as e:
        # Best-effort: the chat still answers; the next message opens a new session
        print(f"[Session Store] [WARN] Could not save session: {e}")


async def load_session(conversation_id: str) -> dict | None:
    """Load an authoritative persisted session for a conversation (A5)."""
    def _select():
        return (
            get_supabase().table("conversation_sessions")
            .select("session_id, last_dataset, created_at, updated_at")
            .eq("conversation_id", conversation_id)
            .limit(1)
            .execute()
        )

    try:
        result = await asyncio.to_thread(_select)
    except Exception as e:
        # Best-effort: without a stored session the chat creates a new one
        print(f"[Session Store] [WARN] Could not load session: {e}")
        return None
    if not (result.data and len(result.data) > 0):
        return None

    record = result.data[0]
    # Restore the cached dataset after a server restart (T10)
    if record.get("last_dataset") and conversation_id not in last_finance_dataset:
        last_finance_dataset[conversation_id] = {"tool_result": record["last_dataset"]}
    return record


# ---------------------------------------------------------------------------
# T10: Visualization follow-ups ("chart this", "show it as a graph") are answered
# from the cached dataset with no model call.
# ---------------------------------------------------------------------------

_VIZ_WORDS = re.compile(
    r"(?i)\b(visuali[sz](e|ed|ing|ation)|charts?|graphs?|plot(ted|ting)?|diagram)\b"
)
_VIZ_REFERENCE = re.compile(
    r"(?i)\b(this|that|it|these|those|the\s+(data|result|results|above|same)|above|dataset)\b"
)


def is_visualization_followup(question: str, conversation_id: str | None) -> bool:
    """True when the user asks to chart the previous result and a dataset is cached."""
    if not question or not conversation_id or conversation_id not in last_finance_dataset:
        return False
    if not _VIZ_WORDS.search(question):
        return False
    words = question.strip().split()
    return bool(_VIZ_REFERENCE.search(question)) or len(words) <= 4


def get_bounded_conversation_context(conversation_id: str, max_messages: int = 3) -> str:
    """
    T7: Bounded Conversation Context Strategy (Strict Maximum 3 Previous Messages).

    Only used when a conversation has to start a NEW Managed Agents session
    (first message after a restart or an expired session). A reused session
    already holds the full history, with platform caching and compaction.
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


def remember_turn(conversation_id: str, question: str, answer: str, max_entries: int = 20):
    """Append a turn to the in-memory history, keeping it bounded (A5)."""
    history = conversation_history.setdefault(conversation_id, [])
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})
    del history[:-max_entries]
