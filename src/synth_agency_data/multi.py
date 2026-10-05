"""Two agencies whose books overlap by a known set of real people (commons C1).

Agency A is exactly the seed-42 world (planted records, injected defects), untouched. Agency B
is a clean world built from its own seed, then:

1. Re-keyed: every client, household, and policy id gets the prefix "B-" and agent emails move
   to their own domain. A carrier member id that also exists in agency A (including A's planted
   HL-998213) moves to the next free number. NPNs that collide with A refuse the seed.
2. Overlapped: `overlap` people from agency A's clean world are placed into B. Each takes over
   one B client who lives alone, in the same state, with the same Medicare or ACA status and
   eligibility reason, and whose policies started after that person turned 65 (when the reason
   is age). The B client gets the person's true identity (name, birth date, MBI) and address,
   so nobody moves. Phone stays B's; email is rebuilt from the new name, so it differs from A's.

Agency A's identity defects are A's own labels: a shared person may read "Dave" in A's CRM and
"David" in B. The cross-agency truth lists those labels next to each person.
"""

import random
from dataclasses import dataclass, replace
from typing import Any

from agency_schema.formats import normalize_name
from synth_agency_data.injectors.base import Defect
from synth_agency_data.planted import ORPHAN_MEMBER, PLANTED_NPN
from synth_agency_data.world import (
    Row,
    World,
    _first_month_at_65,
    build_world,
    commission_lines,
)

B_PREFIX = "B-"
B_EMAIL_DOMAIN = "agency-b.example.com"
DEFAULT_OVERLAP = 300
DEFAULT_B_CLIENTS = 1500
MULTI_HOUSEHOLD_SHARE = 0.4  # of shared people, placed with a housemate in B (C2)
IDENTITY_FIELDS = ("first_name", "last_name", "dob", "mbi")
ADDRESS_FIELDS = ("address_line1", "city", "state", "zip")


@dataclass(frozen=True)
class Shared:
    """One real person held by both agencies."""

    person_id: str
    a_client_id: str  # the original A client; A's copies are found through copy_of
    b_client_id: str


def b_seed(seed: int) -> int:
    return seed + 1


def _rekey(b: World, a: World) -> World:
    t = b.tables
    a_npns = {x["npn"] for x in a.tables["agents"]} | {PLANTED_NPN}
    a_npns |= {p["writing_agent_npn"] for p in a.tables["policies"]}
    if a_npns & {x["npn"] for x in t["agents"]}:
        raise ValueError("agency B's NPNs collide with agency A (try another seed)")
    # Member ids are 6 random digits per carrier, so a few B ids can match A's by chance (about
    # one per 2,000 B policies). Each one moves to the next free number.
    taken = {p["carrier_member_id"] for w in (a, b) for p in w.tables["policies"]}
    a_members = {p["carrier_member_id"] for p in a.tables["policies"]} | {ORPHAN_MEMBER}
    members: dict[str, str] = {}
    for old in sorted({p["carrier_member_id"] for p in t["policies"]} & a_members):
        prefix, number = old.split("-")
        new = next(
            f"{prefix}-{n}" for n in range(int(number), 10**6) if f"{prefix}-{n}" not in taken
        )
        taken.add(new)
        members[old] = new

    def bk(value: str | None) -> str | None:
        return B_PREFIX + value if value else value

    agents = [
        {**x, "email": x["email"].replace("example.com", B_EMAIL_DOMAIN)} for x in t["agents"]
    ]
    clients = [
        {**c, "client_id": bk(c["client_id"]), "household_id": bk(c["household_id"])}
        for c in t["clients"]
    ]
    households = [
        {
            **h,
            "household_id": bk(h["household_id"]),
            "primary_client_id": bk(h["primary_client_id"]),
            "members": tuple(B_PREFIX + m for m in h["members"]),
        }
        for h in t["households"]
    ]
    policies = [
        {
            **p,
            "policy_id": bk(p["policy_id"]),
            "client_id": bk(p["client_id"]),
            "carrier_member_id": members.get(p["carrier_member_id"], p["carrier_member_id"]),
        }
        for p in t["policies"]
    ]
    tables = {**t, "agents": agents, "clients": clients, "households": households}
    tables |= {"policies": policies, "commission_lines": commission_lines(policies, clients)}
    return replace(b, tables=tables)


