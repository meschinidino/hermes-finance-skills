from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from skills.data.edgar.edgar import fetch_edgar_facts, resolve_cik

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_resolves_aapl_cik() -> None:
    assert resolve_cik("AAPL") == "0000320193"


def test_extracts_required_facts_with_provenance() -> None:
    facts = fetch_edgar_facts("AAPL")

    assert facts.cik == "0000320193"
    assert len(facts.years) == 5
    assert facts.facts.revenue[0].provenance.accession == "0000320193-20-000096"
    assert facts.facts.ebit[-1].value == 123216
    assert facts.facts.shares_outstanding[-1].unit == "shares"
    assert "goodwill_explicit_zero" in facts.flags


def test_missing_required_concept_fails_closed(tmp_path: Path) -> None:
    fixture_dir = _copy_fixtures(tmp_path)
    facts_path = fixture_dir / "aapl_companyfacts.json"
    raw = json.loads(facts_path.read_text(encoding="utf-8"))
    del raw["facts"]["us-gaap"]["CashAndCashEquivalentsAtCarryingValue"]
    facts_path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="unresolved_concept:cash"):
        fetch_edgar_facts("AAPL", fixture_dir=fixture_dir)


def test_less_than_five_annual_periods_fails_closed(tmp_path: Path) -> None:
    fixture_dir = _copy_fixtures(tmp_path)
    facts_path = fixture_dir / "aapl_companyfacts.json"
    raw = json.loads(facts_path.read_text(encoding="utf-8"))
    raw["facts"]["us-gaap"]["OperatingIncomeLoss"]["units"]["USD"] = raw["facts"]["us-gaap"]["OperatingIncomeLoss"]["units"]["USD"][-4:]
    facts_path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="insufficient_history"):
        fetch_edgar_facts("AAPL", fixture_dir=fixture_dir)


def _copy_fixtures(tmp_path: Path) -> Path:
    fixture_dir = tmp_path / "fixtures"
    shutil.copytree(FIXTURE_DIR, fixture_dir)
    return fixture_dir
