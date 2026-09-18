from pathlib import Path

SKILLS_DIR = Path(__file__).parent / "skills"


def load_skill(skill_name: str) -> str:
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"

    if not skill_path.exists():
        raise FileNotFoundError(
            f"Skill file not found: {skill_path}"
        )

    with open(skill_path, "r", encoding="utf-8") as file:
        return file.read()


FINANCE_RESPONSE_SKILL = load_skill("finance_response")

FINANCIAL_FORMULAS_SKILL = load_skill("financial_formulas")

FINANCIAL_RATIOS_SKILL = load_skill("financial_ratios")

INVENTORY_COSTING_SKILL = load_skill("inventory_costing")

PROCUREMENT_RECONCILIATION_SKILL = load_skill(
    "procurement_reconciliation"
)


FINANCE_SKILLS = (
    "\nFINANCE RESPONSE SKILL\n"
    + FINANCE_RESPONSE_SKILL
    + "\nFINANCIAL FORMULAS SKILL\n"
    + FINANCIAL_FORMULAS_SKILL
    + "\nFINANCIAL RATIOS SKILL\n"
    + FINANCIAL_RATIOS_SKILL
    + "\nINVENTORY COSTING SKILL\n"
    + INVENTORY_COSTING_SKILL
    + "\nPROCUREMENT RECONCILIATION SKILL\n"
    + PROCUREMENT_RECONCILIATION_SKILL
)