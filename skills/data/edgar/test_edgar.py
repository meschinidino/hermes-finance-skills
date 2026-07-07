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


def test_extracts_mrna_real_sec_fixture_with_raw_usd_scale() -> None:
    facts = fetch_edgar_facts("MRNA")

    assert resolve_cik("MRNA") == "0001682852"
    assert facts.cik == "0001682852"
    assert facts.years == ["FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]
    assert facts.facts.revenue[-1].value == 1944
    assert facts.facts.revenue[-1].provenance.accession == "0001682852-26-000033"
    assert facts.facts.ebit[-1].value == -3074
    assert facts.facts.ebit[-1].provenance.accession == "0001682852-26-000033"
    assert "revenue_fallback:mixed:us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax,us-gaap:Revenues" in facts.flags


def test_extracts_uber_service_platform_fixture_with_non_reported_inventory_marker() -> None:
    facts = fetch_edgar_facts("UBER")

    assert resolve_cik("UBER") == "0001543151"
    assert facts.cik == "0001543151"
    assert facts.years == ["FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]
    assert facts.facts.revenue[-1].value == 52017
    assert (
        facts.facts.cost_of_revenue[-1].provenance.tag
        == "us-gaap:CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization"
    )
    assert facts.facts.inventory[-1].value == 0
    assert facts.facts.inventory[-1].provenance.tag == "us-gaap:InventoryNet:not_reported_by_issuer"
    assert facts.facts.inventory[-1].provenance.accession == "not_reported_by_issuer"
    assert "inventory_not_reported_by_issuer" in facts.flags


def test_extracts_crm_saas_fixture_with_raw_usd_scale() -> None:
    facts = fetch_edgar_facts("CRM")

    assert resolve_cik("CRM") == "0001108524"
    assert facts.cik == "0001108524"
    assert facts.years == ["FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]
    assert facts.facts.revenue[-1].value == 41525
    assert facts.facts.revenue[-1].provenance.accession == "0001108524-26-000060"
    assert facts.facts.ebit[-1].value == 8331
    assert facts.facts.ebit[-1].provenance.accession == "0001108524-26-000060"
    assert facts.facts.shares_outstanding[-1].value == 923
    assert "inventory_not_reported_by_issuer" in facts.flags


def test_missing_required_concept_fails_closed(tmp_path: Path) -> None:
    fixture_dir = _copy_fixtures(tmp_path)
    facts_path = fixture_dir / "aapl_companyfacts.json"
    raw = json.loads(facts_path.read_text(encoding="utf-8"))
    del raw["facts"]["us-gaap"]["CashAndCashEquivalentsAtCarryingValue"]
    facts_path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="unresolved_concept:cash"):
        fetch_edgar_facts("AAPL", fixture_dir=fixture_dir)


def test_missing_required_screen_concept_fails_closed(tmp_path: Path) -> None:
    fixture_dir = _copy_fixtures(tmp_path)
    facts_path = fixture_dir / "aapl_companyfacts.json"
    raw = json.loads(facts_path.read_text(encoding="utf-8"))
    del raw["facts"]["us-gaap"]["AccountsReceivableNetCurrent"]
    facts_path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="unresolved_concept:receivables"):
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
