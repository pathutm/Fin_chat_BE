import os
from pathlib import Path
import re
from agents.client import client

SKILLS_DIR = Path(__file__).resolve().parent / "skills"

def parse_skill_metadata(content: str) -> dict:
    """Extract YAML frontmatter metadata from SKILL.md content."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}
    meta = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta

def load_all_skill_metadata() -> dict:
    """Load lightweight metadata (name, description) for all available skills."""
    if not SKILLS_DIR.exists():
        raise FileNotFoundError(f"Skills directory not found: {SKILLS_DIR}")

    skills_meta = {}
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        content = skill_file.read_text(encoding="utf-8")
        meta = parse_skill_metadata(content)
        skills_meta[skill_dir.name] = {
            "name": meta.get("name", skill_dir.name),
            "description": meta.get("description", ""),
            "path": skill_file,
        }
    return skills_meta

def get_or_register_custom_skills() -> list:
    """
    Return the custom skill parameter references for the Finance Agent.
    Loads skill metadata locally without making network calls on module import (A1).
    """
    skill_meta = load_all_skill_metadata()
    custom_skills = []
    for dir_name, info in skill_meta.items():
        # Look for configured skill ID from env or use standardized name reference
        env_key = f"SKILL_{dir_name.upper()}_ID"
        skill_id = os.getenv(env_key, f"skill_{dir_name}")
        custom_skills.append({
            "type": "custom",
            "skill_id": skill_id,
        })
    return custom_skills

import os
FINANCE_CUSTOM_SKILLS = get_or_register_custom_skills()