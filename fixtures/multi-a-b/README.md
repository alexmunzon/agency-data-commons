# multi-a-b: two agencies that share 300 people

Made with:

```bash
uv run synth generate-multi --seed 42 --no-agency-a --out fixtures/multi-a-b
```

- `agency-b/`: agency B (seed 43, 1,500 clients, 1,050 households, 1,950 policies, 25 agents).
  `drop/` holds the same four source shapes as agency A plus `manifest.json`; `canonical/` holds
  the clean canonical tables; `ground_truth.json` lists no defects (B is clean in C1).
- `cross_agency_truth.json`: the 300 people both agencies hold, each with their client ids in
  agency A and agency B, agency A's labels on those ids, and which contact fields differ.

Agency A is not copied here. It is exactly `uv run synth generate --seed 42 --clients 2000`, the
same bytes as agency-intake-kit's `fixtures/agency-a` (hashes in
`tests/reference/aik-fixture-hashes.json`). Drop `--no-agency-a` to write it next to agency B.
All data is synthetic.
