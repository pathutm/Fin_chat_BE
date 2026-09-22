from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent / "skills"

def load_all_skills():
    skills = {}

    if not SKILLS_DIR.exists():
        raise FileNotFoundError(
            f"Skills directory not found: {SKILLS_DIR}"
        )

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_file = skill_dir / "SKILL.md"

        if not skill_file.exists():
            continue

        skills[skill_dir.name] = skill_file.read_text(
            encoding="utf-8"
        )

    return skills

SKILLS = load_all_skills()

FINANCE_SKILLS = "\n\n".join(
    f"{skill_name.upper()} SKILL\n\n{skill_content}"
    for skill_name, skill_content in SKILLS.items()
)