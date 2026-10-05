"""C1: a second agency that shares a known set of real people with agency A."""

import atexit
import csv
import json
import shutil
import tempfile
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from aik_reference import digest, reference_hashes
from typer.testing import CliRunner

from agency_schema.formats import normalize_name
from agency_schema.models import TABLE_MODELS
from synth_agency_data.cli import app
from synth_agency_data.identity import RATES, STALE_COPY, inject_identity
from synth_agency_data.injectors import inject
from synth_agency_data.multi import ADDRESS_FIELDS, IDENTITY_FIELDS, build_agency_b
from synth_agency_data.planted import ORPHAN_MEMBER, PLANTED_NPN, PLANTED_POLICY
from synth_agency_data.world import AS_OF, World, build_world

FIXTURE = Path(__file__).parents[2] / "fixtures" / "multi-a-b"
Rows = list[dict[str, str]]


@cache
def generated() -> Path:
    root = Path(tempfile.mkdtemp(prefix="commons-multi-"))
    atexit.register(shutil.rmtree, root, ignore_errors=True)
    result = CliRunner().invoke(app, ["generate-multi", "--seed", "42", "--out", str(root)])
    assert result.exit_code == 0, result.output
    return root


@cache
def worlds() -> tuple[World, World]:
    clean = build_world(seed=42, n_clients=2000)
    return clean, inject(clean)[0]


def _csv(path: Path) -> Rows:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _truth() -> dict[str, Any]:
    truth: dict[str, Any] = json.loads((generated() / "cross_agency_truth.json").read_text())
    return truth


def _clients(agency: str) -> dict[str, dict[str, str]]:
    folder = "canonical-defected" if agency == "a" else "canonical"
    rows = _csv(generated() / f"agency-{agency}" / folder / "clients.csv")
    return {r["client_id"]: r for r in rows}


def test_agency_a_is_todays_seed_42_world_byte_for_byte() -> None:
    assert digest(generated() / "agency-a") == reference_hashes("agency-a")


def test_committed_fixture_is_the_regeneration_without_agency_a() -> None:
    expected = {k: v for k, v in digest(generated()).items() if not k.startswith("agency-a/")}
    assert {k: v for k, v in digest(FIXTURE).items() if k != "README.md"} == expected


def test_agency_b_is_deterministic_by_seed() -> None:
    clean, final = worlds()
    first, second = (build_agency_b(clean, final, 50, 300, 40) for _ in range(2))
    other = build_agency_b(clean, final, 51, 300, 40)
    assert first == second and first[0].tables != other[0].tables
    # seeds 50 and 51 draw member ids that agency A also uses; each moved to a free number
    a_members = {p["carrier_member_id"] for p in final.tables["policies"]}
    for b_world, _ in (first, other):
        b_members = [p["carrier_member_id"] for p in b_world.tables["policies"]]
        assert len(set(b_members)) == len(b_members) and not a_members & set(b_members)


def test_exactly_the_stated_number_of_people_are_shared() -> None:
    truth = _truth()
    assert truth["counts"]["shared_people"] == len(truth["people"]) == 300
    assert len({p["agency_b"]["client_ids"][0] for p in truth["people"]}) == 300
    assert len({p["agency_a"]["client_ids"][0] for p in truth["people"]}) == 300
    # C2 adds B-only look-alike people (twins, sons, children) and B copies of moved people
    clusters = json.loads((generated() / "cluster_truth.json").read_text())
    assert truth["counts"]["distinct_people"] == len(clusters) > 2000 + 1500 - 300
    clean, final = worlds()
    assert len(build_agency_b(clean, final, 50, 300, 40)[1]) == 40
    with pytest.raises(ValueError, match="at most"):
        build_agency_b(clean, final, 50, 100, 90)


def test_only_two_agencies_are_supported(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["generate-multi", "--agencies", "3", "--out", str(tmp_path)])
    assert result.exit_code != 0


def test_every_shared_id_resolves_in_both_agencies() -> None:
    a, b = _clients("a"), _clients("b")
    for person in _truth()["people"]:
        assert person["agency_a"]["client_ids"] and person["agency_b"]["client_ids"]
        assert all(cid in a for cid in person["agency_a"]["client_ids"])
        assert all(cid in b for cid in person["agency_b"]["client_ids"])


def test_shared_people_carry_their_true_identity_and_address_into_b() -> None:
    """Except the fields a C2 injector changed in B, each labeled on that person."""
    clean = {c["client_id"]: c for c in worlds()[0].tables["clients"]}
    b = _clients("b")
    for person in _truth()["people"]:
        truth_row = clean[person["agency_a"]["client_ids"][0]]
        b_row = b[person["agency_b"]["client_ids"][0]]
        changed = {f for x in person["agency_b"]["labels"] for f in x["fields"]}
        for field in set(IDENTITY_FIELDS + ADDRESS_FIELDS) - changed:
            value = truth_row[field]
            assert b_row[field] == (value.isoformat() if isinstance(value, date) else value or "")


