from pathlib import Path

from skills.bundle_validation import validate_skill_bundle


def test_scenarios_bundle_shape() -> None:
    validate_skill_bundle(Path(__file__).parents[1], expected_role="analyst")
