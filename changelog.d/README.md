# Changelog fragments

Each PR adds one fragment file here instead of editing CHANGELOG.md. This stops parallel PRs from
fighting over the same lines in one file.

- One fragment file per PR, named `cNN-short-name.md` (for example `c01-second-agency.md`).
- Start it with a heading `## C0a: Short title (YYYY-MM-DD)`, then a few plain-language bullets.
- Say whether the change is breaking for a consumer (docs/versioning.md decides the version bump).
- At release, the fragments are assembled into CHANGELOG.md in PR order and then deleted from here.
