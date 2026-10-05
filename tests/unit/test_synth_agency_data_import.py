from importlib.metadata import version

import synth_agency_data


def test_synth_agency_data_imports() -> None:
    """One version for all three packages: the distribution's (docs/versioning.md)."""
    assert synth_agency_data.__version__ == version("agency-data-commons") == "0.1.0"
