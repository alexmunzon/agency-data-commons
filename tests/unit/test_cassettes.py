"""C0a: the copied cassettes hold no secrets, and they replay from a folder passed in explicitly.

The replay test also proves the cassette hash recipe did not change in the move, so
agency-intake-kit's existing cassettes keep hitting after it switches to this package.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from agency_schema.outputs import JevMode
from jev_client import JevClient, JevRequest, JevResponse, request_hash

CASSETTES = Path(__file__).parents[1] / "cassettes"
SECRET_MARKERS = ("authorization", "typesafe_api_key", "bearer")


def cassette_files() -> list[Path]:
    return sorted(p for p in CASSETTES.rglob("*") if p.is_file())


def test_there_is_at_least_one_cassette() -> None:
    assert [p.suffix for p in cassette_files()] == [".json"]


@pytest.mark.parametrize("path", cassette_files(), ids=lambda p: p.name[:12])
def test_no_secret_markers_in_cassettes(path: Path) -> None:
    text = path.read_text(encoding="utf-8").casefold()
    assert [m for m in SECRET_MARKERS if m in text] == []


@pytest.mark.parametrize("path", cassette_files(), ids=lambda p: p.name[:12])
def test_cassette_holds_only_request_and_response(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert sorted(data) == ["request", "response"]
    assert path.stem == request_hash(data["request"]), "file name is the request hash"


@pytest.mark.parametrize("path", cassette_files(), ids=lambda p: p.name[:12])
def test_cassette_replays_from_an_explicit_folder(path: Path) -> None:
    recorded = json.loads(path.read_text(encoding="utf-8"))["request"]
    request = JevRequest.model_validate(
        {"state": recorded["state"], "questions": recorded["questions"]}
    )
    assert request.body() == recorded, "the body this package sends hashes to the same file"
    client = JevClient(
        mode=JevMode.REPLAY, api_key=None, cassette_dir=CASSETTES, budget_usd=Decimal("0.50")
    )
    response = client.ask(request)
    assert isinstance(response, JevResponse)
    assert set(response.answers) == set(recorded["questions"])
    assert client.usage.calls == 1
