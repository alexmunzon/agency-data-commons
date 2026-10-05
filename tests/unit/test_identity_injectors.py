"""C2: harder identity cases in agency B, with pair, cluster, and must-not-merge truth."""

import json
from collections import Counter
from functools import cache
from typing import Any

import pytest
from test_multi_agency import _clients, generated, worlds

from synth_agency_data.identity import MUST_NOT_MERGE, RATES, STALE_COPY, inject_identity
from synth_agency_data.multi import Shared, build_agency_b
from synth_agency_data.world import Row, World

Labels = list[dict[str, Any]]


@cache
def clean_b() -> tuple[World, list[Shared]]:
    clean, final = worlds()
    return build_agency_b(clean, final, 43, 1500, 300)


def injected(rates: tuple[tuple[str, float], ...] | None = None) -> tuple[World, Labels, Labels]:
    clean, final = worlds()
    b, shared = clean_b()
    return inject_identity(clean, final, b, shared, dict(rates) if rates else None)


def _jsonl(name: str) -> Labels:
    lines = (generated() / name).read_text().splitlines()
    return [json.loads(line) for line in lines]


def _clusters() -> dict[str, list[str]]:
    clusters: dict[str, list[str]] = json.loads((generated() / "cluster_truth.json").read_text())
    return clusters


def test_each_injector_yields_at_least_15_scored_labels_with_keys_in_both_agencies() -> None:
    labels = json.loads((generated() / "agency-b" / "ground_truth.json").read_text())["defects"]
    counts = Counter(d["defect_type"] for d in labels)
    assert all(counts[kind] >= 15 for kind in RATES), counts
    assert counts[STALE_COPY] > 0
    for d in labels:
        assert d["scored"] is True and d["injected_values"] and d["source_row"]
        assert d["record_keys"]["agency-a"] and d["record_keys"]["agency-b"]
        lookalike = d["defect_type"] in set(MUST_NOT_MERGE) - {"shared_household_contact"}
        assert d["same_person"] is not lookalike


@pytest.mark.parametrize("kind", sorted(RATES))
def test_each_injector_changes_only_what_it_labels(kind: str) -> None:
    before = {c["client_id"]: c for c in clean_b()[0].tables["clients"]}
    world, labels, _ = injected(((kind, RATES[kind]),))
    assert {d["defect_type"] for d in labels} - {STALE_COPY} == {kind}
    assert len([d for d in labels if d["defect_type"] == kind]) >= 15
    touched = {k["client_id"] for d in labels for k in d["record_keys"]["agency-b"]}
    homes: dict[str, set[str]] = {}
    for h in world.tables["households"]:
        for m in h["members"]:
            homes[m] = set(h["members"])
    reach = touched | {m for cid in touched for m in homes.get(cid, ())}
    for c in world.tables["clients"]:
        if c != before.get(c["client_id"]):
            assert c["client_id"] in reach, (kind, c["client_id"])
    changed = {p["client_id"] for p in world.tables["policies"]} ^ {
        p["client_id"] for p in clean_b()[0].tables["policies"]
    }
    assert changed <= touched


def test_no_rates_means_no_change() -> None:
    world, labels, mnm = injected((("maiden_name", 0.0),))
    assert world == clean_b()[0] and labels == [] and mnm == []


def test_identity_injection_is_deterministic_by_seed() -> None:
    clean, final = worlds()
    first, second = injected(), injected()
    assert first == second
    b, shared = build_agency_b(clean, final, 50, 1500, 300)
    assert inject_identity(clean, final, b, shared)[1] != first[1]