def test_identity_differences_across_agencies_are_all_labeled() -> None:
    a, b = _clients("a"), _clients("b")
    labeled = 0
    for person in _truth()["people"]:
        b_row = b[person["agency_b"]["client_ids"][0]]
        for cid in person["agency_a"]["client_ids"]:
            differs = {f for f in IDENTITY_FIELDS + ADDRESS_FIELDS if a[cid][f] != b_row[f]}
            allowed = {
                f
                for x in person["agency_a"]["labels"] + person["agency_b"]["labels"]
                if x["client_id"] in (cid, b_row["client_id"])
                for f in x["fields"]
            }
            assert differs <= allowed, (person["person_id"], cid, differs)
            labeled += bool(differs)
    assert labeled > 0  # some shared people do read differently, and each is labeled


def test_nothing_planted_in_b_only_c2_identity_cases_and_no_id_collides_with_a() -> None:
    root = generated() / "agency-b"
    defects = json.loads((root / "ground_truth.json").read_text())["defects"]
    assert {d["defect_type"] for d in defects} == set(RATES) | {STALE_COPY}
    a_root = generated() / "agency-a" / "canonical-defected"
    for table, field in [
        ("clients", "client_id"),
        ("households", "household_id"),
        ("policies", "policy_id"),
        ("policies", "carrier_member_id"),
        ("agents", "npn"),
    ]:
        b_ids = {r[field] for r in _csv(root / "canonical" / f"{table}.csv")}
        assert not b_ids & {r[field] for r in _csv(a_root / f"{table}.csv")}, (table, field)
        assert not b_ids & {PLANTED_POLICY, PLANTED_NPN, ORPHAN_MEMBER}
    lines = _csv(root / "canonical" / "commission_lines.csv")
    assert all(ln["policy_ref"] and ln["carrier_member_id"] != ORPHAN_MEMBER for ln in lines)


@pytest.mark.parametrize("injected", [False, True])
def test_agency_b_is_a_consistent_book(injected: bool) -> None:
    """Clean B (C1) and B with the C2 identity cases keep every invariant of a real book.
    Stale copies (a mover's old record) have no household and no policy, like A's copies."""
    clean, final = worlds()
    b, shared = build_agency_b(clean, final, 43, 1500, 300)
    t = inject_identity(clean, final, b, shared)[0].tables if injected else b.tables
    clients = {c["client_id"]: c for c in t["clients"] if c["household_id"]}
    policies = {p["policy_id"]: p for p in t["policies"]}
    npns = {a["npn"]: set(a["license_states"]) for a in t["agents"]}
    assert len(t["clients"]) == 1500 + 60 * injected and len(policies) == len(t["policies"])
    rts = {
        (r["npn"], r["carrier"], r["state"], r["plan_year"], r["line_of_business"])
        for r in t["rts"]
    }
    keys = {
        (normalize_name(f"{c['first_name']} {c['last_name']}"), c["dob"]) for c in clients.values()
    }
    assert len(keys) == len(clients)
    assert sorted(m for h in t["households"] for m in h["members"]) == sorted(clients)
    assert all(
        clients[m]["household_id"] == h["household_id"]
        for h in t["households"]
        for m in h["members"]
    )
    assert all(a["upline_npn"] is None or a["upline_npn"] in npns for a in t["agents"])
    for p in policies.values():
        c = clients[p["client_id"]]
        assert p["state"] == c["state"] in npns[p["writing_agent_npn"]]
        assert (
            p["writing_agent_npn"],
            p["carrier"],
            p["state"],
            p["effective_date"].year,
            p["line_of_business"],
        ) in rts
        age = (
            p["effective_date"].year
            - c["dob"].year
            - (
                (p["effective_date"].month, p["effective_date"].day)
                < (c["dob"].month, c["dob"].day)
            )
        )
        if p["eligibility_reason"] == "AGE":
            assert age >= 65
        elif p["eligibility_reason"]:
            assert age < 65
        else:
            assert c["mbi"] is None and AS_OF.year - c["dob"].year <= 65
    for ln in t["commission_lines"]:
        p, c = policies[ln["policy_ref"]], clients[policies[ln["policy_ref"]]["client_id"]]
        assert ln["carrier_member_id"] == p["carrier_member_id"]
        assert (
            ln["member_name"] == f"{c['first_name']} {c['last_name']}"
            and ln["member_dob"] == c["dob"]
        )
    for table, model in TABLE_MODELS.items():
        lineage = {
            "source_file": table,
            "sheet": None,
            "row_number": 2,
            "raw_hash": "0" * 64,
            "run_id": "t",
            "mapping_version": "c",
        }
        for row in t[table]:
            model.model_validate({**row, "lineage": lineage})
