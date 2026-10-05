"""C0a: no shared package may import agency-intake-kit's pipeline (`intake`), or any app code.

The scan reads every .py file under src/ as a syntax tree, so comments and strings that mention
intake do not count, but `import intake`, `from intake.x import y`, and
`importlib.import_module("intake...")` all do.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).parents[2] / "src"
PACKAGES = ("agency_schema", "synth_agency_data", "jev_client")
FORBIDDEN = ("intake", "bob_resolve", "plan_diff")


def _is_forbidden(module: str) -> bool:
    return module.split(".")[0] in FORBIDDEN


def forbidden_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        elif (
            isinstance(node, ast.Call)
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and (
                (isinstance(node.func, ast.Attribute) and node.func.attr == "import_module")
                or (
                    isinstance(node.func, ast.Name)
                    and node.func.id in {"import_module", "__import__"}
                )
            )
        ):
            names = [node.args[0].value]
        found += [
            f"{path.relative_to(SRC)}:{node.lineno} imports {n}" for n in names if _is_forbidden(n)
        ]
    return found


def test_every_package_is_scanned() -> None:
    assert sorted(
        p.name for p in SRC.iterdir() if p.is_dir() and (p / "__init__.py").exists()
    ) == sorted(PACKAGES)
    assert len(list(SRC.rglob("*.py"))) >= 30


def test_no_shared_package_imports_intake() -> None:
    offenders = [hit for path in sorted(SRC.rglob("*.py")) for hit in forbidden_imports(path)]
    assert offenders == []


@pytest.mark.parametrize(
    "line",
    [
        "import intake",
        "import intake.config as c",
        "from intake.config import JEV_MODEL",
        "from intake import config",
        "import importlib\nimportlib.import_module('intake.config')",
        "__import__('intake')",
    ],
)
def test_the_scan_catches_each_import_form(
    tmp_path: Path, line: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(f"{__name__}.SRC", tmp_path)
    bad = tmp_path / "bad.py"
    bad.write_text(line + "\n", encoding="utf-8")
    assert forbidden_imports(bad), line


def test_the_scan_ignores_mentions_in_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{__name__}.SRC", tmp_path)
    ok = tmp_path / "ok.py"
    ok.write_text('"""Used by intake."""\n# from intake import x\nHEADER = "uv run intake"\n')
    assert forbidden_imports(ok) == []
