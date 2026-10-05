"""Harder identity cases in agency B (commons C2), the held-out test for bob-resolve.

Agency A is never touched. Every injector edits agency B after C1's overlap and labels each
instance: defect_type, scored true, the record keys in both agencies, and the injected values.
Same-person injectors change how a shared person reads in B. Must-not-merge injectors make a B
client look like someone they are not. Each shared person anchors at most one injector, so every
label is unambiguous. Rates are shares of the shared people (300 by default).
"""

import json
import random
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path
from typing import Any

from faker import Faker
from faker.providers.person.en_US import Provider as Names

from agency_schema.enums import LineOfBusiness as Lob
from agency_schema.enums import PolicyStatus
from agency_schema.formats import zip3_table
from synth_agency_data.injectors.base import Defect, defect
from synth_agency_data.multi import Shared, _email, _key, _profile, a_copies
from synth_agency_data.world import (
    AS_OF,
    Row,
    World,
    _dob,
    _first_month_at_65,
    _mbi,
    commission_lines,
)

RATES: dict[str, float] = {
    "maiden_name": 0.07,
    "hyphenated_surname": 0.06,
    "moved_household": 0.08,
    "shared_household_contact": 0.07,
    "same_policy_two_member_ids": 0.06,
    "child_on_parent_policy": 0.06,
    "name_dob_lookalike": 0.06,
    "twin_lookalike": 0.06,
    "father_son_same_name": 0.06,
}
STALE_COPY = "moved_household_stale_copy"  # the old B record kept after a move (same person)
STALE_COPY_SHARE = 1 / 3
MUST_NOT_MERGE = {
    "child_on_parent_policy": "a dependent child on the parent's policy: same surname, address, "
    "phone, and member id stem",
    "name_dob_lookalike": "a different person with the same name and birth date in another ZIP",
    "twin_lookalike": "a twin in the same household: near-identical first name, same birth date",
    "father_son_same_name": "father and son with the same name and no suffix, born decades apart",
    "shared_household_contact": "spouses who share a surname, address, phone, and email",
}
_PAIRS = (
    ("Mario", "Maria"),
    ("Daniel", "Danielle"),
    ("Michael", "Michelle"),
    ("Paul", "Paula"),
    ("Eric", "Erica"),
    ("Robert", "Roberta"),
    ("Brian", "Briana"),
    ("Christian", "Christina"),
    ("Stephen", "Stephanie"),
    ("Andrew", "Andrea"),
    ("Patrick", "Patricia"),
    ("Carl", "Carla"),
    ("Francis", "Frances"),
    ("Gabriel", "Gabriela"),
    ("Joel", "Joelle"),
    ("Dennis", "Denise"),
    ("Alexander", "Alexandra"),
    ("Kristopher", "Kristina"),
    ("Julian", "Juliana"),
)
TWINS = {a: b for x, y in _PAIRS for a, b in ((x, y), (y, x))}
ADDRESS = ("address_line1", "city", "zip")


