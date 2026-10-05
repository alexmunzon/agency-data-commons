# agency-data-commons

Shared Python packages for the Agency Data Trust Series. agency-intake-kit, bob-resolve, and
plan-diff install one copy from here. Synthetic data only.

| Package | What it holds |
|---|---|
| `agency_schema` | Canonical models for the six tables, lineage, ExceptionRecord, rule registry, format checks, run output models |
| `synth_agency_data` | The seeded generator, defect injectors, planted records, and the four messy source writers (`synth` command) |
| `jev_client` | A typed client for TypeSafe's Jev with replay, off, live, and record modes, cassettes, and a spend guard |

## Install

Pin an exact tag (docs/versioning.md):

```toml
dependencies = [
    "agency-data-commons @ git+https://github.com/alexmunzon/agency-data-commons@v0.1.0",
]
```

## Use the Jev client

Every project passes its own cassette folder and its own budget. There are no defaults.

```python
from decimal import Decimal
from pathlib import Path

from jev_client import JevClient

client = JevClient.from_env(cassette_dir=Path("tests/cassettes"), budget_usd=Decimal("0.50"))
```

`JEV_MODE` defaults to `replay`, which is free. `live` and `record` spend money and also need
`allow_spend=True`.

## Develop

```bash
uv sync
npm run verify   # ruff, ruff format check, mypy strict, pytest
```

Docs: [schema](docs/schema.md), [Jev](docs/jev.md), [synthetic data](docs/synthetic-data.md),
[versioning](docs/versioning.md), [C0a extraction notes](docs/c0a-notes.md).
Extracted from agency-intake-kit; the source commit is in CHANGELOG.md. MIT license.
