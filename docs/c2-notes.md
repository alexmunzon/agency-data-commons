# C2 notes: hard identity cases in agency B

Branch `c2-harder-injectors`, based on main at `a2aeb62` (C1). Code: `src/synth_agency_data/identity.py`
(injectors and truth files), `multi.py` (household placement, B labels in the cross-agency truth),
`cli.py`. Tests: `tests/unit/test_identity_injectors.py`, updated `tests/unit/test_multi_agency.py`.
What each case looks like: docs/synthetic-data.md, "Hard identity cases in agency B".

## Decisions

1. **Agency A is untouched.** Every injector edits agency B only. A's byte test still passes.
2. **Built blind to the matcher.** Only bob-resolve SPEC section 5 (phase 2 list) was read; none of
   bob-resolve's scoring, blocking, or hard-case files. Cases were designed from how real agency
   books go wrong, not from what the matcher finds hard.
3. **Households first (the C1 leak).** In C1 every shared person lived alone in B. Now each shared
   person first rolls a 40 percent chance to replace someone in a multi-person B household (falling
   back to a single, or the other way round). Housemates take the person's surname and address, so
   the household still reads as one family at one address. One shared person per household.
   Result at seed 43: 117 of 300 placed with others; 154 after twins, sons, and children join.
4. **One case per shared person.** Each injector draws anchors from shared people no other case has
   used, so a label always explains exactly one change. Real life stacks problems; A's own defects
   still stack on top (a B maiden name can meet an A nickname), and pair truth lists both.
5. **Rates are shares of the shared people** (`identity.RATES`, passed as `rates=` to
   `inject_identity`), so instance counts track the overlap. Defaults give 15 to 28 each. The CLI
   uses the defaults; a test runs each injector alone to prove it changes only what it labels.
6. **Label shape.** B labels reuse the A defect shape (`source`, `record_key`, `row_ref`,
   `source_file`, `source_row`, `expected_rule_ids: []`) and add `scored: true`, `same_person`,
   `anchor_client_id`, `fields` (identity or address fields changed), and `record_keys` for both
   agencies. `scored` here means bob-resolve scores it; no intake rule fires on it.
7. **Same policy, two member ids** replaces the person's B policies with copies of their A policies
   (A's carrier, plan, dates, premium) written by their B agent, with new member ids. RTS rows are
   added for any new agent, carrier, state, year, and product, so B stays a consistent book.
8. **Child on a parent's policy** uses ACA only, since Medicare has no dependents. The child's
   policy row reuses the parent's member id plus "-01", carries no premium, and gets no commission
   line, because carriers pay the subscriber's policy. Intake's TIE-001 would flag that row if
   someone ran intake on B; nobody does today.
9. **Father and son** need a Medicare father aged 66 or more; the son (26 to 63) gets a copy of an
   ACA client's policies in the same state, so agent licenses and RTS fit.
10. **Name and birth date look-alikes** pair a B single with an A-only person in the same state but
   a different ZIP, matching Medicare status and eligibility, so state alone cannot separate them.
11. **Stale copies** (a third of movers) give 8 same-person pairs within B. They have no household and
   no policy, like A's copies. B therefore has 1,560 client ids for 1,552 people.
12. **Person ids.** Shared people keep `PER-00001` to `PER-00300` from C1; A-only people follow in A
   id order, then B-only people in B id order. A copies join their original's cluster.
13. **Pair truth covers cross-agency and within-B pairs only.** A's internal pairs are already in A's
   ground truth (`copy_of`) and bob-resolve phase 1.
14. **Version 0.2.0** in pyproject and each `__version__`. The orchestrator tags.

## Counts at seed 42 / 43

320 true pairs (312 cross, 8 within B), 3,252 clusters, 164 must-not-merge pairs (42 spouses, 36
child, 36 father and son, 32 twins, 18 same name and birth date). See the fixture README.

## Risks

- `twin_lookalike` has 16 instances, just over the floor of 15: twins need a first name in a fixed
  table, and two drawn anchors were skipped because the twin's name and birth date were taken.
- Look-alikes differ from their anchor in MBI. bob-resolve's "no shared ids" mode is the honest
  test; with MBI available, most look-alikes are easy.
- Housemates who adopt a shared person's surname are B-only people, so their changed names are not
  labeled (nothing to match them to in A). A test confirms only labeled clients and their housemates
  change.
- The code is larger than the 400-line guide (see the report): nine injectors plus three truth files.