def test_every_true_pair_resolves_and_sits_in_one_cluster() -> None:
    a, b = _clients("a"), _clients("b")
    clusters = _clusters()
    pairs = _jsonl("pair_truth.jsonl")
    assert (
        len(pairs)
        == json.loads((generated() / "cross_agency_truth.json").read_text())["counts"]["true_pairs"]
    )
    scopes = Counter(p["scope"] for p in pairs)
    assert scopes["cross"] >= 300 and scopes["within_b"] > 0
    for p in pairs:
        assert p["left"] in (a if p["scope"] == "cross" else b) and p["right"] in b
        assert {p["left"], p["right"]} <= set(clusters[p["person_id"]])
    kinds = Counter(k for p in pairs for k in p["defect_types"])
    same = ["maiden_name", "hyphenated_surname", "moved_household", "shared_household_contact"]
    assert all(kinds[k] >= 15 for k in [*same, "same_policy_two_member_ids"]), kinds
    assert not set(kinds) & (set(MUST_NOT_MERGE) - {"shared_household_contact"})


def test_must_not_merge_pairs_resolve_and_never_appear_as_true_pairs() -> None:
    a, b = _clients("a"), _clients("b")
    true = {frozenset((p["left"], p["right"])) for p in _jsonl("pair_truth.jsonl")}
    person = {r: pid for pid, ids in _clusters().items() for r in ids}
    mnm = _jsonl("must_not_merge.jsonl")
    counts = Counter(m["defect_type"] for m in mnm)
    assert set(counts) == set(MUST_NOT_MERGE) and min(counts.values()) >= 15, counts
    for m in mnm:
        assert m["left"] in a or m["left"] in b
        assert m["right"] in b and m["reason"] == MUST_NOT_MERGE[m["defect_type"]]
        assert frozenset((m["left"], m["right"])) not in true
        assert person[m["left"]] != person[m["right"]]
    cross = sum(m["left"] in a for m in mnm)
    assert 0 < cross < len(mnm)  # look-alikes both across agencies and within B


def test_lookalikes_really_look_alike() -> None:
    a, b = _clients("a"), _clients("b")
    # A's side as its true (clean) values: A's own defects may make it read "Bob" for "Robert"
    clean = {
        c["client_id"]: {k: str(v or "") for k, v in c.items()}
        for c in worlds()[0].tables["clients"]
    }
    rows = a | b
    for m in _jsonl("must_not_merge.jsonl"):
        x, y = clean.get(m["left"], rows[m["left"]]), rows[m["right"]]
        same = {f for f in ("first_name", "last_name", "dob", "zip") if x[f] == y[f]}
        if m["defect_type"] == "name_dob_lookalike":
            assert {"first_name", "last_name", "dob"} <= same and "zip" not in same
            assert x["mbi"] != y["mbi"] or not x["mbi"]  # ACA clients have no MBI
        elif m["defect_type"] == "father_son_same_name" and m["left"] in b:
            assert {"first_name", "last_name"} <= same
            assert abs(int(x["dob"][:4]) - int(y["dob"][:4])) >= 21
        elif m["defect_type"] == "twin_lookalike" and m["left"] in b:
            assert {"last_name", "dob"} <= same and x["first_name"] != y["first_name"]
        elif m["defect_type"] == "shared_household_contact" and m["left"] in b:
            assert (x["phone"], x["email"], x["zip"]) == (y["phone"], y["email"], y["zip"])


def test_cluster_truth_is_a_partition_of_every_client_id_in_both_agencies() -> None:
    a, b = _clients("a"), _clients("b")
    ids = [r for members in _clusters().values() for r in members]
    assert len(ids) == len(set(ids)) and set(ids) == set(a) | set(b)


def test_shared_people_no_longer_all_live_alone_in_b() -> None:
    truth = json.loads((generated() / "cross_agency_truth.json").read_text())
    sizes = [p["agency_b"]["household_size"] for p in truth["people"]]
    share = sum(s > 1 for s in sizes) / len(sizes)
    assert 0.35 <= share <= 0.65, share
    assert truth["counts"]["shared_people_living_with_others_in_b"] == sum(s > 1 for s in sizes)
    homes: dict[str, Row] = {}
    for h in clean_b()[0].tables["households"]:
        homes |= dict.fromkeys(h["members"], h)
    placed = [len(homes[s.b_client_id]["members"]) > 1 for s in clean_b()[1]]
    assert sum(placed) / len(placed) >= 0.35  # before C2 adds twins, sons, and children
