from importlib.metadata import version

import jev_client


def test_jev_client_imports() -> None:
    """One version for all three packages: the distribution's (docs/versioning.md)."""
    assert jev_client.__version__ == version("agency-data-commons") == "0.2.0"
