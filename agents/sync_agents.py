"""
Push changes in agents/*.md to the existing Managed Agents (same IDs, new versions).

Run from Fin_chat_BE:
    python agents/sync_agents.py            # dry run: show what would change
    python agents/sync_agents.py --apply    # push the changes to Anthropic
    python agents/sync_agents.py --apply --all   # push every agent, changed or not

Reads the agent IDs and API key from .env. Only updates agent configuration -
no sessions and no model calls, so it uses no tokens. Existing chat sessions keep
the version they started with; new chats use the new version.

Not synced: skill files in agents/skills/ (uploaded once when the agents were created).
"""
import argparse
import pathlib
import re
import sys

import anthropic
import yaml
from dotenv import dotenv_values

BE = pathlib.Path(__file__).resolve().parent.parent

# Coordinator last: it is pinned to specific versions of the other two
AGENTS = (
    ("finance", "FINANCE_AGENT_ID"),
    ("general", "GENERAL_AGENT_ID"),
    ("coordinator", "COORDINATION_AGENT_ID"),
)


def read_agent_file(name: str) -> tuple[dict, str]:
    """Frontmatter = agent config, Markdown body = system prompt."""
    text = (BE / "agents" / f"{name}.md").read_text()
    front, body = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S).groups()
    return yaml.safe_load(front), body.strip() + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="push the changes (default: dry run)")
    parser.add_argument("--all", action="store_true", help="push every agent even if nothing changed")
    args = parser.parse_args()

    env = dotenv_values(BE / ".env")
    missing = [key for key in ("ANTHROPIC_API_KEY",) + tuple(k for _, k in AGENTS) if not env.get(key)]
    if missing:
        sys.exit("Missing in .env: " + ", ".join(missing))

    client = anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"])
    versions = {}

    for name, env_key in AGENTS:
        cfg, system = read_agent_file(name)
        live = client.beta.agents.retrieve(env[env_key])

        changes = {}
        if args.all or (live.system or "").strip() != system.strip():
            changes["system"] = system
        if args.all or (live.description or "") != (cfg.get("description") or ""):
            changes["description"] = cfg.get("description")
        if args.all or getattr(live.model, "id", live.model) != cfg["model"]:
            changes["model"] = cfg["model"]
        if changes and "tools" in cfg:
            # Tools are sent along with any other change to the agent
            changes["tools"] = cfg["tools"]

        if name == "coordinator":
            pinned = {a.id: a.version for a in live.multiagent.agents} if live.multiagent else {}
            wanted = {
                env["FINANCE_AGENT_ID"]: versions["finance"],
                env["GENERAL_AGENT_ID"]: versions["general"],
            }
            if args.all or pinned != wanted:
                changes["multiagent"] = {
                    "type": "coordinator",
                    "agents": [{"type": "agent", "id": agent_id, "version": version}
                               for agent_id, version in wanted.items()],
                }

        if not changes:
            print(f"{cfg['name']:<20} v{live.version}  up to date")
            versions[name] = live.version
            continue

        print(f"{cfg['name']:<20} v{live.version}  changed: {', '.join(changes)}")
        if args.apply:
            updated = client.beta.agents.update(live.id, version=live.version, **changes)
            print(f"{'':<20} -> now v{updated.version}")
            versions[name] = updated.version
        else:
            # Dry run: the coordinator would be re-pinned to the next version
            versions[name] = live.version + 1

    if not args.apply:
        print("\nDry run - nothing was changed. Run again with --apply to push.")


if __name__ == "__main__":
    main()
