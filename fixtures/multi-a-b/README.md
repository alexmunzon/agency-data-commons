# multi-a-b: two agencies that share 300 people, with hard identity cases in agency B

Made with:

```bash
uv run synth generate-multi --seed 42 --no-agency-a --out fixtures/multi-a-b
```

- `agency-b/`: agency B (seed 43, 1,560 client ids for 1,552 people, 1,050 households, 2,012
  policies, 25 agents). `drop/` holds the same four source shapes as agency A plus `manifest.json`;
  `canonical/` holds the canonical tables; `ground_truth.json` lists the 190 C2 labels
  (docs/synthetic-data.md, "Hard identity cases"), each with `scored: true`, `same_person`,
  `record_keys` in both agencies, and the injected values.
- `cross_agency_truth.json`: the 300 people both agencies hold, each with their client ids and
  labels in agency A and agency B, B household size, which contact fields differ, and the counts.
- `pair_truth.jsonl`: one line per true same-person pair, 320 in all: 312 across agencies and 8
  within agency B. 146 pairs carry at least one defect type; 174 have none.
- `cluster_truth.json`: person id to every client id in A and B (3,252 people). Each client id is
  in exactly one cluster. Pairs within agency A (A's own copies) are in A's ground truth.
- `must_not_merge.jsonl`: 164 pairs that look alike but are different people, with a reason:
  42 spouses sharing contact details, 36 child on a parent's policy, 36 father and son with the
  same name, 32 twins, 18 same name and birth date in another ZIP. 91 cross the agencies.

Labels by type: same_policy_two_member_ids 28 (18 people), moved_household 24 (8 of them keep a
stale old record, `moved_household_stale_copy`), maiden_name 21, shared_household_contact 21,
hyphenated_surname 18, child_on_parent_policy 18, father_son_same_name 18, name_dob_lookalike 18,
twin_lookalike 16. 154 of the 300 shared people live with someone else in B.

Agency A is not copied here. It is exactly `uv run synth generate --seed 42 --clients 2000`, the
same bytes as agency-intake-kit's `fixtures/agency-a` (hashes in
`tests/reference/aik-fixture-hashes.json`). Drop `--no-agency-a` to write it next to agency B.
All data is synthetic.
