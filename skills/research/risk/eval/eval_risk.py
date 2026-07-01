from pathlib import Path

from skills.bundle_validation import validate_skill_bundle


def test_risk_bundle_shape() -> None:
    validate_skill_bundle(Path("skills/research/risk"), expected_role="analyst")
