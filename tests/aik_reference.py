"""agency-intake-kit's committed seed-42 fixtures, as SHA-256 hashes plus a fresh regeneration.

This repo does not copy the 6 MB of fixtures. tests/reference/aik-fixture-hashes.json holds the
hash of every file in agency-intake-kit's fixtures/agency-a, agency-a-ssn, and agency-a-truncated
at the commit recorded in that file. `generated_root()` regenerates all three once per test run
with this repo's generator and refuses to hand them out unless every byte matches those hashes,
so tests that read file contents read exactly what agency-intake-kit committed.
"""

import atexit
import hashlib
import json
import shutil
import tempfile
from functools import cache
from pathlib import Path

from typer.testing import CliRunner

from synth_agency_data.cli import app

REFERENCE = Path(__file__).parent / "reference" / "aik-fixture-hashes.json"
# The flags agency-intake-kit used to write each committed fixture (its tests/unit/test_writers.py).
FLAGS: dict[str, list[str]] = {
    "agency-a": [],
    "agency-a-truncated": ["--truncate-crm", "2574", "--no-canonical"],
    "agency-a-ssn": ["--add-ssn-column", "--no-canonical"],
}


def digest(root: Path) -> dict[str, str]:
    """Relative path to SHA-256 hex for every file under root."""
    files = sorted(p for p in root.rglob("*") if p.is_file())
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files
    }


@cache
def reference() -> dict[str, object]:
    data: dict[str, object] = json.loads(REFERENCE.read_text(encoding="utf-8"))
    return data


def reference_hashes(name: str) -> dict[str, str]:
    fixtures = reference()["fixtures"]
    assert isinstance(fixtures, dict)
    hashes: dict[str, str] = fixtures[name]
    return hashes


def generate(name: str, out: Path) -> None:
    args = ["generate", "--seed", "42", "--out", str(out), *FLAGS[name]]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output


@cache
def generated_root() -> Path:
    """A temp folder holding all three regenerated fixtures, checked byte for byte."""
    root = Path(tempfile.mkdtemp(prefix="commons-fixtures-"))
    atexit.register(shutil.rmtree, root, ignore_errors=True)
    for name in FLAGS:
        generate(name, root / name)
        assert digest(root / name) == reference_hashes(name), (
            f"the generator no longer reproduces agency-intake-kit's fixtures/{name}"
        )
    return root
