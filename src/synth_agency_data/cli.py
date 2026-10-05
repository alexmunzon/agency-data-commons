"""Command line entry point for the synthetic data generator."""

import json
from pathlib import Path
from typing import Annotated

import typer

from synth_agency_data import __version__
from synth_agency_data.canonical_writer import write_ground_truth, write_tables
from synth_agency_data.injectors import Defect, inject
from synth_agency_data.multi import (
    DEFAULT_B_CLIENTS,
    DEFAULT_OVERLAP,
    b_seed,
    build_agency_b,
    cross_agency_truth,
)
from synth_agency_data.world import build_world
from synth_agency_data.writers import write_drop

app = typer.Typer(help="Synthetic agency data generator.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Keep the app a command group."""


@app.command()
def version() -> None:
    """Print the generator version."""
    typer.echo(__version__)


@app.command()
def generate(
    out: Annotated[Path, typer.Option(help="Output folder, for example ../fixtures/agency-a.")],
    seed: Annotated[
        int, typer.Option(help="Random seed. The same seed gives identical files.")
    ] = 42,
    clients: Annotated[int, typer.Option(help="Number of clients.")] = 2000,
    inject_defects: Annotated[
        bool,
        typer.Option(
            "--inject/--no-inject",
            help="Plant SPEC examples 3 and 4 and inject labeled defects (needs seed 42). "
            "--no-inject writes the clean world to canonical/ instead.",
        ),
    ] = True,
    truncate_crm: Annotated[
        int | None,
        typer.Option(help="Keep only this many CRM data rows (SPEC example 5 uses 2574)."),
    ] = None,
    add_ssn_column: Annotated[
        bool, typer.Option(help="Add a fake SSN column to the roster (SPEC example 6).")
    ] = False,
    canonical: Annotated[
        bool, typer.Option("--canonical/--no-canonical", help="Also write the canonical CSVs.")
    ] = True,
) -> None:
    """Write drop/ (the four source shapes), canonical CSVs, and ground_truth.json."""
    world = build_world(seed=seed, n_clients=clients)
    defects: list[Defect] = []
    folder = "canonical"
    if inject_defects:
        try:
            world, defects = inject(world)
        except ValueError as error:
            raise typer.BadParameter(str(error)) from error
        folder = "canonical-defected"
    defects = write_drop(
        world, defects, out / "drop", truncate_crm, add_ssn_column, plant_pii=inject_defects
    )
    if canonical:
        write_tables(world, out / folder)
    write_ground_truth(world, out, defects)
    counts = ", ".join(f"{len(rows)} {name}" for name, rows in world.tables.items())
    typer.echo(f"Wrote {out}: {counts}, {len(defects)} defects")


@app.command("generate-multi")
def generate_multi(
    out: Annotated[Path, typer.Option(help="Output folder, for example ../fixtures/multi-a-b.")],
    seed: Annotated[int, typer.Option(help="Agency A's seed (42). Agency B uses seed + 1.")] = 42,
    agencies: Annotated[int, typer.Option(help="Number of agencies. Only 2 for now.")] = 2,
    overlap: Annotated[
        int, typer.Option(help="People held by both agencies (docs/c1-notes.md).")
    ] = DEFAULT_OVERLAP,
    b_clients: Annotated[int, typer.Option(help="Agency B clients.")] = DEFAULT_B_CLIENTS,
    agency_a: Annotated[
        bool,
        typer.Option(
            "--agency-a/--no-agency-a",
            help="Also write agency-a/ (exactly `synth generate --seed 42`).",
        ),
    ] = True,
) -> None:
    """Write agency-a/, agency-b/, and cross_agency_truth.json (the people both agencies hold)."""
    if agencies != 2:
        raise typer.BadParameter("only --agencies 2 is supported")
    a_clean = build_world(seed=seed, n_clients=2000)  # planting needs 2,000 clients
    try:
        a_world, a_defects = inject(a_clean)
        b, shared = build_agency_b(a_clean, a_world, b_seed(seed), b_clients, overlap)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    if agency_a:
        generate(out / "agency-a", seed=seed)
    folder = out / "agency-b"
    write_drop(b, [], folder / "drop", plant_pii=False)
    write_tables(b, folder / "canonical")
    write_ground_truth(b, folder, [])
    truth = cross_agency_truth(seed, b, shared, a_world, a_defects)
    text = json.dumps(truth, indent=2) + "\n"
    (out / "cross_agency_truth.json").write_text(text, encoding="utf-8")
    counts = ", ".join(f"{len(rows)} {name}" for name, rows in b.tables.items())
    typer.echo(f"Wrote {folder}: {counts}; {len(shared)} people shared with agency A")