@dataclass
class _Book:
    rng: random.Random
    fake: Faker
    clients: dict[str, Row]
    households: dict[str, Row]
    policies: list[Row]
    shared: dict[str, str]  # person id: B client id
    a_ids: dict[str, str]  # person id: A client id
    member_ids: set[str]
    keys: set[tuple[str, Any]]
    next_policy: int
    used: set[str] = field(default_factory=set)
    labels: list[Defect] = field(default_factory=list)
    mnm: list[dict[str, str]] = field(default_factory=list)  # b client id, anchor record id
    unpaid: set[str] = field(default_factory=set)  # dependents' policy ids

    def mates(self, cid: str) -> list[str]:
        hid = self.clients[cid]["household_id"]
        return [m for m in self.households[hid]["members"] if m != cid] if hid else []

    def held(self, cid: str) -> list[Row]:
        return [p for p in self.policies if p["client_id"] == cid]

    def anchors(self, n: int, ok: Any) -> list[tuple[str, Row]]:
        people = [
            (pid, self.clients[b])
            for pid, b in sorted(self.shared.items())
            if b not in self.used and ok(self.clients[b])
        ]
        picks = sorted(self.rng.sample(people, min(n, len(people))), key=lambda x: x[0])
        self.used |= {r["client_id"] for _, r in picks}
        return picks

    def edit(self, cid: str, **changes: Any) -> Row:
        old = self.clients[cid]
        new = {**old, **changes}
        if "last_name" in changes or "first_name" in changes:
            new["email"] = _email(old, new["first_name"], new["last_name"])
        self.keys.discard(_key(old))
        self.keys.add(_key(new))
        self.clients[cid] = new
        return new

    def add(self, row: Row, household: bool = True) -> str:
        cid = f"B-C-{len(self.clients) + 1:05d}"
        self.clients[cid] = {**row, "client_id": cid}
        if household and row["household_id"]:
            h = self.households[row["household_id"]]
            self.households[row["household_id"]] = {**h, "members": (*h["members"], cid)}
        if household:
            self.keys.add(_key(self.clients[cid]))
        return cid

    def member_id(self, carrier_id: str) -> str:
        prefix = carrier_id.split("-")[0]
        while (new := f"{prefix}-{self.rng.randint(100000, 999999)}") in self.member_ids:
            pass
        self.member_ids.add(new)
        return new

    def copy_policies(self, policies: list[Row], cid: str, **changes: Any) -> list[Row]:
        out = []
        for p in policies:
            new = {
                **p,
                "client_id": cid,
                "carrier_member_id": self.member_id(p["carrier_member_id"]),
            }
            new |= {"policy_id": f"B-P-{self.next_policy:05d}", **changes}
            self.next_policy += 1
            self.policies.append(new)
            out.append(new)
        return out

    def label(
        self,
        kind: str,
        key: dict[str, str],
        anchor: str,
        a_keys: list[dict[str, str]],
        b_keys: list[dict[str, str]],
        fields: list[str],
        **values: Any,
    ) -> None:
        d = defect(kind, "policies" if "policy_id" in key else "clients", key, None, **values)
        same = kind not in MUST_NOT_MERGE or kind == "shared_household_contact"
        d |= {"scored": True, "same_person": same, "anchor_client_id": anchor, "fields": fields}
        self.labels.append(d | {"record_keys": {"agency-a": a_keys, "agency-b": b_keys}})

    def free_surname(self, rows: list[str], make: Any) -> tuple[str, ...]:
        while True:
            names = make(self.fake.last_name())
            if names[0] != self.clients[rows[0]]["last_name"]:
                trial = [{**self.clients[r], "last_name": names[i > 0]} for i, r in enumerate(rows)]
                if not {_key(t) for t in trial} & self.keys:
                    return tuple(names)


def _a_key(book: _Book, pid: str) -> list[dict[str, str]]:
    return [{"client_id": book.a_ids[pid]}]


def _surname(book: _Book, n: int, kind: str) -> None:
    """maiden_name: B has the married name (housemates too). hyphenated_surname: B has
    Garcia-Lopez or Lopez-Garcia where A has Garcia; housemates have Lopez."""
    female = set(Names.first_names_female)
    ok = (lambda c: c["first_name"] in female) if kind == "maiden_name" else (lambda c: True)
    for pid, c in book.anchors(n, ok):
        old, rows = c["last_name"], [c["client_id"], *book.mates(c["client_id"])]
        if kind == "maiden_name":
            new, mate = book.free_surname(rows, lambda s: (s, s))
        else:
            first = book.rng.random() < 0.5
            new, mate = book.free_surname(
                rows, lambda s, f=first, o=old: (f"{o}-{s}" if f else f"{s}-{o}", s)
            )
        book.edit(c["client_id"], last_name=new)
        for m in rows[1:]:
            book.edit(m, last_name=mate)
        b_key = {"client_id": c["client_id"]}
        book.label(
            kind,
            b_key,
            c["client_id"],
            _a_key(book, pid),
            [b_key],
            ["last_name"],
            a_last_name=old,
            b_last_name=new,
        )


