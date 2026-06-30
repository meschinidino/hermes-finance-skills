from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator


class StrictConfigModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CostOfCapitalConfig(StrictConfigModel):
    erp: float
    risk_free_fallback: float
    credit_spread: float

    @field_validator("erp", "risk_free_fallback", "credit_spread")
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

    @field_validator("unlevered")
    @classmethod
    def positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("unlevered beta must be positive")
        return value


class Config(StrictConfigModel):
    schema_version: str
    cost_of_capital: CostOfCapitalConfig
    tax: TaxConfig
    invested_capital: InvestedCapitalConfig
    betas: dict[str, BetaConfig]

    @model_validator(mode="after")
    def validate_betas(self) -> Config:
        if not self.betas:
            raise ValueError("at least one beta is required")
        normalized = {ticker.upper(): beta for ticker, beta in self.betas.items()}
        object.__setattr__(self, "betas", normalized)
        return self


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
