# full-pipeline replay test (docs/07_testing_strategy.md §2).
from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Lands Phase 3 W6 once pipeline is wired")
def test_replay_30s_log() -> None:
    raise NotImplementedError
