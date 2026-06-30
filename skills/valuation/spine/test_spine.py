from __future__ import annotations

import pytest

from skills.audit import AuditError, audit_m1_handoff
from skills.config import load_config
from skills.data.cost_of_capital.cost_of_capital import build_cost_of_capital_inputs
from skills.data.edgar.edgar import fetch_edgar_facts
from skills.data.price.price import fetch_price
from skills.synthesis.handoff.handoff import build_handoff
from skills.valuation.normalize.normalize import normalize_financials
from skills.valuation.spine.spine import build_spine


def _spine(price_feed=None):
    config = load_config("config/conventions.yaml")
    edgar = fetch_edgar_facts("AAPL")
    normalized = normalize_financials(edgar)
    coc = build_cost_of_capital_inputs("AAPL", config)
    price = fetch_price("AAPL", price_feed=price_feed)
    return build_spine(
        normalized,
        coc,
        price,
        excess_cash_pct=config.invested_capital.excess_cash_pct,
        schema_version=config.schema_version,
    )


def test_spine_computes_sane_fixture_values() -> None:
    spine = _spine()

    assert len(spine.years) == 5
    assert all(item.value > 0 for item in spine.roic_incl_gw)
    assert all(0 < item.value < 0.30 for item in spine.wacc)
    for margin, turnover, roic in zip(spine.nopat_margin, spine.capital_turnover, spine.roic_incl_gw, strict=True):
        assert margin.value * turnover.value == pytest.approx(roic.value)


def test_spine_uses_book_equity_when_price_unavailable() -> None:
    class BadFeed:
        def quote(self, ticker: str) -> dict[str, object]:
            raise RuntimeError("offline")

    spine = _spine(price_feed=BadFeed())

    assert "price_unavailable" in spine.flags
    assert all(item.value > 0 for item in spine.roic_incl_gw)


def test_audit_rejects_out_of_bounds_wacc() -> None:
    spine = _spine()
    broken_wacc = spine.wacc[0].model_copy(update={"value": 0.50})
    broken = spine.model_copy(update={"wacc": [broken_wacc, *spine.wacc[1:]]})
    handoff = build_handoff("AAPL", "0000320193", broken, price=None, as_of=None, schema_version="1.0", flags=[])

    with pytest.raises(AuditError, match="WACC out of bounds"):
        audit_m1_handoff(handoff)


def test_audit_rejects_missing_provenance() -> None:
    spine = _spine()
    broken_nopat = spine.nopat[0].model_copy(update={"provenance": None})
    broken = spine.model_copy(update={"nopat": [broken_nopat, *spine.nopat[1:]]})
    handoff = build_handoff("AAPL", "0000320193", broken, price=None, as_of=None, schema_version="1.0", flags=[])

    with pytest.raises(AuditError, match="missing provenance"):
        audit_m1_handoff(handoff)


def test_audit_rejects_missing_estimate_derivation() -> None:
    spine = _spine()
    broken_nopat = spine.nopat[0].model_copy(update={"derivation": None})
    broken = spine.model_copy(update={"nopat": [broken_nopat, *spine.nopat[1:]]})
    handoff = build_handoff("AAPL", "0000320193", broken, price=None, as_of=None, schema_version="1.0", flags=[])

    with pytest.raises(AuditError, match="estimate missing derivation"):
        audit_m1_handoff(handoff)


def test_audit_rejects_non_positive_invested_capital() -> None:
    spine = _spine()
    broken_ic = spine.invested_capital_incl_gw[0].model_copy(update={"value": 0.0})
    broken = spine.model_copy(update={"invested_capital_incl_gw": [broken_ic, *spine.invested_capital_incl_gw[1:]]})
    handoff = build_handoff("AAPL", "0000320193", broken, price=None, as_of=None, schema_version="1.0", flags=[])

    with pytest.raises(AuditError, match="invested capital must be positive"):
        audit_m1_handoff(handoff)


def test_audit_rejects_out_of_bounds_roic() -> None:
    spine = _spine()
    broken_roic = spine.roic_incl_gw[0].model_copy(update={"value": 2.0})
    broken = spine.model_copy(update={"roic_incl_gw": [broken_roic, *spine.roic_incl_gw[1:]]})
    handoff = build_handoff("AAPL", "0000320193", broken, price=None, as_of=None, schema_version="1.0", flags=[])

    with pytest.raises(AuditError, match="ROIC out of bounds"):
        audit_m1_handoff(handoff)


def test_audit_rejects_storage_round_trip_mismatch() -> None:
    spine = _spine()
    handoff = build_handoff("AAPL", "0000320193", spine, price=None, as_of=None, schema_version="1.0", flags=[])

    class CorruptingStorage:
        def put_json(self, path: str, payload: dict[str, object]) -> None:
            self.payload = dict(payload)

        def get_json(self, path: str) -> dict[str, object]:
            corrupted = dict(self.payload)
            corrupted["ticker"] = "MSFT"
            return corrupted

        def append_log(self, table: str, payload: dict[str, object]) -> None:
            raise NotImplementedError

    with pytest.raises(AuditError, match="storage round-trip failed"):
        audit_m1_handoff(handoff, storage=CorruptingStorage(), path="runs/AAPL/test/handoff.json")
