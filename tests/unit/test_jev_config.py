"""C0a: jev_client owns its defaults; each project passes its own budget and cassette folder."""

import inspect
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from agency_schema.outputs import JevMode
from jev_client import JevClient, JevRequest, NoulQuestion, estimate_cost_usd
from jev_client import config as jev_config


def test_defaults_match_the_values_checked_on_2026_10_04() -> None:
    """Changing one of these is a behavior change for every project: bump the version."""
    assert jev_config.JEV_API_URL == "https://api.typesafe.ai/v1/systemone"
    assert jev_config.JEV_MODEL == "jev-latest"
    assert jev_config.JEV_USD_PER_MTOK_IN == Decimal("0.042")
    assert jev_config.JEV_MAX_TRIES == 5
    assert jev_config.JEV_BACKOFF_BASE_S == 1.0
    assert jev_config.JEV_TIMEOUT_S == 30.0
    assert "docs.typesafe.ai on 2026-10-04" in (jev_config.__doc__ or "")


def test_no_budget_default_anywhere() -> None:
    assert not hasattr(jev_config, "JEV_BUDGET_USD"), "the budget is each project's policy"
    for fn in (JevClient.__init__, JevClient.from_env):
        params = inspect.signature(fn).parameters
        for name in ("cassette_dir", "budget_usd"):
            assert params[name].default is inspect.Parameter.empty, f"{fn.__name__}.{name}"
            assert params[name].kind is inspect.Parameter.KEYWORD_ONLY


@pytest.mark.parametrize("missing", ["cassette_dir", "budget_usd"])
def test_client_refuses_to_start_without_budget_or_folder(tmp_path: Path, missing: str) -> None:
    kwargs: dict[str, Any] = {
        "mode": JevMode.REPLAY,
        "api_key": None,
        "cassette_dir": tmp_path,
        "budget_usd": Decimal("0.50"),
    }
    del kwargs[missing]
    with pytest.raises(TypeError, match=missing):
        JevClient(**kwargs)
    env_kwargs = {k: v for k, v in kwargs.items() if k not in ("mode", "api_key")}
    with pytest.raises(TypeError, match=missing):
        JevClient.from_env(**env_kwargs)


@pytest.mark.parametrize("bad", [Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity"), 0.5, None])
def test_budget_must_be_a_real_non_negative_decimal(tmp_path: Path, bad: Any) -> None:
    with pytest.raises(ValueError, match="budget_usd"):
        JevClient(mode=JevMode.REPLAY, api_key=None, cassette_dir=tmp_path, budget_usd=bad)


def test_the_budget_given_is_the_budget_used(tmp_path: Path) -> None:
    client = JevClient(
        mode=JevMode.OFF, api_key=None, cassette_dir=tmp_path, budget_usd=Decimal("0.25")
    )
    assert client.usage.budget_usd == Decimal("0.25")


def test_model_and_price_come_from_jev_client_config() -> None:
    request = JevRequest(
        state={"x": 1},
        questions={"q": NoulQuestion(type="noul", instructions="yes?", criteria=None)},
    )
    assert request.body()["model"] == jev_config.JEV_MODEL
    assert estimate_cost_usd(1_000_000) == jev_config.JEV_USD_PER_MTOK_IN
