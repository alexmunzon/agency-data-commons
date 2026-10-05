## C1: A second agency that shares a known set of people (2026-10-05)

- New command `synth generate-multi --seed 42 --agencies 2 --overlap 300` writes `agency-a/`
  (exactly today's seed-42 world, byte for byte), `agency-b/` (seed 43, 1,500 clients, its own
  agents, households, and policies, ids prefixed `B-`), and `cross_agency_truth.json`.
- 300 people are held by both agencies by default: the same name, birth date, MBI, and address in
  B as their true values in A, with a different phone and email. Planting stays agency A only.
- New committed fixture `fixtures/multi-a-b/` (agency B plus the cross-agency truth, about 2.2 MB).
  Agency A is referenced, not copied.
- Version 0.2.0.dev0 (C2 tags 0.2.0). Not breaking: `synth generate` and every existing seed-42
  file are unchanged.