def _profile(client: Row, policies: list[Row]) -> tuple[Any, ...]:
    """What a person must share with the B client they replace: state, Medicare, reason."""
    reasons = {p["eligibility_reason"] for p in policies}
    return client["state"], client["mbi"] is not None, tuple(sorted(str(r) for r in reasons))


def _email(row: Row, first: str, last: str) -> str | None:
    """Rebuild an email from a name and the row number in the client id, as build_world does."""
    slug = "".join(ch for ch in f"{first}.{last}".lower() if ch.isalnum() or ch == ".")
    return f"{slug}{int(row['client_id'][-5:])}@example.com" if row["email"] else None


def _key(c: Row) -> tuple[str, Any]:
    return normalize_name(f"{c['first_name']} {c['last_name']}"), c["dob"]


def _overlap(a: World, b: World, overlap: int, seed: int) -> tuple[World, list[Shared]]:
    rng = random.Random(f"overlap-{seed}")
    held: dict[str, list[Row]] = {}
    for w in (a, b):
        for p in w.tables["policies"]:
            held.setdefault(p["client_id"], []).append(p)
    b_rows = {c["client_id"]: dict(c) for c in b.tables["clients"]}
    home = {m: h["members"] for h in b.tables["households"] for m in h["members"]}
    # open_b[multi][profile]: B clients a shared person may replace. Multi means the client lives
    # with others (a spouse or an adult child), so shared people are not all living alone (C2).
    open_b: dict[bool, dict[tuple[Any, ...], list[str]]] = {False: {}, True: {}}
    for cid in b_rows:
        open_b[len(home[cid]) > 1].setdefault(_profile(b_rows[cid], held[cid]), []).append(cid)
    keys = {_key(c) for c in b_rows.values()}
    a_people = list(a.tables["clients"])
    rng.shuffle(a_people)
    chosen: dict[str, Row] = {}  # b client id: the A person who replaces them
    for person in a_people:
        if len(chosen) == overlap:
            break
        want_multi = rng.random() < MULTI_HOUSEHOLD_SHARE
        if person["client_id"] not in held or _key(person) in keys:
            continue
        for multi in (want_multi, not want_multi):
            cid = _place(
                person,
                open_b[multi].get(_profile(person, held[person["client_id"]]), []),
                held,
                home,
                b_rows,
                keys,
            )
            if cid:
                chosen[cid] = person
                for other in home[cid]:  # one shared person per household
                    for pool in open_b[multi].values():
                        if other in pool:
                            pool.remove(other)
                break
    if len(chosen) < overlap:
        raise ValueError(f"agency B can share at most {len(chosen)} people with agency A")
    for cid, new in chosen.items():
        c = b_rows[cid]
        b_rows[cid] = {**c, **{f: new[f] for f in IDENTITY_FIELDS + ADDRESS_FIELDS}}
        b_rows[cid]["email"] = _email(c, new["first_name"], new["last_name"])
    clients = [b_rows[c["client_id"]] for c in b.tables["clients"]]
    pairs = sorted((p["client_id"], cid) for cid, p in chosen.items())
    shared = [Shared(f"PER-{i:05d}", a_id, b_id) for i, (a_id, b_id) in enumerate(pairs, start=1)]
    lines = commission_lines(b.tables["policies"], clients)
    return replace(b, tables={**b.tables, "clients": clients, "commission_lines": lines}), shared


