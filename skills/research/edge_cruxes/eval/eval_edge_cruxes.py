from pathlib import Path

from skills.bundle_validation import validate_skill_bundle


def test_edge_cruxes_bundle_shape() -> None:
    validate_skill_bundle(Path("skills/research/edge_cruxes"), expected_role="analyst")
