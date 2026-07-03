from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skills.accountant_artifacts import BareHandoff, ExpectationsLine, GateCard, MethodDirective, Spine, ValuationRange
from skills.analyst_artifacts import ReviewSourceManifest, SeniorDecisionPackage, SeniorReviewPackage
from skills.research.business.business import BusinessArtifact
from skills.research.capalloc.capalloc import CapAllocArtifact
from skills.research.edge_cruxes.edge_cruxes import EdgeCruxesArtifact
from skills.research.moat.moat import MoatArtifact
from skills.research.risk.risk import RiskArtifact
from skills.research.scenarios.scenarios import ScenarioSetArtifact


class SynthesisPayload(BaseModel):
    """Validated M4a boundary output consumed by D-2 and D-3."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=False)

    handoff: BareHandoff = Field(alias="__handoff")
    business: BusinessArtifact
    business_review_package: SeniorReviewPackage
    early_gate: dict[str, Any]
    moat: MoatArtifact
    moat_review_package: SeniorReviewPackage
    capalloc: CapAllocArtifact
    capalloc_review_package: SeniorReviewPackage
    gate_card: GateCard
    gate_card_review_package: SeniorReviewPackage
    method_directive: MethodDirective
    scenarios: ScenarioSetArtifact
    scenarios_review_package: SeniorReviewPackage
    edge_cruxes: EdgeCruxesArtifact
    edge_cruxes_review_package: SeniorReviewPackage
    risk: RiskArtifact
    risk_review_package: SeniorReviewPackage
    senior_review_package: SeniorReviewPackage
    senior_decision_package: SeniorDecisionPackage
    route_review_manifest: ReviewSourceManifest
    valuation_range: ValuationRange | None = None
    expectations_line: ExpectationsLine | None = None
    valuation_deferred: str | None = None

    @model_validator(mode="before")
    @classmethod
    def lift_bare_handoff_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "__handoff" in data:
            return data
        bare_keys = {"header", "status", "ticker", "cik", "as_of", "price", "spine", "confidence_and_gaps", "data_room", "flags"}
        missing = sorted(bare_keys - set(data))
        if missing:
            raise ValueError(f"synthesis payload missing bare handoff fields: {', '.join(missing)}")
        cleaned = {key: value for key, value in data.items() if key not in bare_keys}
        return {
            **cleaned,
            "__handoff": {key: data[key] for key in bare_keys},
        }

    @model_validator(mode="after")
    def validate_route_and_ratification(self) -> SynthesisPayload:
        if not self.senior_decision_package.is_complete:
            raise ValueError("synthesis requires complete Senior decision package")
        required_ids = {item.id for item in self.senior_review_package.review_items if item.required}
        if required_ids != set(self.senior_decision_package.required_item_ids):
            raise ValueError("Senior decision package does not match consolidated review package")
        method = self.method_directive.method
        if method == "DCF":
            if self.valuation_range is None or self.expectations_line is None:
                raise ValueError("DCF synthesis requires valuation_range and expectations_line")
            if self.valuation_deferred is not None:
                raise ValueError("DCF synthesis cannot carry valuation_deferred")
        else:
            if not self.valuation_deferred:
                raise ValueError(f"{method} synthesis requires valuation_deferred")
            if self.valuation_range is not None or self.expectations_line is not None:
                raise ValueError(f"{method} synthesis cannot consume DCF valuation artifacts")
        if self.handoff.ticker != self.method_directive.ticker:
            raise ValueError("synthesis payload ticker mismatch")
        return self

    @property
    def ticker(self) -> str:
        return self.handoff.ticker

    @property
    def as_of(self):
        return self.handoff.as_of

    @property
    def schema_version(self) -> str:
        return self.handoff.header.schema_version

    @property
    def spine(self) -> Spine:
        return self.handoff.spine