def moved_household(book: _Book, n: int) -> None:
    """A new address in B for the person and housemates (half the time a new ZIP3, same state).
    A third of movers also keep their old B record, a same-person copy within agency B."""
    table = zip3_table()
    for pid, c in book.anchors(n, lambda c: True):
        old, rng = dict(c), book.rng
        prefixes = sorted(z for z, states in table.items() if c["state"] in states)
        others = [z for z in prefixes if z != c["zip"][:3]]
        zip3 = rng.choice(others) if others and rng.random() < 0.5 else c["zip"][:3]
        while (new_zip := f"{zip3}{rng.randrange(100):02d}") == c["zip"]:
            pass
        moved = {"address_line1": book.fake.street_address(), "city": book.fake.city()}
        moved["zip"] = new_zip
        for m in [c["client_id"], *book.mates(c["client_id"])]:
            book.edit(m, **moved)
        b_key = {"client_id": c["client_id"]}
        book.label(
            "moved_household",
            b_key,
            c["client_id"],
            _a_key(book, pid),
            [b_key],
            list(ADDRESS),
            **{f"from_{f}": old[f] for f in ADDRESS},
            **{f"to_{f}": moved[f] for f in ADDRESS},
        )
        if rng.random() < STALE_COPY_SHARE:
            stale = book.add({**old, "household_id": None, "email": None}, household=False)
            book.label(
                STALE_COPY,
                {"client_id": stale},
                c["client_id"],
                _a_key(book, pid),
                [{"client_id": stale}, b_key],
                [],
                copy_of=c["client_id"],
            )


def shared_household_contact(book: _Book, n: int) -> None:
    """The person uses the spouse's phone and email in B (a joint email when the spouse had none).
    The spouse is a different person who now matches on surname, address, phone, and email."""
    for pid, c in book.anchors(n, lambda c: bool(book.mates(c["client_id"]))):
        mate = book.clients[book.mates(c["client_id"])[0]]
        slug = "".join(ch for ch in c["last_name"].lower() if ch.isalnum())
        email = mate["email"] or f"{slug}.family{int(mate['client_id'][-5:])}@example.com"
        book.clients[mate["client_id"]] = {**mate, "email": email}
        book.clients[c["client_id"]] = {**c, "phone": mate["phone"], "email": email}
        b_key = {"client_id": c["client_id"]}
        book.label(
            "shared_household_contact",
            b_key,
            c["client_id"],
            _a_key(book, pid),
            [b_key, {"client_id": mate["client_id"]}],
            ["phone", "email"],
            spouse_client_id=mate["client_id"],
            phone=mate["phone"],
            email=email,
            from_phone=c["phone"],
            from_email=c["email"],
        )
        book.mnm.append(
            {
                "client_id": mate["client_id"],
                "anchor": c["client_id"],
                "defect_type": "shared_household_contact",
            }
        )


def same_policy_two_member_ids(book: _Book, n: int, a_policies: dict[str, list[Row]]) -> None:
    """B's policies for the person become A's policies (same carrier, plan, and dates, written by
    B's agent) under new carrier member ids. One label per policy."""
    for pid, c in book.anchors(n, lambda c: True):
        cid = c["client_id"]
        npn = book.held(cid)[0]["writing_agent_npn"]
        book.policies = [p for p in book.policies if p["client_id"] != cid]
        for ap in a_policies[book.a_ids[pid]]:
            (bp,) = book.copy_policies([ap], cid, writing_agent_npn=npn)
            a_key = {
                "client_id": book.a_ids[pid],
                "policy_id": ap["policy_id"],
                "carrier_member_id": ap["carrier_member_id"],
            }
            b_key = {
                "client_id": cid,
                "policy_id": bp["policy_id"],
                "carrier_member_id": bp["carrier_member_id"],
            }
            book.label(
                "same_policy_two_member_ids",
                {"policy_id": bp["policy_id"]},
                cid,
                [a_key],
                [b_key],
                [],
                a_member_id=ap["carrier_member_id"],
                b_member_id=bp["carrier_member_id"],
            )


