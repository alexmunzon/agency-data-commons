# C0a notes: extracting the shared packages

Source: agency-intake-kit commit `e9a759399fed447fd0bd3c659055f0b04faa89c9` (`v0.1.0-4-ge9a7593`,
main after Sweep 2). One shared file changed after the v0.1.0 tag (`agency_schema/outputs.py`, #83),
so C0b must be based on agency-intake-kit main at or after this commit.

## What moved, and how

- Commit 1 on this branch is a verbatim copy, so `git diff <commit 1>` shows every edit made here.
- Packages: `src/agency_schema`, `src/synth_agency_data`, `src/jev_client` (git-tracked files only,
  including `py.typed` and `agency_schema/data/zip3_state.csv`).
- Tests: the 13 unit test files that import only these packages, plus `tests/unit/conftest.py`.
  Tests that import `intake` stay in agency-intake-kit.
- Fixtures: the four small `sample-run*` folders (used by the output model tests) moved to
  `tests/fixtures/`. The 6 MB seed-42 fixtures did not move; see "Generator fidelity".
- Docs: schema.md, jev.md, synthetic-data.md, each with a note that intake-specific text describes
  agency-intake-kit. jev.md gains a section on the new client arguments.

## Decisions

1. **Flat layout.** `pyproject.toml`, `src/`, and `tests/` sit at the repo root (no `engine/`
   folder), so consumers can install `git+https://...@v0.1.0` without a `#subdirectory`.
2. **Dependencies are exactly what the packages import:** faker, httpx, openpyxl, polars, pydantic,
   typer (the `synth` command). faker 40.40.0 and openpyxl 3.1.5 are pinned exactly, the versions in
   agency-intake-kit's uv.lock, because they decide generator bytes. The others take a floor at
   agency-intake-kit's locked version.
3. **The `synth` command ships here.** C0b must remove `synth` from agency-intake-kit's
   `[project.scripts]`, or the two entry points collide.
4. **Version 0.1.0 everywhere.** Each `__version__` moved from 0.0.0 to 0.1.0; the import tests now
   check that it equals the installed distribution version. No generated file contains these
   versions (agency-intake-kit's run manifest uses `intake.__version__`).
5. **Strings that name agency-intake-kit stay.** `agency_schema.typescript.HEADER` and the JSON
   Schema title still say agency-intake-kit, because its generated `dashboard/lib/types.ts` must not
   change in C0b. Renaming them is a later, versioned change.
6. **Jev budget is required and checked:** `budget_usd` must be a finite `Decimal` of 0 or more, or
   the client raises `ValueError`. A float is refused, matching the money rule of other repos.
7. **Cassette folder is required.** `DEFAULT_CASSETTE_DIR` is gone. A `JEV_CASSETTE_DIR`
   environment setting was not added: one required argument is simpler and cannot be left unset.
8. **Cassettes.** The moved tests write their own cassettes into `tmp_path`, so none of
   agency-intake-kit's 41 were needed. One real, synthetic mapping cassette (`f78025ac98e1...`,
   header "Hire Date") was copied to prove that a recorded cassette replays from a folder passed in
   explicitly and that the hash recipe is unchanged. A test greps every cassette here for
   Authorization, TYPESAFE_API_KEY, and Bearer (case-insensitive): zero hits. The same grep over all
   41 of agency-intake-kit's cassettes also found zero.
9. **Network off in tests.** plan-diff's `tests/conftest.py` refuses real socket connections.
10. **Import scan.** `tests/unit/test_no_intake_imports.py` parses every source file and fails on
    `import intake`, `from intake...`, or `import_module("intake...")`, and also on `bob_resolve` and
    `plan_diff`, so no app can become a dependency of shared code.

## Generator fidelity

`tests/reference/aik-fixture-hashes.json` holds the SHA-256 of all 39 files in agency-intake-kit's
`fixtures/agency-a` (17), `agency-a-ssn` (11), and `agency-a-truncated` (11), read with `git show`
at the source commit. `tests/reference/agency-a/drop/manifest.json` is a small readable copy.

`tests/unit/test_generator_fidelity.py` regenerates all three with the moved generator and compares
every hash. Result at C0a: **byte-identical, all 39 files.**

Copied tests that read fixture contents (`test_writers.py`, `test_injectors.py`) now read a fresh
regeneration (`tests/aik_reference.py`) that is refused unless every hash matches, so they check the
same bytes agency-intake-kit committed. Their own byte-for-byte assertions compare to the hashes.

## What C0b (in agency-intake-kit) needs to change

- Depend on `agency-data-commons @ git+https://github.com/alexmunzon/agency-data-commons@v0.1.0`
  (after the repo exists and the tag is pushed, both with Alex's yes), then `uv sync`.
- Delete `engine/src/{agency_schema,synth_agency_data,jev_client}`; drop the three from hatch
  `packages`; drop the `synth` script entry. Delete the moved unit tests except the byte-for-byte
  fixture tests in `test_writers.py` and `test_injectors.py` (PR 3a, 3b): keep those unedited as
  the safety net against the installed package.
- `DEFAULT_CASSETTE_DIR` no longer exists. `intake/cli.py`, `intake/mapping/jev_mapping.py`, and
  `intake/run/jev.py` import it today; give agency-intake-kit its own constant (for example
  `CASSETTE_DIR` in `intake/config.py`, pointing at `engine/tests/cassettes`).
- Keep `JEV_BUDGET_USD` in `intake/config.py`, delete the other `# PR 6` Jev constants, and pass
  `budget_usd` and `cassette_dir` to every `JevClient(...)`, `JevClient.from_env(...)`, and
  `RunJevClient(...)`: 37 call sites in src and tests today, many with neither argument.
- `RunJevClient` sets the private `_cassette_dir` per request. That still works in 0.1.0 but is a
  private detail; a public way to choose the folder per request is a candidate for a later version.
- Freeze shared-package edits in agency-intake-kit until C0b merges. Rollback: revert C0b.
