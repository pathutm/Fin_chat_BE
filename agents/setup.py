import json
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# A1: The agents are defined as files and created/updated with:
#
#     ant apply agents/coordinator.md
#
# coordinator.md lists finance.md and general.md in its multiagent roster, so
# one apply syncs all three (and uploads agents/skills/* for the Finance Agent).
# Each change creates a new agent version; IDs are recorded in claude-lock.json.
# Runtime code only reads the stored IDs - it never calls agents.create().
# ---------------------------------------------------------------------------

MODEL = "claude-haiku-4-5-20251001"

BASE_DIR = Path(__file__).resolve().parent.parent
LOCK_FILE = BASE_DIR / "claude-lock.json"


def _agent_id_from_lock_file(agent_file: str) -> str | None:
    if not LOCK_FILE.exists():
        return None
    try:
        resources = json.loads(LOCK_FILE.read_text()).get("resources", {})
    except (OSError, ValueError):
        return None
    entry = resources.get(f"./agents/{agent_file}") or resources.get(f"agents/{agent_file}")
    return entry.get("id") if isinstance(entry, dict) else None


class _AgentRef:
    def __init__(self, env_key: str, agent_file: str, name: str):
        # .env wins so an environment can pin a specific agent; otherwise claude-lock.json
        self.id = os.getenv(env_key) or _agent_id_from_lock_file(agent_file)
        self.name = name


coordination_agent = _AgentRef("COORDINATION_AGENT_ID", "coordinator.md", "Coordination Agent")
finance_agent = _AgentRef("FINANCE_AGENT_ID", "finance.md", "Finance Agent")
general_agent = _AgentRef("GENERAL_AGENT_ID", "general.md", "General Agent")

AGENTS_BY_NAME = {a.name: a for a in (coordination_agent, finance_agent, general_agent)}

if not coordination_agent.id:
    print(
        "[Agent Setup] [WARN] No Coordination Agent ID found. Run `ant apply agents/coordinator.md` "
        "from Fin_chat_BE (writes claude-lock.json) or set COORDINATION_AGENT_ID in .env."
    )
