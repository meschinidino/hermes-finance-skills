from __future__ import annotations

import pytest


@pytest.mark.skip(reason="M1 CI uses frozen fixtures; live EDGAR smoke is manual.")
def test_live_edgar_smoke() -> None:
    raise NotImplementedError
