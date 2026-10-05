# C1 notes: a second agency with overlapping people

Branch `c1-second-agency`, based on main at `b2f20ce` (C0a). Code: `src/synth_agency_data/multi.py`,
the `generate-multi` command in `cli.py`, tests in `tests/unit/test_multi_agency.py`.

## What it does

`synth generate-multi --seed 42 --agencies 2 --overlap 300 --b-clients 1500 --out DIR` writes:

| Path | What it is |
|---|---|
| `DIR/agency-a/` | Exactly `synth generate --seed 42` (same code path). Skipped with `--no-agency-a`. |
| `DIR/agency-b/drop/` | The four source shapes plus `manifest.json`, written by the same writers. |
| `DIR/agency-b/canonical/` | B's six canonical tables (clean, so `canonical/`, not `canonical-defected/`). |
| `DIR/agency-b/ground_truth.json` | `{"seed": 43, "defects": []}`. |
| `DIR/cross_agency_truth.json` | Counts, plus one entry per shared person (below). |

Each shared person: `person_id` (`PER-00001`...), `agency_a.client_ids` (the original A client
first, then any A copies found through `copy_of`), `agency_a.labels` (every A client defect on
those ids: `client_id`, `defect_type`, and the `fields` it changed), `agency_b.client_ids` (one id),
`agency_b.labels` (empty), and `contact_differs` (`phone`, `email`, or both).
Anyone not listed is a person held by one agency only.

## Decisions

1. **Agency A is untouched.** `generate-multi` calls the same `generate` function for A, and a
   test checks `agency-a/` against agency-intake-kit's hashes. No existing file or test changed
   except the three version tests.
2. **Agency B seed is A's seed plus 1 (43).** One number to remember; `b_seed()` holds the rule.
3. **Agency B has 1,500 clients**, so it is clearly a different, smaller book and the fixture
   stays near 2 MB. Result: 1,500 clients, 1,050 households, 1,950 policies, 25 agents,
   3,094 RTS rows, 4,995 commission lines.
4. **300 shared people by default.** That is 15 percent of A and 20 percent of B, a believable
   overlap for two agencies in the same states. It gives 300 true cross-agency pairs, so one false
   merge moves precision by about 0.3 points, fine enough to measure the 0.99 target in bob-resolve
   SPEC decision 2. The seed-43 book can hold at most 411 under the rules below, so 300 leaves room.
5. **Who can be shared.** A shared person takes over one B client who lives alone (so no household
   gets a stranger), in the same state, with the same Medicare or ACA status and the same
   eligibility reason, and (for reason AGE) whose B policies all start after the person turned 65.
   This keeps every B invariant of the clean world true: policy state matches the client, ages fit
   the eligibility reason, RTS and licenses cover every policy. People are drawn in a seeded
   shuffle (`overlap-43`) of A's 2,000 clean clients.
6. **True identity, no moves.** The B record gets the person's true first name, last name, birth
   date, MBI, and address (A's clean values, before A's defects). Nobody moves in C1; moved
   households are for C2. Phone stays B's, and email is rebuilt from the new name with B's row
   number, so contact details differ and are labeled in `contact_differs`.
7. **A's defects are the only identity differences.** If A's CRM says "Dave" (nickname) and B says
   "David", the person's `agency_a.labels` names that defect and field. A test checks that every
   identity or address field that differs between A and B is covered by such a label
   (seed 42: 33 labels on shared people, including 3 near-duplicate copies).
8. **Agency B is clean.** No planting (P-00417, NPN 1884412, HL-998213 stay A only) and no injected
   defects. Running A's injectors on B would add copies and identity edits that C2 is meant to
   design with pair truth; doing it here would make C2's work harder to label.
9. **B ids never collide with A.** Client, household, and policy ids are prefixed `B-`
   (`B-C-00001`, `B-H-00001`, `B-P-00001`). Carrier member ids keep their real format
   (`HL-123456`); since they are 6 random digits per carrier, about one B policy in 2,000 matches
   an A member id by chance, so each such id moves to the next free number (seed 43 has none;
   seeds 50 and 51 do, and a test uses them). An NPN shared with A refuses the seed, since 25
   random 8-digit NPNs almost never collide. Agent emails use `agency-b.example.com`.
10. **Version 0.2.0.dev0** (the PEP 440 spelling of 0.2.0-dev) in pyproject and each
    `__version__`. C2 tags 0.2.0. Nothing generated contains the version, so no fixture changes.

## Risks and notes for C2

- Shared people in B always live alone and never in a household with someone else. A matcher
  could learn that. C2's moved households and shared contacts should break the pattern.
- The overlap rules cap the count (411 at seed 43, 1,500 clients). Raising `--overlap` past that
  fails with a clear message rather than bending the rules.
- `distinct_people` counts A's 40 copies as the same people (2,000 + 1,500 - 300 = 3,200).
- C2's pair and cluster truth should extend `cross_agency_truth.json` rather than replace it, and
  should list B's own copies in `agency_b.client_ids` once B gets identity injectors.
- Changing `build_world`, the writers, or faker changes B's bytes; the fixture test catches it.
