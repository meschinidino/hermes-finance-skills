from __future__ import annotations

import pytest


@pytest.mark.skip(reason="M1 CI uses injected or frozen price data; live smoke is manual.")
def test_live_price_smoke() -> None:
    raise NotImplementedError