def _relative(
    book: _Book, kind: str, pid: str, c: Row, row: Row, policies: list[Row], **change: Any
) -> str:
    """A look-alike B client in c's household with copies of `policies`, labeled must-not-merge."""
    new = book.add(row)
    added = book.copy_policies(policies, new, **change)
    book.label(
        kind,
        {"client_id": new},
        c["client_id"],
        _a_key(book, pid),
        [{"client_id": new}, {"client_id": c["client_id"]}],
        [],
        first_name=row["first_name"],
        last_name=row["last_name"],
        dob=row["dob"],
        policy_ids=[p["policy_id"] for p in added],
    )
    book.mnm.append({"client_id": new, "anchor": c["client_id"], "defect_type": kind})
    return new


def _free_dob(book: _Book, base: Row, ages: tuple[int, int]) -> Any:
    while _key(trial := {**base, "dob": _dob(book.rng, book.rng.randint(*ages))}) in book.keys:
        pass
    return trial["dob"]


def child_on_parent_policy(book: _Book, n: int) -> None:
    """A dependent child (3 to 25) on the parent's ACA policy: member id is the parent's plus -01,
    no premium, and no commission line (carriers pay the subscriber's policy)."""

    def aca(c: Row) -> list[Row]:
        return [
            p
            for p in book.held(c["client_id"])
            if p["line_of_business"] == Lob.ACA and p["status"] != PolicyStatus.TERMINATED
        ]

    for pid, c in book.anchors(n, lambda c: bool(aca(c))):
        parent = aca(c)[-1]
        first = book.fake.first_name()
        base = {**c, "first_name": first, "mbi": None, "email": None}
        row = {**base, "dob": _free_dob(book, base, (3, 25))}
        before = book.next_policy
        _relative(book, "child_on_parent_policy", pid, c, row, [parent], monthly_premium=None)
        dep = book.policies[-1]
        book.policies[-1] = {**dep, "carrier_member_id": parent["carrier_member_id"] + "-01"}
        book.member_ids.discard(dep["carrier_member_id"])
        book.unpaid.add(f"B-P-{before:05d}")
        book.labels[-1]["injected_values"] |= {"parent_policy_id": parent["policy_id"]}


def twin_lookalike(book: _Book, n: int) -> None:
    for pid, c in book.anchors(n, lambda c: c["first_name"] in TWINS):
        row = {**c, "first_name": TWINS[c["first_name"]], "mbi": None}
        if c["mbi"]:
            row["mbi"] = _mbi(book.rng)
        row["email"] = _email(c, row["first_name"], c["last_name"])
        if _key(row) not in book.keys:
            _relative(book, "twin_lookalike", pid, c, row, book.held(c["client_id"]))


def father_son_same_name(book: _Book, n: int) -> None:
    """A son with the father's exact name, 22 to 40 years younger, on his own ACA policy (copied
    from an ACA client in the same state, so agent, license, and RTS all fit)."""
    male = set(Names.first_names_male)
    aca: dict[str, list[str]] = {}
    for cid, row in book.clients.items():
        held = book.held(cid)
        unpaid = any(p["policy_id"] in book.unpaid for p in held)
        if row["mbi"] is None and held and not unpaid and cid not in book.shared.values():
            aca.setdefault(row["state"], []).append(cid)

    def ok(c: Row) -> bool:
        age = AS_OF.year - c["dob"].year
        return c["first_name"] in male and c["mbi"] is not None and age >= 66 and c["state"] in aca

    for pid, c in book.anchors(n, ok):
        age = AS_OF.year - c["dob"].year
        base = {**c, "mbi": None, "email": None}
        row = {**base, "dob": _free_dob(book, base, (max(26, age - 40), min(63, age - 22)))}
        template = book.held(book.rng.choice(aca[c["state"]]))
        _relative(book, "father_son_same_name", pid, c, row, template)


