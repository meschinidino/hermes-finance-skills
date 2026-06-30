from __future__ import annotations

import pytest


@pytest.mark.skip(reason="M1 uses configured cost-of-capital inputs; live FRED smoke is manual.")
def test_live_fred_smoke() -> None:
    raise NotImplementedError

