## C2: Hard identity cases and pair truth for agency B (2026-10-05)

- Agency B now holds nine labeled identity cases at default rates (15 or more each): maiden and
  hyphenated surnames, moved households (some with a stale old record), spouses sharing phone and
  email, the same policy under two member ids, and must-not-merge look-alikes (child on a parent's
  policy, twins, father and son with one name, same name and birth date in another ZIP).
- 40 percent of shared people now live with someone in B, so living alone no longer marks them.
- New truth files: `pair_truth.jsonl`, `cluster_truth.json`, `must_not_merge.jsonl`.
  `cross_agency_truth.json` gains B labels, B copies, household size, and more counts.
- `fixtures/multi-a-b/` regenerated (about 2.6 MB). Agency A is unchanged, byte for byte.
- Version 0.2.0. Breaking for consumers of `fixtures/multi-a-b` or `generate-multi`: agency B's
  bytes changed, `agency-b/ground_truth.json` is no longer empty, and B has more client ids than
  people. `synth generate` is unchanged.
