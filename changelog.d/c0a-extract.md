## C0a: Extract the shared packages from agency-intake-kit (2026-10-05)

- Copied `agency_schema`, `synth_agency_data`, and `jev_client` from agency-intake-kit commit
  `e9a759399fed447fd0bd3c659055f0b04faa89c9`, with their unit tests, `zip3_state.csv`, the four sample-run fixtures,
  and docs/schema.md, docs/jev.md, docs/synthetic-data.md. Import names are unchanged.
- One distribution, `agency-data-commons` 0.1.0, ships all three packages and the `synth` command.
- New `jev_client/config.py` holds the Jev URL, model, price, retries, backoff, and timeout.
  Nothing in the packages imports `intake` any more, and a test keeps it that way.
- Breaking for callers: `JevClient` and `JevClient.from_env` now require `cassette_dir` and
  `budget_usd`. There is no default budget and no default cassette folder.
- The moved generator regenerates agency-intake-kit's seed-42 fixtures byte for byte, checked
  against their SHA-256 hashes.