def name_dob_lookalike(
    book: _Book, n: int, a_clean: World, a_policies: dict[str, list[Row]]
) -> None:
    """A B client who lives alone takes the name and birth date of an A-only person in the same
    state but another ZIP. Their MBI, address, phone, and policies stay their own."""
    held = {cid: book.held(cid) for cid in book.clients}
    pool: dict[tuple[Any, ...], list[str]] = {}
    for h in book.households.values():
        cid = h["members"][0]
        if len(h["members"]) == 1 and cid not in book.used and cid not in book.shared.values():
            pool.setdefault(_profile(book.clients[cid], held[cid]), []).append(cid)
    shared_a = set(book.a_ids.values())
    people = [p for p in a_clean.tables["clients"] if p["client_id"] not in shared_a]
    book.rng.shuffle(people)
    done = 0
    for person in people:
        if done == n or person["client_id"] not in a_policies or _key(person) in book.keys:
            continue
        for cid in pool.get(_profile(person, a_policies[person["client_id"]]), []):
            starts = min(p["effective_date"] for p in held[cid])
            late = "AGE" in str(held[cid][0]["eligibility_reason"]) and (
                _first_month_at_65(person["dob"]) > starts
            )
            if late or book.clients[cid]["zip"] == person["zip"]:
                continue
            pool[_profile(person, a_policies[person["client_id"]])].remove(cid)
            book.used.add(cid)
            names = {f: person[f] for f in ("first_name", "last_name", "dob")}
            book.edit(cid, **names)
            book.label(
                "name_dob_lookalike",
                {"client_id": cid},
                person["client_id"],
                [{"client_id": person["client_id"]}],
                [{"client_id": cid}],
                ["first_name", "last_name", "dob"],
                a_zip=person["zip"],
                b_zip=book.clients[cid]["zip"],
                **names,
            )
            book.mnm.append(
                {
                    "client_id": cid,
                    "anchor": person["client_id"],
                    "defect_type": "name_dob_lookalike",
                }
            )
            done += 1
            break


def inject_identity(
    a_clean: World,
    a_final: World,
    b: World,
    shared: list[Shared],
    rates: dict[str, float] | None = None,
) -> tuple[World, list[Defect], list[dict[str, str]]]:
    """Agency B with every C2 injector applied, the labels, and the must-not-merge anchors."""
    rates = RATES if rates is None else rates
    fake = Faker("en_US")
    fake.seed_instance(f"identity-{b.seed}")
    t = b.tables
    a_policies: dict[str, list[Row]] = {}
    for p in a_clean.tables["policies"]:
        a_policies.setdefault(p["client_id"], []).append(p)
    book = _Book(
        rng=random.Random(f"identity-{b.seed}"),
        fake=fake,
        clients={c["client_id"]: c for c in t["clients"]},
        households={h["household_id"]: h for h in t["households"]},
        policies=list(t["policies"]),
        shared={s.person_id: s.b_client_id for s in shared},
        a_ids={s.person_id: s.a_client_id for s in shared},
        member_ids={p["carrier_member_id"] for w in (a_final, b) for p in w.tables["policies"]},
        keys={_key(c) for c in t["clients"]},
        next_policy=len(t["policies"]) + 1,
    )
    n = {k: round(rates.get(k, 0.0) * len(shared)) for k in RATES}
    _surname(book, n["maiden_name"], "maiden_name")
    _surname(book, n["hyphenated_surname"], "hyphenated_surname")
    moved_household(book, n["moved_household"])
    shared_household_contact(book, n["shared_household_contact"])
    same_policy_two_member_ids(book, n["same_policy_two_member_ids"], a_policies)
    child_on_parent_policy(book, n["child_on_parent_policy"])
    twin_lookalike(book, n["twin_lookalike"])
    father_son_same_name(book, n["father_son_same_name"])
    name_dob_lookalike(book, n["name_dob_lookalike"], a_clean, a_policies)
    clients = list(book.clients.values())
    rts = {
        (r["npn"], r["carrier"], r["state"], r["plan_year"], r["line_of_business"])
        for r in t["rts"]
    }
    for p in book.policies:
        last_day = p["termination_date"] or max(p["effective_date"], AS_OF)
        for year in range(p["effective_date"].year, last_day.year + 1):
            rts.add((p["writing_agent_npn"], p["carrier"], p["state"], year, p["line_of_business"]))
    template = t["rts"][0]
    names = ("npn", "carrier", "state", "plan_year", "line_of_business")
    rts_rows = [
        {**template, **dict(zip(names, k, strict=True)), "effective_date": date(k[3], 1, 1)}
        for k in sorted(rts)
    ]
    paid = [p for p in book.policies if p["policy_id"] not in book.unpaid]
    tables = {**t, "clients": clients, "households": list(book.households.values())}
    tables |= {"policies": book.policies, "rts": rts_rows}
    tables["commission_lines"] = commission_lines(paid, clients)
    return replace(b, tables=tables), book.labels, book.mnm


