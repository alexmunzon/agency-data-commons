"""C0a: the moved generator reproduces agency-intake-kit's committed seed-42 fixtures byte for byte.

If this fails, do not edit the hashes: the generator changed behavior. Stop and report.
"""

import hashlib
import re
from pathlib import Path

import pytest
from aik_reference import FLAGS, digest, generate, generated_root, reference, reference_hashes

SMALL_COPY = Path(__file__).parents[1] / "reference" / "agency-a" / "drop" / "manifest.json"


def test_reference_names_its_source_commit() -> None:
    assert reference()["source_repo"] == "agency-intake-kit"
    assert re.fullmatch(r"[0-9a-f]{40}", str(reference()["source_commit"]))
    changelog = (Path(__file__).parents[2] / "CHANGELOG.md").read_text(encoding="utf-8")
    assert str(reference()["source_commit"]) in changelog, "CHANGELOG.md records the source SHA"


def test_reference_covers_every_file() -> None:
    assert len(reference_hashes("agency-a")) == 17  # 6 canonical tables, 10 drop files, truth
    assert len(reference_hashes("agency-a-ssn")) == 11  # drop files and truth, no canonical
    assert len(reference_hashes("agency-a-truncated")) == 11
    for hashes in map(reference_hashes, FLAGS):
        assert all(re.fullmatch(r"[0-9a-f]{64}", h) for h in hashes.values())


@pytest.mark.parametrize("name", sorted(FLAGS))
def test_seed_42_regenerates_byte_for_byte(name: str, tmp_path: Path) -> None:
    generate(name, tmp_path)
    assert digest(tmp_path) == reference_hashes(name)


def test_small_copy_matches_its_hash_and_the_generator() -> None:
    """A readable copy of one small file, so a reviewer can see the hashes mean real bytes."""
    data = SMALL_COPY.read_bytes()
    assert hashlib.sha256(data).hexdigest() == reference_hashes("agency-a")["drop/manifest.json"]
    assert (generated_root() / "agency-a" / "drop" / "manifest.json").read_bytes() == data
