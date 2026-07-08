"""Load contracts/digest-main.json — shared rules for generate + validate."""
from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "digest-main.json"


@lru_cache(maxsize=1)
def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text())


def validate_main_rules() -> list[tuple[str, str, int]]:
    """(desc, pattern, expected) scoped to <main> unless scope is html."""
    rules: list[tuple[str, str, int]] = []
    for row in load_contract()["validate"]["main"]:
        rules.append((row["desc"], row["pattern"], int(row["expected"])))
    return rules


def validate_html_only_descs() -> set[str]:
    return {row["desc"] for row in load_contract()["validate"]["main"] if row.get("scope") == "html"}


def validate_static_rules() -> list[tuple[str, str, int, str]]:
    """(desc, pattern, expected, scope_kind) where scope_kind is js or html."""
    rules: list[tuple[str, str, int, str]] = []
    for row in load_contract()["validate"]["static"]:
        rules.append((row["desc"], row["pattern"], int(row["expected"]), row["scope"]))
    return rules


def build_system_prompt() -> str:
    c = load_contract()
    site = c["site"]["url"]
    voice = c["voice"]
    gen = c["generate"]

    style = " ".join(voice["style"])
    structural = "\n".join(f"- {line}" for line in gen["structuralRules"])
    content = "\n".join(f"- {line}" for line in gen["contentRules"])

    return f"""You are generating Wesley's daily market digest for {site}.

{voice["audience"]} {style}

{gen["intro"]}

{gen["output"]}

STRUCTURAL RULES (the static template's JS breaks if these drift):
{structural}

CONTENT (synthesized from the sources):
{content}"""


def check_contract() -> list[str]:
    """Sanity-check contract JSON; return list of error strings."""
    errors: list[str] = []
    c = load_contract()

    for section in ("main", "static"):
        for row in c["validate"].get(section, []):
            pat = row.get("pattern", "")
            try:
                re.compile(pat, re.DOTALL | re.I)
            except re.error as exc:
                errors.append(f"validate.{section}.{row.get('id')}: bad regex: {exc}")

    gen = c.get("generate", {})
    if not gen.get("structuralRules"):
        errors.append("generate.structuralRules is empty")
    if not gen.get("contentRules"):
        errors.append("generate.contentRules is empty")

    return errors


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        errors = check_contract()
        if errors:
            for err in errors:
                print(f"FAIL {err}")
            return 1
        n_main = len(load_contract()["validate"]["main"])
        n_static = len(load_contract()["validate"]["static"])
        print(f"OK contract v{load_contract()['version']}: {n_main} main + {n_static} static checks")
        return 0

    print(build_system_prompt())
    return 0


if __name__ == "__main__":
    sys.exit(main())
