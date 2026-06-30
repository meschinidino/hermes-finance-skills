from __future__ import annotations

import re
from pathlib import Path
from typing import Literal


class BundleValidationError(ValueError):
    pass


Role = Literal["accountant", "analyst"]


def validate_skill_bundle(path: Path | str, *, expected_role: Role | None = None) -> None:
    bundle_path = Path(path)
    metadata = _read_skill_metadata(bundle_path)
    role = metadata.get("type")
    if role not in {"accountant", "analyst"}:
        raise BundleValidationError("skill bundle must declare type: accountant | analyst")
    if expected_role and role != expected_role:
        raise BundleValidationError(f"expected {expected_role} bundle, got {role}")

    no_llm = _parse_bool(metadata.get("no_llm"), field_name="no_llm")
    llm_dependency = _parse_bool(metadata.get("llm_dependency", "false"), field_name="llm_dependency")
    output_contract = metadata.get("output_contract", metadata.get("outputs", ""))

    _require_file(bundle_path / "SKILL.md")
    _require_file(bundle_path / "resolver.entry")

    implementation_name = metadata.get("implementation")
    implementation_path = bundle_path / implementation_name if implementation_name else _default_implementation(bundle_path)
    _require_file(implementation_path)

    if role == "accountant":
        if not no_llm:
            raise BundleValidationError("accountant bundle must declare no_llm: true")
        if llm_dependency:
            raise BundleValidationError("accountant bundle must not declare an LLM dependency")
        return

    if no_llm:
        raise BundleValidationError("analyst bundle must declare no_llm: false")
    if not llm_dependency:
        raise BundleValidationError("analyst bundle must declare an LLM dependency")
    if not _declares_ratifiable_output(output_contract):
        raise BundleValidationError("analyst bundle must declare a ratifiable draft output contract")
    _require_file(bundle_path / "prompt.md")
    _require_file(bundle_path / "eval" / "cases.jsonl")
    if not list((bundle_path / "eval").glob("eval_*.py")):
        raise BundleValidationError("analyst bundle requires eval runner")


def _read_skill_metadata(bundle_path: Path) -> dict[str, str]:
    skill_path = bundle_path / "SKILL.md"
    _require_file(skill_path)
    metadata: dict[str, str] = {}
    for line in skill_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*(?:#.*)?$", line)
        if match:
            metadata[match.group(1)] = match.group(2).strip()
    return metadata


def _parse_bool(value: str | None, *, field_name: str) -> bool:
    normalized = (value or "").strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise BundleValidationError(f"{field_name} must be true or false")


def _declares_ratifiable_output(output_contract: str) -> bool:
    normalized = output_contract.lower()
    return "analystdraft" in normalized or "needs_ratification" in normalized


def _require_file(path: Path) -> None:
    if not path.is_file():
        raise BundleValidationError(f"required bundle file missing: {path.name}")


def _default_implementation(bundle_path: Path) -> Path:
    return bundle_path / f"{bundle_path.name}.py"
