from importlib.metadata import version

import agency_schema


def test_agency_schema_imports() -> None:
    """One version for all three packages: the distribution's (docs/versioning.md)."""
    assert agency_schema.__version__ == version("agency-data-commons") == "0.2.0"
