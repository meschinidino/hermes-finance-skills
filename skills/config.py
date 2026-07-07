from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class StrictConfigModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CostOfCapitalConfig(StrictConfigModel):
    erp: float
    risk_free_fallback: float
    credit_spread: float
    synthetic_rating: str
    wacc_band_bps: float

    @field_validator("erp", "risk_free_fallback", "credit_spread", "wacc_band_bps")
    @classmethod
    def non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("must be non-negative")
        return value


class TaxConfig(StrictConfigModel):
    marginal_rate: float

    @field_validator("marginal_rate")
    @classmethod
    def decimal_rate(cls, value: float) -> float:
        if not 0 < value < 1:
            raise ValueError("marginal_rate must be a decimal between 0 and 1")
        return value


class InvestedCapitalConfig(StrictConfigModel):
    excess_cash_pct: float

    @field_validator("excess_cash_pct")
    @classmethod
    def non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("excess_cash_pct must be non-negative")
        return value


class BetaConfig(StrictConfigModel):
    unlevered: float
    source_name: str
    source_url: str
    source_date: str
    tickers: list[str]

    @field_validator("unlevered")
    @classmethod
    def positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("unlevered beta must be positive")
        return value

    @model_validator(mode="after")
    def source_backed(self) -> BetaConfig:
        if not self.source_name or not self.source_date or not self.source_url:
            raise ValueError("beta requires Damodaran source metadata")
        if not self.tickers:
            raise ValueError("beta sector requires covered tickers")
        return self


class DcfScenarioConfig(StrictConfigModel):
    revenue_growth: float
    nopat_margin: float
    sales_to_capital: float

    @field_validator("sales_to_capital")
    @classmethod
    def positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("sales_to_capital must be positive")
        return value


class DcfSectorScenarioConfig(StrictConfigModel):
    status: Literal["active"]
    source_name: str
    source_date: str
    industry_category: str
    firm_count: int
    source_urls: dict[str, str]
    tickers: list[str]
    rationale: str
    scenarios: dict[str, DcfScenarioConfig]

    @field_validator("firm_count")
    @classmethod
    def positive_firm_count(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("firm_count must be positive")
        return value

    @model_validator(mode="after")
    def validate_sector(self) -> DcfSectorScenarioConfig:
        if not self.source_name.strip() or not self.source_date.strip():
            raise ValueError("active sector scenario requires source metadata")
        if not self.industry_category.strip():
            raise ValueError("active sector scenario requires industry category")
        if not self.source_urls or any(not key.strip() or not value.strip() for key, value in self.source_urls.items()):
            raise ValueError("active sector scenario requires source URLs")
        if not self.tickers:
            raise ValueError("active sector scenario requires covered tickers")
        if not self.rationale.strip():
            raise ValueError("active sector scenario requires rationale")
        if set(self.scenarios) != {"bear", "base", "bull"}:
            raise ValueError("sector dcf scenarios must be bear/base/bull")
        return self


class DcfConfig(StrictConfigModel):
    forecast_years: int
    terminal_growth: float
    reverse_growth_low: float
    reverse_growth_high: float
    scenarios: dict[str, DcfScenarioConfig]
    sector_scenarios: dict[str, DcfSectorScenarioConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dcf(self) -> DcfConfig:
        if self.forecast_years <= 0:
            raise ValueError("forecast_years must be positive")
        if self.reverse_growth_low >= self.reverse_growth_high:
            raise ValueError("reverse growth low must be below high")
        if set(self.scenarios) != {"bear", "base", "bull"}:
            raise ValueError("dcf scenarios must be bear/base/bull")
        return self


class Config(StrictConfigModel):
    schema_version: str
    cost_of_capital: CostOfCapitalConfig
    tax: TaxConfig
    invested_capital: InvestedCapitalConfig
    betas: dict[str, BetaConfig]
    dcf: DcfConfig

    @model_validator(mode="after")
    def validate_betas(self) -> Config:
        if not self.betas:
            raise ValueError("at least one beta is required")
        if "AAPL" in {ticker.upper() for ticker in self.betas}:
            raise ValueError("AAPL ticker beta placeholder is not allowed; use source-backed sector beta")
        seen_sector_tickers: dict[str, str] = {}
        for sector, sector_config in self.dcf.sector_scenarios.items():
            for ticker in sector_config.tickers:
                normalized = ticker.upper().strip()
                if normalized in seen_sector_tickers:
                    raise ValueError(f"duplicate_dcf_sector_assignment:{normalized}")
                seen_sector_tickers[normalized] = sector
        normalized = {sector: beta for sector, beta in self.betas.items()}
        object.__setattr__(self, "betas", normalized)
        return self

    def beta_for_ticker(self, ticker: str) -> BetaConfig:
        normalized = ticker.upper().strip()
        for beta in self.betas.values():
            if normalized in {covered.upper() for covered in beta.tickers}:
                return beta
        raise ValueError(f"missing_beta:{normalized}")

    def dcf_sector_for_ticker(self, ticker: str) -> str | None:
        normalized = ticker.upper().strip()
        matched = [
            sector
            for sector, sector_config in self.dcf.sector_scenarios.items()
            if normalized in {covered.upper() for covered in sector_config.tickers}
        ]
        if len(matched) > 1:
            raise ValueError(f"duplicate_dcf_sector_assignment:{normalized}")
        return matched[0] if matched else None


def load_config(path: Path | str) -> Config:
    raw = _parse_yaml(Path(path))
    try:
        return Config.model_validate(raw)
    except ValidationError as exc:
        missing = next((error for error in exc.errors() if error["type"] == "missing"), None)
        if missing:
            key = ".".join(str(part) for part in missing["loc"])
            raise ValueError(f"missing required config key: {key}") from exc
        raise ValueError(str(exc)) from exc


def _parse_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)

    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("config root must be a mapping")
    return loaded