def pair_and_cluster_truth(
    truth: dict[str, Any],
    a_world: World,
    b: World,
    a_defects: list[Defect],
    mnm: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[dict[str, str]]]:
    """Every true same-person pair (across agencies and within B), every person's record ids in
    A and B, and every must-not-merge pair, each anchor expanded to all of the anchor's records."""
    clusters: dict[str, list[str]] = {}
    pairs: list[dict[str, Any]] = []
    for p in truth["people"]:
        a_ids, b_ids = p["agency_a"]["client_ids"], p["agency_b"]["client_ids"]
        clusters[p["person_id"]] = [*a_ids, *b_ids]
        labels = p["agency_a"]["labels"] + p["agency_b"]["labels"]
        both = [(x, y, "cross") for x in a_ids for y in b_ids]
        both += [(x, y, "within_b") for i, x in enumerate(b_ids) for y in b_ids[i + 1 :]]
        for x, y, scope in both:
            kinds = sorted({lab["defect_type"] for lab in labels if lab["client_id"] in (x, y)})
            pairs.append(
                {
                    "person_id": p["person_id"],
                    "left": x,
                    "right": y,
                    "scope": scope,
                    "defect_types": kinds,
                }
            )
    person = {r: pid for pid, ids in clusters.items() for r in ids}
    copies = a_copies(a_defects)
    copied = {c for v in copies.values() for c in v}
    rows = [c["client_id"] for w in (a_world, b) for c in w.tables["clients"]]
    for cid in rows:
        if cid not in person and cid not in copied:
            pid = f"PER-{len(clusters) + 1:05d}"
            clusters[pid] = [cid, *copies.get(cid, [])]
            person |= dict.fromkeys(clusters[pid], pid)
    must_not = [
        {
            "left": r,
            "right": e["client_id"],
            "defect_type": e["defect_type"],
            "reason": MUST_NOT_MERGE[e["defect_type"]],
        }
        for e in mnm
        for r in clusters[person[e["anchor"]]]
    ]
    return pairs, clusters, must_not


def write_truth(
    out: Path,
    truth: dict[str, Any],
    pairs: list[dict[str, Any]],
    clusters: dict[str, list[str]],
    must_not: list[dict[str, str]],
) -> None:
    """cross_agency_truth.json (with counts), pair_truth.jsonl, cluster_truth.json, and
    must_not_merge.jsonl."""
    truth["counts"] |= {
        "true_pairs": len(pairs),
        "true_pairs_within_b": sum(p["scope"] == "within_b" for p in pairs),
        "clusters": len(clusters),
        "must_not_merge_pairs": dict(sorted(Counter(m["defect_type"] for m in must_not).items())),
    }
    (out / "cross_agency_truth.json").write_text(json.dumps(truth, indent=2) + "\n", "utf-8")
    (out / "cluster_truth.json").write_text(json.dumps(clusters, indent=1) + "\n", "utf-8")
    for name, rows in (("pair_truth", pairs), ("must_not_merge", must_not)):
        text = "".join(json.dumps(r) + "\n" for r in rows)
        (out / f"{name}.jsonl").write_text(text, encoding="utf-8")
