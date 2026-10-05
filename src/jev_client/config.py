"""Jev client defaults. Moved here from agency-intake-kit's intake/config.py (PR 6) in C0a.

Endpoint, model, and price checked on docs.typesafe.ai on 2026-10-04 (see docs/jev.md).

Two settings are deliberately NOT here, because each project owns them:
- the spend budget: every JevClient must be given `budget_usd` (agency-intake-kit uses $0.50);
- the cassette folder: every JevClient must be given `cassette_dir`, inside the calling project.
"""

from decimal import Decimal
from typing import Final

JEV_API_URL: Final[str] = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL: Final[str] = "jev-latest"
JEV_USD_PER_MTOK_IN: Final[Decimal] = Decimal("0.042")  # dollars per million input tokens
JEV_MAX_TRIES: Final[int] = 5  # total tries on 429 and 529, the first one included
JEV_BACKOFF_BASE_S: Final[float] = 1.0  # first wait; doubles each retry, with jitter
JEV_TIMEOUT_S: Final[float] = 30.0  # seconds per HTTP request