def _place(
    person: Row,
    candidates: list[str],
    held: dict[str, list[Row]],
    home: dict[str, tuple[str, ...]],
    b_rows: dict[str, Row],
    keys: set[tuple[str, Any]],
) -> str | None:
    """The first candidate the person can replace. Housemates take the person's surname and address
    (one household, one address); a housemate whose new name and birth date are taken refuses."""
    for cid in candidates:
        starts = min(p["effective_date"] for p in held[cid])
        if "AGE" in str(held[cid][0]["eligibility_reason"]) and (
            _first_month_at_65(person["dob"]) > starts
        ):
            continue
        mates = [m for m in home[cid] if m != cid]
        moved = [
            {
                **b_rows[m],
                "last_name": person["last_name"],
                **{f: person[f] for f in ADDRESS_FIELDS},
            }
            for m in mates
        ]
        new_keys = {_key(m) for m in moved}
        if len(new_keys) < len(moved) or new_keys & (keys - {_key(b_rows[m]) for m in mates}):
            continue
        for m in mates:
            keys.discard(_key(b_rows[m]))
        for row in moved:
            row["email"] = _email(row, row["first_name"], row["last_name"])
            b_rows[row["client_id"]] = row
        keys |= new_keys | {_key(person)}
        candidates.remove(cid)
        return cid
    return None


def build_agency_b(
    a_clean: World, a_final: World, seed: int, n_clients: int, overlap: int
) -> tuple[World, list[Shared]]:
    """Agency B from its own seed, sharing `overlap` people with agency A.

    People come from A's clean world (their true identity). Ids are kept apart from every id in
    A's final world (`a_final`, after planting and injection).
    """
    if overlap < 0:
        raise ValueError("overlap must be 0 or more")
    b = _rekey(build_world(seed=seed, n_clients=n_clients), a_final)
    return _overlap(a_clean, b, overlap, seed)


def cross_agency_truth(
    a_seed: int, b: World, shared: list[Shared], a_world: World, a_defects: list[Defect]
) -> dict[str, Any]:
    """Person id to client ids in each agency, A's labels on those ids, and counts."""
    copies: dict[str, list[str]] = {}
    labels: dict[str, list[dict[str, Any]]] = {}
    for d in a_defects:
        if d["source"] != "clients":
            continue
        cid = d["record_key"]["client_id"]
        v = d["injected_values"]
        if "copy_of" in v:
            copies.setdefault(v["copy_of"], []).append(cid)
        # The fields this defect changed: an edit names one; a copy may carry a new last name.
        fields = [v["field"]] if "field" in v else [k for k in v if k in IDENTITY_FIELDS]
        labels.setdefault(cid, []).append(
            {"client_id": cid, "defect_type": d["defect_type"], "fields": fields}
        )
    a_rows = {c["client_id"]: c for c in a_world.tables["clients"]}
    b_rows = {c["client_id"]: c for c in b.tables["clients"]}
    people = []
    for s in shared:
        a_ids = [s.a_client_id, *copies.get(s.a_client_id, [])]
        contact = [
            f for f in ("phone", "email") if a_rows[s.a_client_id][f] != b_rows[s.b_client_id][f]
        ]
        people.append(
            {
                "person_id": s.person_id,
                "agency_a": {
                    "client_ids": a_ids,
                    "labels": [x for i in a_ids for x in labels.get(i, [])],
                },
                "agency_b": {"client_ids": [s.b_client_id], "labels": []},
                "contact_differs": contact,
            }
        )
    a_n, b_n = len(a_world.tables["clients"]), len(b.tables["clients"])
    a_people = a_n - sum(len(v) for v in copies.values())
    return {
        "agencies": {"agency-a": {"seed": a_seed}, "agency-b": {"seed": b.seed}},
        "counts": {
            "shared_people": len(shared),
            "agency_a_client_ids": a_n,
            "agency_b_client_ids": b_n,
            "agency_b_people": b_n,  # B is clean: one client id per person
            "distinct_people": a_people + b_n - len(shared),
        },
        "people": people,
    }
