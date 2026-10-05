# Versioning

How agency-data-commons is released and how the other repos depend on it. Decided in bob-resolve
SPEC decision 6 and the bob-resolve kickoff handoff, section 3.

## One version for all three packages

`agency_schema`, `synth_agency_data`, and `jev_client` ship together in one distribution,
`agency-data-commons`, with one version number. It is set in `pyproject.toml` and repeated as
`__version__` in each package; a test checks they agree. Bump all of them together.

## Releases are git tags

A release is a git tag `vX.Y.Z` on `main`, for example `v0.1.0`. There is no PyPI package. Only the
orchestrator creates tags, after `npm run verify` is green and Alex has said yes.

## Consumers pin an exact tag

Each consumer pins one exact tag in its `pyproject.toml`, and its `uv.lock` pins the commit:

```toml
dependencies = [
    "agency-data-commons @ git+https://github.com/alexmunzon/agency-data-commons@v0.1.0",
]
```

No ranges and no branch names. Upgrading is a deliberate PR in the consumer that changes the tag,
reruns `uv sync`, and runs that repo's full verify.

## Which number to bump (while in 0.x)

| Change | Bump | Example |
|---|---|---|
| Breaking: a model field renamed, removed, or retyped; a required argument added; a function removed | minor, 0.1.0 to 0.2.0 | `JevClient` gains a required argument |
| Generator output changes by even one byte for an existing seed | minor | a new injector at seed 42 |
| A `jev_client/config.py` default changes (URL, model, price, retries) | minor | the price per million tokens changes |
| Fix or addition that keeps every existing caller and fixture identical | patch, 0.1.0 to 0.1.1 | a new optional helper |

Every breaking change gets a line in its changelog fragment saying what callers must change.
After 1.0.0, breaking changes bump the major version instead.

## Pinned dependencies

`faker` and `openpyxl` are pinned exactly in `pyproject.toml`, because a different version can
change the bytes the generator writes. Changing either pin follows the generator-output row above.
