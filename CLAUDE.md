# agency-data-commons

Shared Python packages for the Agency Data Trust Series, installed by agency-intake-kit, bob-resolve,
and plan-diff: `agency_schema` (canonical models, lineage, exceptions, rule registry, formats),
`synth_agency_data` (seeded generator, injectors, planted records, source writers), and `jev_client`
(typed TypeSafe client with replay, off, live, record). Synthetic data only.

## Commands
- `npm run verify`   ruff, ruff format check, mypy strict, pytest. Must pass before any commit.
- `uv run synth generate --seed 42 --clients 2000 --out /tmp/agency-a`   the seed-42 world.
- `uv run synth generate-multi --seed 42 --no-agency-a --out fixtures/multi-a-b`   agency B and the
  cross-agency truth (docs/c1-notes.md).
- `uv run pytest -q tests/unit/test_generator_fidelity.py`   byte check against agency-intake-kit.

## Invariants (never break these)
- No package imports `intake`, `bob_resolve`, or `plan_diff` (tests/unit/test_no_intake_imports.py).
- Seed 42 regenerates agency-intake-kit's committed fixtures byte for byte
  (tests/reference/aik-fixture-hashes.json). Never edit the hashes to make a test pass.
  A deliberate generator change is a version bump and a coordinated fixture update in every consumer.
- `JevClient` has no default budget and no default cassette folder. Each project passes its own.
- JEV_MODE defaults to replay. live and record spend money and need Alex's approval every time.
  CI is always replay. Tests never touch the network (tests/conftest.py).
- Cassettes store request and response only, never headers. tests/unit/test_cassettes.py greps
  every cassette for Authorization, TYPESAFE_API_KEY, and Bearer.
- No PHI, no real data, no SSNs. The six carriers are fictional.
- Never read .env or any .env.* file. This repo needs no key.

## Versioning
- One version for all three packages, set in pyproject.toml and each `__version__`.
- Releases are git tags `vX.Y.Z`; consumers pin an exact tag. See docs/versioning.md.
- Only the orchestrator tags, after verify is green and Alex has said yes.

## Gotchas
- Use uv, not pip. Use polars, not pandas. Python 3.12.
- faker and openpyxl are pinned exactly: their versions change generator bytes.
- Node 24 for the root verify script only. There is no dashboard here.
- Docs: plain language, no em dashes.
- The repo path contains a space ("Data intake"). Quote every absolute path.

## Workflow
- One PR per session. Branch names cNN-short-name. Under 400 changed lines, excluding moved code.
- Tests first, then implementation, then `npm run verify`, then show the output.
- One changelog fragment per PR in changelog.d/ (see its README). Do not edit CHANGELOG.md directly.
- Never push, open a PR, merge, tag, create a GitHub repo, or link Vercel without Alex's explicit
  go-ahead in his own words, each time.
