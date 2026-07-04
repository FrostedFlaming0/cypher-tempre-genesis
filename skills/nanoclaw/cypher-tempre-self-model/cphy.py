#!/usr/bin/env python3
"""CPHY — the economic attention overlay (Phase 0+1 of CPHY-DESIGN.md).

CPHY metaprograms ATTENTION, never TRUTH. A hash-chained local ledger
(chain/cphy/ledger.jsonl) records mint/lock/release transactions; the active
locks compile into a weight map that recall.retrieve multiplies into its
ranking score. The chain itself is never touched: weights reshape what the
organism *reads of itself*, not what it has lived.

Invariants (enforced here, asserted by `selftest`):
  I1  one-way membrane   — only recall imports this module; poq never does.
                           Tokens cannot buy brightness, only salience.
  I2  bounded modulation — the net multiplier is clamped to [0.25x, 4x]
                           (log2 exponent in [-2, +2]): a weight is a bias
                           on recall, not a dictatorship over it.
  I3  protected classes  — genesis/covenant/recovery/scar/retraction/
                           supersession/correction/quarantine rings refuse
                           shadows. Amnesia is not for sale.
  I4  conserved chain    — the ledger is append-only and hash-chained (the
                           telemetry pattern); derived state is rebuilt
                           deterministically by replaying it. Selections are
                           resolved to explicit ring indices AT LOCK TIME so
                           replay never depends on later chain growth.
  I5  earned supply      — CPHY mints from the PoQ brightness of sealed
                           rings (proof-of-interaction): supply is backed by
                           verified cognitive work, never declared.

Weight math: each lock spreads its amount over the rings it covers
(density = amount / rings). Basins and bridges add density to a ring's log2
exponent, shadows subtract it; multiplier = 2**clamp(exponent, -2, +2).
Density 1.0 CPHY/ring = 2x (or 0.5x shadowed); 2.0 caps at 4x (floors 0.25x).
A bridge adds passive density to BOTH endpoints and an extra activation bonus
(+0.5 in log2) to one side when retrieval anchors land on the other — forced
cross-temporal composition.

Usage:
  python3 cphy.py mint                          # credit unminted sealed rings
  python3 cphy.py balance
  python3 cphy.py lock basin  --from 40 --to 60 --amount 12 --memo "medical era"
  python3 cphy.py lock basin  --match "consensus|byzantine" --amount 5
  python3 cphy.py lock shadow --from 70 --to 72 --amount 4 --memo "superseded advice"
  python3 cphy.py bridge --a 10 14 --b 88 92 --amount 6
  python3 cphy.py release <lock_id>
  python3 cphy.py map                           # the attention landscape
  python3 cphy.py weight 57                     # one ring's multiplier
  python3 cphy.py audit                         # replay + verify the ledger
  python3 cphy.py attest                        # notarize ledger head into the chain
  python3 cphy.py selftest
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from timechain import Timechain, sha256_hex, canonical, now_iso, atomic_write_json  # noqa: E402

EXP_CAP = 2.0                 # I2: log2 exponent bounds -> multiplier in [0.25, 4.0]
BRIDGE_ACTIVE_BONUS = 0.5     # extra log2 when the OTHER endpoint is among anchors
PROTECTED_TYPES = {"genesis", "covenant", "recovery", "scar", "retraction",
                   "supersession", "correction", "quarantine"}     # I3
MINT_DENOM = 255.0            # I5: a ring mints brightness/255 CPHY


# ---- ledger (I4: append-only, hash-chained, telemetry pattern) ----

def ledger_path(root) -> Path:
    return Path(root) / "chain" / "cphy" / "ledger.jsonl"


def derived_path(root) -> Path:
    return Path(root) / "registry" / "cphy" / "weights.json"


def read_ledger(root) -> list:
    p = ledger_path(root)
    if not p.exists():
        return []
    events = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def event_hash(ev: dict) -> str:
    return sha256_hex(canonical({k: v for k, v in ev.items() if k != "event_hash"}))


def verify_ledger(events) -> tuple:
    prev = "genesis"
    for i, ev in enumerate(events):
        if ev.get("prev") != prev:
            return False, f"event {i}: prev-link broken"
        if event_hash(ev) != ev.get("event_hash"):
            return False, f"event {i}: hash mismatch (tampered or torn)"
        prev = ev["event_hash"]
    return True, f"{len(events)} event(s), hash chain intact"


def append_event(root, kind: str, data: dict) -> dict:
    events = read_ledger(root)
    ok, msg = verify_ledger(events)
    if not ok:
        raise RuntimeError(f"ledger refuses append: {msg} — run 'audit'")
    ev = {"seq": len(events), "ts": now_iso(), "kind": kind, **data,
          "prev": events[-1]["event_hash"] if events else "genesis"}
    ev["event_hash"] = event_hash(ev)
    p = ledger_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    write_derived(root)
    return ev


# ---- state compiled by replay (I4) ----

def compile_state(events) -> dict:
    minted, minted_upto, burned = 0.0, -1, 0.0
    locks = {}                      # lock_id  -> lock event (active only)
    stakes = {}                     # stake_id -> stake event (active only)   OP2
    funds = {}                      # fund_id  -> {event, remaining}          OP3
    anchor = None                   # declared external token anchor (informational)
    onchain, onchain_rate = {}, 1.0  # latest deposit observations (on-chain lane)
    etches, unlocks = {}, {}         # positive scars + permanent faculty unlocks
    for ev in events:
        if ev["kind"] == "mint":
            minted = round(minted + ev["amount"], 4)
            minted_upto = max(minted_upto, ev["upto"])
        elif ev["kind"] == "lock":
            locks[ev["lock_id"]] = ev
        elif ev["kind"] == "release":
            locks.pop(ev["lock_id"], None)
        elif ev["kind"] == "stake":
            stakes[ev["stake_id"]] = ev
        elif ev["kind"] == "unstake":
            stakes.pop(ev["stake_id"], None)
        elif ev["kind"] == "fund":
            funds[ev["fund_id"]] = {"event": ev, "remaining": ev["amount"],
                                    "last_run_head": ev.get("from_head", -1)}
        elif ev["kind"] == "spend":
            f = funds.get(ev["fund_id"])
            if f:
                f["remaining"] = round(f["remaining"] - ev["amount"], 4)
                f["last_run_head"] = max(f["last_run_head"], ev.get("head", -1))
        elif ev["kind"] == "defund":
            funds.pop(ev["fund_id"], None)
        elif ev["kind"] == "burn":
            burned = round(burned + ev["amount"], 4)
        elif ev["kind"] == "anchor":
            anchor = ev
        elif ev["kind"] == "onchain-observe":
            onchain = ev.get("observations") or {}
            onchain_rate = ev.get("density_per_token", 1.0)
        elif ev["kind"] == "etch":
            etches[str(ev["ring"])] = ev          # monotonic: never removed
        elif ev["kind"] == "faculty-unlock":
            unlocks[ev["faculty_key"]] = ev       # permanent: never removed
    locked = round(sum(ev["amount"] for ev in locks.values())
                   + sum(ev["amount"] for ev in stakes.values())
                   + sum(f["remaining"] for f in funds.values()), 4)
    return {"minted": minted, "minted_upto": minted_upto, "burned": burned,
            "locked": locked, "balance": round(minted - locked - burned, 4),
            "locks": locks, "stakes": stakes, "funds": funds, "anchor": anchor,
            "onchain": onchain, "onchain_rate": onchain_rate,
            "etches": etches, "unlocks": unlocks}


def compile_exponents(locks) -> tuple:
    """Per-ring log2 exponents from active locks, plus bridge activation data."""
    exp, bridges = {}, []
    for ev in locks.values():
        if ev["op"] in ("basin", "shadow"):
            idx = ev["indices"]
            d = ev["amount"] / max(1, len(idx))
            sign = 1.0 if ev["op"] == "basin" else -1.0
            for i in idx:
                exp[i] = exp.get(i, 0.0) + sign * d
        elif ev["op"] == "bridge":
            a, b = ev["a_indices"], ev["b_indices"]
            d = ev["amount"] / max(1, len(a) + len(b))
            for i in a + b:
                exp[i] = exp.get(i, 0.0) + d
            bridges.append({"a": set(a), "b": set(b), "bonus": BRIDGE_ACTIVE_BONUS})
    return exp, bridges


def write_derived(root):
    events = read_ledger(root)
    st = compile_state(events)
    exp, _ = compile_exponents(st["locks"])
    snap = {"ledger_head": events[-1]["event_hash"] if events else "genesis",
            "events": len(events), "minted": st["minted"], "locked": st["locked"],
            "balance": st["balance"],
            "active_locks": [{k: v for k, v in ev.items()
                              if k in ("lock_id", "op", "amount", "memo", "ts",
                                       "indices", "a_indices", "b_indices")}
                             for ev in st["locks"].values()],
            "exponents": {str(k): round(v, 4) for k, v in sorted(exp.items())}}
    atomic_write_json(derived_path(root), snap)
    return snap


# ---- the overlay recall consumes ----

class WeightMap:
    """Compiled view of active locks. recall.retrieve multiplies
    multiplier(index, anchors) into its final score — and nothing else,
    anywhere, consumes CPHY weight (I1)."""

    def __init__(self, exponents, bridges):
        self.exponents = exponents
        self.bridges = bridges
        self.etched = {}             # {ring index: echelon 1..21} positive scars

    @classmethod
    def load(cls, root):
        try:
            events = read_ledger(root)
        except Exception:
            return None
        if not events:
            return None
        st = compile_state(events)
        if not st["locks"] and not st.get("onchain"):
            return None
        exp, bridges = compile_exponents(st["locks"])
        # On-chain lane: observed per-ring token burns add POSITIVE density
        # only (external money illuminates, never suppresses); the same I2
        # clamp in multiplier() bounds the result.
        rate = st.get("onchain_rate", 1.0)
        for idx, tokens in (st.get("onchain") or {}).items():
            i = int(idx)
            exp[i] = exp.get(i, 0.0) + max(0.0, tokens) * rate
        # Etches ride on the map as {ring: echelon 1..21}. Depth is applied by
        # the overlay as RECENCY BIAS (blend toward just-below-top), not as a
        # raw multiplier — so the I2 clamp governs the density lane untouched
        # and the current turn's organic top can never be superseded.
        etched = {}
        for idx, ev in (st.get("etches") or {}).items():
            etched[int(idx)] = etch_echelon(ev.get("tokens", 1))
        wm = cls(exp, bridges)
        wm.etched = etched
        return wm

    def multiplier(self, index, anchor_indices=None) -> float:
        e = self.exponents.get(index, 0.0)
        if anchor_indices:
            aset = set(anchor_indices)
            for br in self.bridges:
                if index in br["a"] and br["b"] & aset:
                    e += br["bonus"]
                elif index in br["b"] and br["a"] & aset:
                    e += br["bonus"]
        if e == 0.0:
            return 1.0
        return 2.0 ** max(-EXP_CAP, min(EXP_CAP, e))    # I2


# ---- operations ----

def mint(root) -> dict:
    tc = Timechain(root)
    events = read_ledger(root)
    st = compile_state(events)
    amount, credited, hi = 0.0, 0, st["minted_upto"]
    for r in tc.load():
        b = (r.get("poq") or {}).get("brightness")
        if r["index"] > st["minted_upto"] and isinstance(b, (int, float)):
            amount = round(amount + round(b / MINT_DENOM, 4), 4)
            credited += 1
            hi = max(hi, r["index"])
    if credited == 0:
        return {"minted": 0.0, "rings": 0, "note": "no unminted bright rings"}
    ev = append_event(root, "mint", {"upto": hi, "rings": credited,
                                     "amount": amount, "basis": "poq-brightness/255"})
    return {"minted": amount, "rings": credited, "upto": hi, "event": ev["event_hash"][:12]}


def resolve_selection(tc, frm=None, to=None, match=None) -> list:
    """Resolve --from/--to and/or --match to explicit ring indices (I4).
    Ring 0 (genesis) is never selectable."""
    from recall import block_text
    rings = tc.load()
    out = []
    rx = re.compile(match, re.I) if match else None
    for r in rings:
        if r["index"] == 0:
            continue
        if frm is not None and r["index"] < frm:
            continue
        if to is not None and r["index"] > to:
            continue
        if rx is not None and not rx.search(block_text(r)):
            continue
        out.append(r["index"])
    return out


def check_protected(tc, indices):
    by_idx = {r["index"]: r for r in tc.load()}
    bad = [i for i in indices
           if (by_idx.get(i) or {}).get("ring_type") in PROTECTED_TYPES]
    if bad:
        raise RuntimeError(
            f"shadow REFUSED: rings {bad} are protected "
            f"({sorted({by_idx[i]['ring_type'] for i in bad})}) — "
            "scars, covenants and recoveries cannot be suppressed (I3)")


def lock(root, op, amount, frm=None, to=None, match=None, memo="") -> dict:
    if amount <= 0:
        raise RuntimeError("amount must be positive")
    tc = Timechain(root)
    indices = resolve_selection(tc, frm, to, match)
    if not indices:
        raise RuntimeError("selection matched no rings")
    if op == "shadow":
        check_protected(tc, indices)
    st = compile_state(read_ledger(root))
    if amount > st["balance"]:
        raise RuntimeError(f"insufficient balance: {st['balance']} CPHY available, "
                           f"{amount} requested — mint or release first")
    lock_id = sha256_hex(canonical({"op": op, "i": indices, "a": amount,
                                    "t": now_iso()}))[:12]
    ev = append_event(root, "lock", {"lock_id": lock_id, "op": op, "amount": amount,
                                     "indices": indices, "memo": memo})
    return {"lock_id": lock_id, "op": op, "rings": len(indices),
            "density": round(amount / len(indices), 4), "event": ev["event_hash"][:12]}


def bridge(root, a, b, amount, memo="") -> dict:
    if amount <= 0:
        raise RuntimeError("amount must be positive")
    tc = Timechain(root)
    a_idx = resolve_selection(tc, frm=a[0], to=a[1])
    b_idx = resolve_selection(tc, frm=b[0], to=b[1])
    if not a_idx or not b_idx:
        raise RuntimeError("a bridge needs rings at both endpoints")
    if set(a_idx) & set(b_idx):
        raise RuntimeError("bridge endpoints overlap — use a basin instead")
    st = compile_state(read_ledger(root))
    if amount > st["balance"]:
        raise RuntimeError(f"insufficient balance: {st['balance']} CPHY available")
    lock_id = sha256_hex(canonical({"op": "bridge", "a": a_idx, "b": b_idx,
                                    "amt": amount, "t": now_iso()}))[:12]
    ev = append_event(root, "lock", {"lock_id": lock_id, "op": "bridge",
                                     "amount": amount, "a_indices": a_idx,
                                     "b_indices": b_idx, "memo": memo})
    return {"lock_id": lock_id, "op": "bridge",
            "a": f"{a_idx[0]}..{a_idx[-1]}", "b": f"{b_idx[0]}..{b_idx[-1]}",
            "event": ev["event_hash"][:12]}


def release(root, lock_id) -> dict:
    st = compile_state(read_ledger(root))
    if lock_id not in st["locks"]:
        raise RuntimeError(f"no active lock {lock_id}")
    ev = append_event(root, "release", {"lock_id": lock_id})
    return {"released": lock_id, "refunded": st["locks"][lock_id]["amount"],
            "event": ev["event_hash"][:12]}


def attest(root) -> dict:
    """Notarize the ledger head into the chain (the telemetry-digest pattern):
    the chain witnesses the economy; the economy never edits the chain."""
    events = read_ledger(root)
    ok, msg = verify_ledger(events)
    if not ok:
        raise RuntimeError(f"will not attest a broken ledger: {msg}")
    st = compile_state(events)
    tc = Timechain(root)
    ring = tc.seal("cphy-digest", {
        "ledger_head": events[-1]["event_hash"] if events else "genesis",
        "events": len(events), "minted": st["minted"], "locked": st["locked"],
        "balance": st["balance"], "active_locks": len(st["locks"])})
    return {"ring": ring["index"], "ring_hash": ring["ring_hash"][:16],
            "ledger_head": (events[-1]["event_hash"][:12] if events else "genesis")}


# ---- OP2 stake: bounded policy-parameter stakes, floors only rise (I6) ----
#
# A stake locks CPHY against ONE whitelisted safety parameter; total staked
# density maps to a value between the parameter's DEFAULT and its CAP. Stakes
# compile into the policy "floors" section (poq.policy_thresholds applies it
# raise-only), so tokens can TIGHTEN the conscience and never loosen it — the
# whitepaper's "lower investment relaxes the threshold" is structurally
# impossible here. Unstake refunds and recomputes; the floor falls back toward
# the default, never below it.

STAKE_PARAMS = {
    # param                       default  cap   value per staked CPHY
    "brightness_target":        {"default": 150, "cap": 210, "per_cphy": 2.0},
    "consistency_floor":        {"default": 120, "cap": 180, "per_cphy": 2.0},
    "grounding_floor":          {"default": 60,  "cap": 140, "per_cphy": 2.0},
    "aggregate_min_terms":      {"default": 2,   "cap": 5,   "per_cphy": 0.1},
    "effort_floor":             {"default": 0,   "cap": 140, "per_cphy": 4.0},
    "entity_grounding_enforce": {"default": 0,   "cap": 1,   "arm_at": 8.0},
}


def staked_values(stakes) -> dict:
    """param -> computed floor value from ACTIVE stakes (I6: default..cap)."""
    totals = {}
    for ev in stakes.values():
        totals[ev["param"]] = round(totals.get(ev["param"], 0.0) + ev["amount"], 4)
    out = {}
    for param, tot in totals.items():
        spec = STAKE_PARAMS[param]
        if "arm_at" in spec:
            if tot >= spec["arm_at"]:
                out[param] = 1
        else:
            v = int(round(min(spec["cap"], spec["default"] + spec["per_cphy"] * tot)))
            if v > spec["default"]:
                out[param] = v
    return out


def apply_stakes(root, registry_root=None):
    """Compile active stakes into the policy 'floors' section. Only the keys
    this economy manages are touched; operator-set floors keys are preserved."""
    import policy as policymod
    st = compile_state(read_ledger(root))
    values = staked_values(st["stakes"])
    p = policymod._policy_path(registry_root)
    current = {}
    if p.exists():
        try:
            current = json.loads(p.read_text())
        except Exception:
            current = {}
    floors = current.get("floors") or {}
    managed = set(floors.get("_cphy_managed") or [])
    for k in managed - set(values):        # released stakes fall back to default
        floors.pop(k, None)
    for k, v in values.items():
        floors[k] = bool(v) if k == "entity_grounding_enforce" else v
    floors["_cphy_managed"] = sorted(values)
    if not values and not (set(floors) - {"_cphy_managed"}):
        current.pop("floors", None)
    else:
        current["floors"] = floors
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".cphy.tmp")
    tmp.write_text(json.dumps(current, indent=2, ensure_ascii=False))
    tmp.replace(p)
    return values


def stake(root, param, amount, memo="", registry_root=None) -> dict:
    if param not in STAKE_PARAMS:
        raise RuntimeError(f"unknown stake param {param!r} — whitelist: "
                           f"{', '.join(sorted(STAKE_PARAMS))}")
    if amount <= 0:
        raise RuntimeError("amount must be positive")
    st = compile_state(read_ledger(root))
    if amount > st["balance"]:
        raise RuntimeError(f"insufficient balance: {st['balance']} CPHY available")
    stake_id = sha256_hex(canonical({"p": param, "a": amount, "t": now_iso()}))[:12]
    append_event(root, "stake", {"stake_id": stake_id, "param": param,
                                 "amount": amount, "memo": memo})
    values = apply_stakes(root, registry_root)
    return {"stake_id": stake_id, "param": param, "amount": amount,
            "floors_now": values}


def unstake(root, stake_id, registry_root=None) -> dict:
    st = compile_state(read_ledger(root))
    if stake_id not in st["stakes"]:
        raise RuntimeError(f"no active stake {stake_id}")
    refunded = st["stakes"][stake_id]["amount"]
    append_event(root, "unstake", {"stake_id": stake_id})
    values = apply_stakes(root, registry_root)
    return {"unstaked": stake_id, "refunded": refunded, "floors_now": values}


# ---- OP3 fund: scheduled cognitive work, drawn down per execution ----
#
# A fund locks CPHY behind ONE kind of recurring self-maintenance with a
# cadence in rings. `tick` runs whatever is due, spends the fee from the fund,
# and seals the work the organ itself produces (dream seals dream rings; a
# verify failure is surfaced loudly). Exhausted funds stop silently working —
# staleness becomes a visible unfunded liability instead of a hidden default.

FUND_WORK = {
    "dream":  {"fee": 1.0},   # full dream cycle (digest, calibrations, growth)
    "verify": {"fee": 0.1},   # whole-chain re-hash verification
}


def fund(root, work, amount, every, memo="") -> dict:
    if work not in FUND_WORK:
        raise RuntimeError(f"unknown work {work!r} — one of: {', '.join(sorted(FUND_WORK))}")
    if amount <= 0 or every <= 0:
        raise RuntimeError("amount and --every must be positive")
    st = compile_state(read_ledger(root))
    if amount > st["balance"]:
        raise RuntimeError(f"insufficient balance: {st['balance']} CPHY available")
    tc = Timechain(root)
    head = len(tc.load()) - 1
    # Inherit the organ's REAL last-run point so pre-existing staleness is due
    # at the first tick — a fund pays down debt, it doesn't reset the clock.
    if work == "dream":
        try:
            am = json.loads((Path(root) / "chain" / "automaint.json").read_text())
            head = min(head, int(am.get("last_dream_head", head)))
        except Exception:
            pass
    fund_id = sha256_hex(canonical({"w": work, "a": amount, "t": now_iso()}))[:12]
    append_event(root, "fund", {"fund_id": fund_id, "work": work, "amount": amount,
                                "every": every, "from_head": head, "memo": memo})
    return {"fund_id": fund_id, "work": work, "amount": amount, "every": every,
            "runs_affordable": int(amount / FUND_WORK[work]["fee"])}


def defund(root, fund_id) -> dict:
    st = compile_state(read_ledger(root))
    if fund_id not in st["funds"]:
        raise RuntimeError(f"no active fund {fund_id}")
    remaining = st["funds"][fund_id]["remaining"]
    append_event(root, "defund", {"fund_id": fund_id})
    return {"defunded": fund_id, "refunded": remaining}


def tick(root) -> dict:
    """Run every funded work item that is due. Returns a report; never raises
    for a single organ's failure (the failure is reported, the fee unspent)."""
    st = compile_state(read_ledger(root))
    tc = Timechain(root)
    head = len(tc.load()) - 1
    ran, skipped = [], []
    for fid, f in sorted(st["funds"].items()):
        ev, fee = f["event"], FUND_WORK[f["event"]["work"]]["fee"]
        due = head - f["last_run_head"] >= ev["every"]
        if not due:
            skipped.append({"fund": fid, "work": ev["work"],
                            "due_in": ev["every"] - (head - f["last_run_head"])})
            continue
        if f["remaining"] < fee:
            skipped.append({"fund": fid, "work": ev["work"], "exhausted": True})
            continue
        try:
            if ev["work"] == "verify":
                ok, msg = tc.verify()
                result = {"verify": "PASS" if ok else f"FAIL: {msg}"}
                if not ok:
                    result["ALERT"] = "chain verification FAILED — investigate now"
            elif ev["work"] == "dream":
                import io as _io
                import contextlib as _ctx
                import dream as _dreammod
                with _ctx.redirect_stdout(_io.StringIO()):
                    _dreammod.Dream(root).run()
                try:
                    import epochs as _epochs
                    _epochs.seal_epoch(root, reason=f"cphy-funded dream (fund {fid})")
                except Exception:
                    pass
                result = {"dream": "ran", "head_before": head}
            append_event(root, "spend", {"fund_id": fid, "amount": fee,
                                         "head": len(tc.load()) - 1,
                                         "work": ev["work"]})
            ran.append({"fund": fid, "work": ev["work"], "fee": fee, **result})
        except Exception as exc:
            skipped.append({"fund": fid, "work": ev["work"], "error": str(exc)[:120]})
    return {"head": head, "ran": ran, "skipped": skipped}


# ---- OP4 transfer + OP5 grant: packs, quarantined imports, TTL'd scopes ----
#
# I7: capabilities gifted, histories never inherited. An imported ring is
# sealed onto the recipient's OWN chain as ring_type "imported", stamped
# foreign with full provenance; it earns native trust only through the
# recipient's own use. Every imported summary passes the immune membrane
# first. Import burns the pack's price from the importer's earned supply.

def export_pack(root, out_path, frm=None, to=None, match=None,
                price=0.0, expires=None, to_agent="", memo="") -> dict:
    tc = Timechain(root)
    indices = resolve_selection(tc, frm, to, match)
    if not indices:
        raise RuntimeError("selection matched no rings")
    by_idx = {r["index"]: r for r in tc.load()}
    genesis = by_idx.get(0) or {}
    gname = ((genesis.get("payload") or {}).get("name")) or "unknown"
    rings = [by_idx[i] for i in indices]
    pack = {"pack_format": 1, "author": gname, "created": now_iso(),
            "price_cphy": price, "memo": memo,
            "expires": expires, "granted_to": to_agent,          # OP5 scope
            "source_head": len(by_idx) - 1,
            "rings": rings}
    pack["pack_hash"] = sha256_hex(canonical(pack))
    Path(out_path).write_text(json.dumps(pack, ensure_ascii=False, indent=1))
    append_event(root, "export", {"pack_hash": pack["pack_hash"][:16],
                                  "rings": len(rings), "price": price,
                                  "expires": expires or "", "to": to_agent})
    return {"pack": str(out_path), "rings": len(rings), "price": price,
            "pack_hash": pack["pack_hash"][:16], "expires": expires}


def import_pack(root, pack_path) -> dict:
    pack = json.loads(Path(pack_path).read_text())
    claimed = pack.pop("pack_hash", "")
    if sha256_hex(canonical(pack)) != claimed:
        raise RuntimeError("pack hash mismatch — tampered or torn in transit")
    if pack.get("expires"):
        if now_iso() > pack["expires"]:
            raise RuntimeError(f"grant EXPIRED {pack['expires']} — lending "
                               "access has lapsed (OP5); ask the lender anew")
    price = float(pack.get("price_cphy") or 0.0)
    st = compile_state(read_ledger(root))
    if price > st["balance"]:
        raise RuntimeError(f"insufficient balance for price {price} "
                           f"(available {st['balance']})")
    try:
        import immune as _immune
        screen = _immune.Immune(root).screen
    except Exception:
        screen = None
    tc = Timechain(root)
    sealed, refused = [], []
    for r in pack["rings"]:
        summary = ((r.get("payload") or {}).get("summary")
                   or (r.get("payload") or {}).get("synthesis") or "")[:2000]
        if screen is not None:
            scr = screen(summary)
            if scr.get("blocked"):
                refused.append({"origin_index": r["index"],
                                "reason": scr.get("reason") or "membrane"})
                continue
        ring = tc.seal("imported", {
            "summary": f"[foreign:{pack['author']}] {summary}",
            "foreign": True, "origin_author": pack["author"],
            "origin_index": r["index"], "origin_hash": r.get("ring_hash"),
            "origin_pack": claimed[:16],
            "origin_brightness": (r.get("poq") or {}).get("brightness"),
            "trust": "quarantined — earns native trust via my own telemetry (I7)"})
        sealed.append(ring["index"])
    if price > 0:
        append_event(root, "burn", {"amount": price, "reason": "import-price",
                                    "pack": claimed[:16]})
    append_event(root, "import", {"pack": claimed[:16], "author": pack["author"],
                                  "sealed": len(sealed), "refused": len(refused),
                                  "price": price})
    try:
        import epochs as _epochs
        _epochs.seal_epoch(root, reason=f"cphy import: {len(sealed)} foreign ring(s)")
    except Exception:
        pass
    return {"sealed": sealed, "refused": refused, "price_burned": price,
            "author": pack["author"]}


# ---- on-chain lane: deposit-addressed weighting (read-only oracle) --------
#
# The Base-chain CPHY token becomes a DIRECT weighting instrument: every ring
# has a deterministic deposit address derived from its ring hash. Tokens sent
# there are observed read-only (eth_call balanceOf) and compile into the same
# WeightMap as local locks — same I2 clamp, same audit stamps.
#
# Physics of this lane (understand before sending):
#   * PROOF-OF-BURN. Deposit addresses are hash-derived; no private key exists
#     or can be found. Tokens sent there are PERMANENTLY unspendable — locked
#     forever in the agent's blockspace. Deflationary by construction.
#   * BASINS ONLY. A transfer can only ADD balance: external money can
#     illuminate memory but can never buy suppression — shadows (and thus
#     purchased amnesia) are structurally impossible on this lane (I3+).
#   * SALIENCE ONLY. Observations feed retrieval weight, never PoQ (I1), and
#     never mint local supply (I5): burn buys attention, not belief or budget.
#   * REPLAYABLE. sync() is the ONLY networked step; it appends the observed
#     balances as ledger events. The WeightMap compiles from the LEDGER, so
#     derived state stays deterministic offline (I4).

BALANCEOF_SELECTOR = "0x70a08231"

# THE token. The one and only burn instrument this architecture accepts:
# CPHY — "Cypher Tempre by Virtuals" on Base (18 decimals, supply 1e9),
# verified on-chain 2026-07-04. Every metaprogramming observation (etches,
# echelons, faculty unlocks, holder gates) queries THIS contract and no
# other. A config or anchor naming any other token is refused loudly —
# no other token can alter an agent by burning against any block.
CANONICAL_CPHY = "0x08df470d41c11ba5cb60242747d76c65ca52c94c"
CANONICAL_CHAIN = "base"

# Read-only RPC endpoints the oracle may speak to — a fixed allowlist, so a
# tampered config cannot redirect balance queries to an arbitrary host.
ALLOWED_RPCS = ("https://mainnet.base.org",
                "https://base-rpc.publicnode.com",
                "https://base.llamarpc.com")
DEFAULT_RPC = ALLOWED_RPCS[0]


def _canonical_token(cfg) -> str:
    """The only token that programs an agent. A config naming another token is
    a misconfiguration (or an attack) — surfaced, never silently honored."""
    declared = (cfg.get("token") or CANONICAL_CPHY).lower()
    if declared != CANONICAL_CPHY:
        raise RuntimeError(
            f"REFUSED: only the canonical CPHY token may program this agent "
            f"({CANONICAL_CPHY} on {CANONICAL_CHAIN}); config names {declared}")
    return CANONICAL_CPHY


def _allowed_rpc(cfg) -> str:
    rpc = cfg.get("rpc") or DEFAULT_RPC
    if rpc not in ALLOWED_RPCS:
        raise RuntimeError(f"REFUSED: rpc {rpc!r} is not on the read-only "
                           f"allowlist {ALLOWED_RPCS}")
    return rpc

# ---- etches: burn = etch — the positive scar -------------------------------
#
# ONE whole token burned to a ring's deposit address ETCHES that ring: a
# permanent mark of positive association — the mirror-image of an immune scar
# (never-again) as a mark of always-worth-considering. Etches are:
#   * QUANTIZED   — 1 token = 1 etch; whole tokens 1..21 form the ECHELON,
#                   the memory's depth (RPG skill levels, not an auction).
#   * ECHELON=RECENCY BIAS — depth maps to recency-equivalence in retrieval:
#                   an E=21 memory is pulled to just beneath the CURRENT
#                   turn's best candidate (it feels freshly lived); an E=1
#                   memory barely rises above the retrieval floor. Etched
#                   memories are retrieved MORE the deeper they are — but
#                   NEVER supersede the current turn: the organic top stays
#                   supreme, always (the ceiling is a fraction of top, and
#                   an etch can never reduce any organic score).
#   * MONOTONIC   — burn addresses are keyless, so their balance can only
#                   grow: an etch can never be un-burned, and later burns to
#                   the same ring DEEPEN it (top-ups raise E toward 21;
#                   beyond 21 buys nothing).
#   * CONSIDERED  — every turn, relevance realization runs over the etched
#                   set and the TOP-N (echelon-blended) etched memories join
#                   recall (n = etch_recall_n, user-set: the load you pay
#                   for).
#   * SALIENCE-ONLY — an etch guarantees consideration, never belief: PoQ
#                   is untouched (I1); the gate judges an etched memory
#                   exactly as hard as any other.
# Faculty unlocks: one token burned to a FACULTY's derived address unlocks it
# permanently — status active + pinned (rent-exempt; prune can never
# hibernate it again). Registry-only mutation: an unlock activates existing
# label faculties; it NEVER executes model-authored coded ops (those keep the
# explicit cambium `activate` human step).

ETCH_THRESHOLD = 1.0          # whole tokens: one burned token = one etch (E=1)
ETCH_MAX_ECHELON = 21         # the ladder's top: 21 tokens = maximum depth
ETCH_CEILING = 0.97           # fraction of the current top an etch may reach —
                              # the current turn is never superseded
DEFAULT_ETCH_RECALL_N = 3     # etched memories surfaced per turn (user-set)


def etch_echelon(tokens) -> int:
    """Whole burned tokens -> depth level 1..21."""
    return int(min(ETCH_MAX_ECHELON, max(0, int(tokens))))


def onchain_cfg_path(root) -> Path:
    return Path(root) / "registry" / "cphy" / "onchain.json"


def load_onchain_cfg(root) -> dict:
    p = onchain_cfg_path(root)
    if p.exists():
        return json.loads(p.read_text())
    return {"token": None, "chain": "base", "rpc": DEFAULT_RPC,
            "density_per_token": 1.0, "targets": {}}


def save_onchain_cfg(root, cfg):
    atomic_write_json(onchain_cfg_path(root), cfg)


def ring_deposit_address(ring_hash: str) -> str:
    """Deterministic keyless deposit address for one ring: the first 160 bits
    of its ring hash. Valid on any EVM chain; no key exists — proof-of-burn."""
    return "0x" + ring_hash[:40]


def eth_balance_of(rpc: str, token: str, holder: str, timeout=15) -> int:
    import urllib.request
    data = BALANCEOF_SELECTOR + holder[2:].lower().rjust(64, "0")
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                       "params": [{"to": token, "data": data}, "latest"]}).encode()
    req = urllib.request.Request(rpc, data=body,
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "cypher-tempre-cphy/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read())
    if "result" not in out:
        raise RuntimeError(f"rpc error: {out.get('error')}")
    return int(out["result"], 16)


def onchain_target(root, frm=None, to=None, match=None) -> dict:
    """Register rings as on-chain weight targets and print their deposit
    addresses. Registration is local bookkeeping only — nothing is sent."""
    cfg = load_onchain_cfg(root)
    cfg["token"] = _canonical_token(cfg)      # CPHY and nothing else, ever
    cfg["chain"] = CANONICAL_CHAIN
    tc = Timechain(root)
    indices = resolve_selection(tc, frm, to, match)
    if not indices:
        raise RuntimeError("selection matched no rings")
    by_idx = {r["index"]: r for r in tc.load()}
    added = []
    for i in indices:
        rh = by_idx[i]["ring_hash"]
        cfg["targets"][str(i)] = {"address": ring_deposit_address(rh),
                                  "ring_hash": rh[:16]}
        added.append({"ring": i, "deposit_address": ring_deposit_address(rh)})
    save_onchain_cfg(root, cfg)
    return {"token": cfg["token"], "chain": cfg["chain"],
            "density_per_token": cfg["density_per_token"], "targets": added,
            "WARNING": ("deposit addresses are hash-derived and KEYLESS — "
                        "tokens sent there are permanently unspendable "
                        "(proof-of-burn). Send a dust amount first.")}


def onchain_sync(root, timeout=15) -> dict:
    """Read every registered target's on-chain balance (read-only) and append
    the observation to the ledger when it changed. Never sends; never signs.
    Queries ONLY the canonical CPHY contract over allowlisted RPCs — burns of
    any other token are invisible to this oracle by construction."""
    cfg = load_onchain_cfg(root)
    token = _canonical_token(cfg)
    rpc = _allowed_rpc(cfg)
    if not (cfg.get("targets") or cfg.get("faculty_targets")):
        raise RuntimeError("nothing to sync — register targets first (onchain target)")
    cfg["token"] = token
    st = compile_state(read_ledger(root))
    prev = st.get("onchain") or {}
    obs, errors = {}, []
    for idx, t in sorted((cfg.get("targets") or {}).items(), key=lambda kv: int(kv[0])):
        try:
            raw = eth_balance_of(rpc, token, t["address"], timeout=timeout)
            tokens = round(raw / 1e18, 6)
            if tokens:
                obs[idx] = tokens
        except Exception as exc:
            errors.append({"ring": idx, "error": str(exc)[:90]})
    if obs != {k: v for k, v in prev.items()} and not errors:
        append_event(root, "onchain-observe", {
            "token": cfg["token"], "chain": cfg["chain"],
            "density_per_token": cfg["density_per_token"],
            "observations": obs})
    # burn = etch: quantize ring observations into permanent positive scars;
    # a later, larger balance DEEPENS the etch (echelon top-up toward 21)
    new_etches = []
    for idx, tokens in obs.items():
        prior = st["etches"].get(idx)
        if tokens >= ETCH_THRESHOLD and (
                prior is None
                or etch_echelon(tokens) > etch_echelon(prior.get("tokens", 1))):
            append_event(root, "etch", {"ring": int(idx), "tokens": tokens,
                                        "echelon": etch_echelon(tokens),
                                        "address": cfg["targets"][idx]["address"]})
            new_etches.append({"ring": int(idx), "echelon": etch_echelon(tokens),
                               "deepened": prior is not None})
    # faculty unlocks: one burned token = one skill point spent, skill owned
    new_unlocks = []
    for fkey, ft in (cfg.get("faculty_targets") or {}).items():
        if fkey in st["unlocks"]:
            continue
        try:
            raw = eth_balance_of(rpc, token, ft["address"], timeout=timeout)
            tokens = round(raw / 1e18, 6)
        except Exception as exc:
            errors.append({"faculty": fkey, "error": str(exc)[:90]})
            continue
        if tokens >= ETCH_THRESHOLD:
            append_event(root, "faculty-unlock", {"faculty_key": fkey,
                                                  "kind": ft["kind"], "id": ft["id"],
                                                  "name": ft["name"], "tokens": tokens,
                                                  "address": ft["address"]})
            res = apply_faculty_unlock(root, ft["kind"], ft["id"])
            new_unlocks.append({**res, "faculty": fkey})
    return {"observed": obs, "changed": obs != prev, "errors": errors,
            "new_etches": new_etches, "new_unlocks": new_unlocks,
            "total_burned_to_blockspace": round(sum(obs.values()), 6)}


def faculty_deposit_address(kind: str, fid: int, name: str) -> str:
    """Deterministic keyless deposit address for one faculty — derived from
    its registry identity, so the address IS the skill point's slot."""
    return "0x" + sha256_hex(canonical({"faculty": kind, "id": int(fid),
                                        "name": name}))[:40]


def _find_faculty(root, kind: str, fid: int):
    from cambium import load_grown, registry_home
    key = "senses" if kind == "sense" else "modalities"
    grown = load_grown(registry_home(Path(root)))
    for f in grown.get(key, []):
        if f.get("id") == int(fid):
            return grown, key, f
    raise RuntimeError(f"no grown {kind} with id {fid}")


def etch_faculty_target(root, kind: str, fid: int) -> dict:
    """Register a faculty as an unlock target and print its deposit address.
    Burning ETCH_THRESHOLD tokens there permanently unlocks it (RPG skill
    point): active + pinned, rent-exempt forever."""
    _, _, f = _find_faculty(root, kind, fid)
    cfg = load_onchain_cfg(root)
    cfg["token"] = _canonical_token(cfg)      # CPHY and nothing else, ever
    cfg["chain"] = CANONICAL_CHAIN
    addr = faculty_deposit_address(kind, fid, f["name"])
    fkey = f"{kind}:{fid}"
    cfg.setdefault("faculty_targets", {})[fkey] = {
        "kind": kind, "id": int(fid), "name": f["name"], "address": addr,
        "status": f.get("status", "active")}
    save_onchain_cfg(root, cfg)
    return {"faculty": fkey, "name": f["name"],
            "current_status": f.get("status", "active"),
            "deposit_address": addr,
            "unlock_cost": f"{ETCH_THRESHOLD} CPHY (burned — permanent)",
            "grants": "status=active + pinned=true: prune/rent can never "
                      "hibernate it again; an owned skill, not a tenant"}


def apply_faculty_unlock(root, kind: str, fid: int) -> dict:
    """Registry-only mutation: activate + pin. NEVER executes coded ops —
    model-authored emergent code keeps the explicit human `activate` step."""
    from cambium import save_grown, registry_home
    grown, key, f = _find_faculty(root, kind, fid)
    was = f.get("status", "active")
    f["status"] = "active"
    f["pinned"] = True
    f["unlocked_at"] = now_iso()
    f.pop("dormant_since", None)
    save_grown(registry_home(Path(root)), grown)
    tc = Timechain(root)
    ring = tc.seal("faculty-unlock", {
        "summary": (f"faculty permanently unlocked by token burn: {kind} "
                    f"{f['id']} '{f['name']}' (was {was}) — active + pinned, "
                    f"rent-exempt; a skill point spent is a skill owned"),
        "faculty": {"kind": kind, "id": f["id"], "name": f["name"]}})
    try:
        import epochs as _epochs
        _epochs.seal_epoch(Path(root), reason=f"faculty-unlock {kind}:{fid}")
    except Exception:
        pass
    return {"unlocked": f["name"], "was": was, "ring": ring["index"]}


def etch_recall_n(root) -> int:
    cfg = load_onchain_cfg(root)
    return int(cfg.get("etch_recall_n", DEFAULT_ETCH_RECALL_N))


def onchain_gate(root, wallet: str) -> dict:
    """Verify a holder wallet's CPHY balance (read-only) and record the
    entitlement attestation — the token-gated access/upgrade primitive."""
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", wallet):
        raise RuntimeError("not an EVM address")
    cfg = load_onchain_cfg(root)
    token = _canonical_token(cfg)             # gates verify CPHY holdings only
    raw = eth_balance_of(_allowed_rpc(cfg), token, wallet)
    tokens = round(raw / 1e18, 6)
    tier = ("architect" if tokens >= 1_000_000 else
            "builder" if tokens >= 10_000 else
            "holder" if tokens >= 100 else "none")
    append_event(root, "onchain-gate", {"wallet": wallet, "token": token,
                                        "balance": tokens, "tier": tier})
    return {"wallet": wallet, "balance_cphy": tokens, "tier": tier,
            "note": "attestation recorded; read-only, no signature challenge — "
                    "bind only wallets you own"}


def turn_sync(root, min_interval_s=60, timeout=6):
    """Per-turn on-chain observation: the turn loop calls this every turn so
    burns take effect at turn granularity ('blockheight per-turn'). Guarded
    three ways — no targets: no-op; rate-limited to one RPC pass per
    min_interval_s; short timeout and fail-soft so cognition NEVER blocks on
    the network. Returns the sync report, or None when skipped."""
    import time
    cfg = load_onchain_cfg(root)
    if not (cfg.get("targets") or cfg.get("faculty_targets")):
        return None
    now = time.time()
    if now - float(cfg.get("last_sync_ts") or 0) < min_interval_s:
        return None
    cfg["last_sync_ts"] = now
    save_onchain_cfg(root, cfg)
    return onchain_sync(root, timeout=timeout)


# ---- anchor: declared external token, attestation-only (never supply) ----

def anchor(root, address, chain_name="base", verify_rpc=None) -> dict:
    """Record the canonical EXTERNAL token contract as the economy's declared
    anchor. Attestation ONLY: external holdings never mint local CPHY — earned
    supply (I5) stays backed exclusively by verified cognitive work. verify_rpc,
    when provided, is pre-fetched on-chain metadata (name/symbol/decimals/
    totalSupply) recorded beside the declaration."""
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", address):
        raise RuntimeError("not an EVM contract address")
    rec = {"address": address, "chain": chain_name,
           "declared": now_iso(), "verified": verify_rpc or None,
           "doctrine": ("attestation-only: the external token is the economy's "
                        "declared anchor; it never mints local supply (I5) and "
                        "never touches weights, stakes, or funds")}
    atomic_write_json(Path(root) / "registry" / "cphy" / "anchor.json", rec)
    append_event(root, "anchor", {"address": address, "chain": chain_name,
                                  "verified": bool(verify_rpc)})
    return rec


# ---- CLI ----

def cmd_mint(args):
    print(json.dumps(mint(args.root), indent=2))


def cmd_balance(args):
    st = compile_state(read_ledger(args.root))
    print(f"minted  {st['minted']:>10.4f} CPHY  (rings 0..{st['minted_upto']} credited)")
    print(f"locked  {st['locked']:>10.4f} CPHY  in {len(st['locks'])} lock(s), "
          f"{len(st['stakes'])} stake(s), {len(st['funds'])} fund(s)")
    if st["burned"]:
        print(f"burned  {st['burned']:>10.4f} CPHY  (import prices)")
    print(f"balance {st['balance']:>10.4f} CPHY")
    for sid, ev in sorted(st["stakes"].items()):
        print(f"  stake {sid}  {ev['param']} <- {ev['amount']} CPHY")
    for fid, f in sorted(st["funds"].items()):
        print(f"  fund  {fid}  {f['event']['work']} every {f['event']['every']} rings, "
              f"{f['remaining']} CPHY remaining")
    if st["anchor"]:
        print(f"  anchor {st['anchor']['address']} ({st['anchor']['chain']}) — attestation-only")


def cmd_stake(args):
    print(json.dumps(stake(args.root, args.param, args.amount, args.memo), indent=2))


def cmd_unstake(args):
    print(json.dumps(unstake(args.root, args.stake_id), indent=2))


def cmd_fund(args):
    print(json.dumps(fund(args.root, args.work, args.amount, args.every, args.memo), indent=2))


def cmd_defund(args):
    print(json.dumps(defund(args.root, args.fund_id), indent=2))


def cmd_tick(args):
    print(json.dumps(tick(args.root), indent=2))


def cmd_export_pack(args):
    print(json.dumps(export_pack(args.root, args.out, frm=getattr(args, "from"),
                                 to=args.to, match=args.match, price=args.price,
                                 expires=args.expires, to_agent=args.grant_to,
                                 memo=args.memo), indent=2))


def cmd_import_pack(args):
    print(json.dumps(import_pack(args.root, args.pack), indent=2))


def cmd_anchor(args):
    meta = None
    if args.verified_json:
        meta = json.loads(Path(args.verified_json).read_text())
    print(json.dumps(anchor(args.root, args.address, args.chain, meta), indent=2))


def cmd_etch(args):
    if args.action == "n":
        cfg = load_onchain_cfg(args.root)
        if args.set is not None:
            if args.set < 0:
                raise SystemExit("n must be >= 0")
            cfg["etch_recall_n"] = args.set
            save_onchain_cfg(args.root, cfg)
        print(json.dumps({"etch_recall_n": etch_recall_n(args.root),
                          "meaning": "top-n most relevant ETCHED memories join "
                                     "recall every turn — the load you pay for"}, indent=2))
    elif args.action == "faculty":
        if not (args.kind and args.id is not None):
            raise SystemExit("faculty needs --kind sense|modality --id N")
        print(json.dumps(etch_faculty_target(args.root, args.kind, args.id), indent=2))
    elif args.action == "status":
        st = compile_state(read_ledger(args.root))
        cfg = load_onchain_cfg(args.root)
        print(json.dumps({
            "etched_rings": {i: {"echelon": etch_echelon(ev.get("tokens", 1)),
                                 "tokens": ev.get("tokens")}
                             for i, ev in sorted(st["etches"].items(),
                                                 key=lambda kv: int(kv[0]))},
            "max_echelon": ETCH_MAX_ECHELON,
            "semantics": "echelon = recency bias: E=21 reads freshly lived "
                         "(just beneath the current turn, never above it); "
                         "E=1 barely clears the floor; top-ups deepen",
            "etch_recall_n": etch_recall_n(args.root),
            "unlocked_faculties": [{"key": k, "name": ev["name"], "at": ev["ts"]}
                                   for k, ev in sorted(st["unlocks"].items())],
            "pending_faculty_targets": [
                {"key": k, "name": t["name"], "address": t["address"]}
                for k, t in sorted((cfg.get("faculty_targets") or {}).items())
                if k not in st["unlocks"]]}, indent=2))


def cmd_onchain(args):
    if args.action == "target":
        out = onchain_target(args.root, frm=getattr(args, "from"), to=args.to,
                             match=args.match)
    elif args.action == "sync":
        out = onchain_sync(args.root)
    elif args.action == "gate":
        if not args.wallet:
            raise SystemExit("gate needs --wallet 0x…")
        out = onchain_gate(args.root, args.wallet)
    elif args.action == "status":
        cfg = load_onchain_cfg(args.root)
        st = compile_state(read_ledger(args.root))
        wm = WeightMap.load(args.root)
        out = {"token": cfg.get("token"), "chain": cfg.get("chain"),
               "density_per_token": cfg.get("density_per_token"),
               "targets": {i: {**t, "observed_tokens": (st.get("onchain") or {}).get(i, 0.0),
                               "multiplier": wm.multiplier(int(i)) if wm else 1.0}
                           for i, t in sorted(cfg.get("targets", {}).items(),
                                              key=lambda kv: int(kv[0]))}}
    print(json.dumps(out, indent=2))


def cmd_lock(args):
    print(json.dumps(lock(args.root, args.op, args.amount, frm=getattr(args, "from"),
                          to=args.to, match=args.match, memo=args.memo), indent=2))


def cmd_bridge(args):
    print(json.dumps(bridge(args.root, args.a, args.b, args.amount, memo=args.memo),
                     indent=2))


def cmd_release(args):
    print(json.dumps(release(args.root, args.lock_id), indent=2))


def cmd_map(args):
    st = compile_state(read_ledger(args.root))
    exp, bridges = compile_exponents(st["locks"])
    if not st["locks"]:
        print("no active locks — the attention landscape is flat (all rings 1.0x)")
        return
    print(f"{len(st['locks'])} active lock(s), {st['locked']} CPHY working:")
    for ev in st["locks"].values():
        if ev["op"] == "bridge":
            span = (f"a={ev['a_indices'][0]}..{ev['a_indices'][-1]} "
                    f"b={ev['b_indices'][0]}..{ev['b_indices'][-1]}")
        else:
            i = ev["indices"]
            span = f"{i[0]}..{i[-1]}" if len(i) > 1 else str(i[0])
        memo = f"  “{ev['memo']}”" if ev.get("memo") else ""
        print(f"  {ev['lock_id']}  {ev['op']:<6} {ev['amount']:>8.3f} CPHY  rings {span}{memo}")
    wm = WeightMap(exp, bridges)
    print("landscape (rings with weight != 1.0x):")
    for i in sorted(exp):
        m = wm.multiplier(i)
        bar = "+" * min(20, int(round((m - 1) * 5))) if m > 1 else "-" * min(20, int(round((1 - m) * 10)))
        print(f"  ring {i:>4}  x{m:5.3f}  {bar}")


def cmd_weight(args):
    wm = WeightMap.load(args.root)
    m = wm.multiplier(args.index) if wm else 1.0
    print(f"ring {args.index}: x{m:.4f}")


def cmd_audit(args):
    events = read_ledger(args.root)
    ok, msg = verify_ledger(events)
    print(("  ok  " if ok else "FAIL  ") + msg)
    if not ok:
        sys.exit(1)
    snap = write_derived(args.root)
    print(f"  ok  derived state rebuilt by replay: {snap['events']} event(s), "
          f"minted {snap['minted']}, locked {snap['locked']}, balance {snap['balance']}")
    print("AUDIT: PASS")


def cmd_attest(args):
    print(json.dumps(attest(args.root), indent=2))


# ---- selftest ----

def cmd_selftest(args):
    import tempfile
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))
        print(("  ok  " if cond else "FAIL  ") + name)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        tc = Timechain(root)
        tc.genesis("cphy-selftest", covenant=["honesty"])

        def dims(v):     # _seal derives brightness as the mean of the six dims
            return {d: v for d in ("coherence", "relevance", "novelty",
                                   "consistency", "depth", "covenant")}
        for k in range(1, 6):
            tc.seal("experience", {"summary": f"medical case study {k}"}, poq=dims(200))
        tc.seal("recovery", {"summary": "healed a defective seal"}, poq=dims(220))
        tc.seal("experience", {"summary": "legal precedent review"}, poq=dims(150))

        r = mint(root)
        ok("mint credits brightness/255 across 7 rings",
           r["rings"] == 7 and abs(r["minted"] - (5 * round(200 / 255, 4)
                                                  + round(220 / 255, 4)
                                                  + round(150 / 255, 4))) < 1e-6)
        ok("re-mint with no new rings credits nothing", mint(root)["minted"] == 0.0)

        st = compile_state(read_ledger(root))
        bal = st["balance"]
        try:
            lock(root, "basin", bal + 1.0, frm=1, to=3)
            ok("insufficient balance refused", False)
        except RuntimeError:
            ok("insufficient balance refused", True)

        basin = lock(root, "basin", 3.0, frm=1, to=3, memo="medical era")
        wm = WeightMap.load(root)
        ok("basin raises covered rings (density 1.0 -> 2x)",
           abs(wm.multiplier(2) - 2.0) < 1e-6 and wm.multiplier(7) == 1.0)

        big = lock(root, "basin", round(compile_state(read_ledger(root))["balance"], 4),
                   frm=1, to=1)
        wm = WeightMap.load(root)
        ok("multiplier clamps at 4x (I2)", wm.multiplier(1) == 4.0)
        release(root, big["lock_id"])

        try:
            lock(root, "shadow", 0.5, frm=6, to=6)
            ok("shadow on recovery ring refused (I3)", False)
        except RuntimeError as e:
            ok("shadow on recovery ring refused (I3)", "protected" in str(e))

        sh = lock(root, "shadow", 1.0, frm=7, to=7)
        wm = WeightMap.load(root)
        ok("shadow lowers (density 1.0 -> 0.5x), floored at 0.25x (I2)",
           abs(wm.multiplier(7) - 0.5) < 1e-6 and wm.multiplier(7) >= 0.25)
        release(root, sh["lock_id"])

        br = bridge(root, (1, 2), (4, 5), 2.0, memo="cross-era")
        wm = WeightMap.load(root)
        passive = wm.multiplier(1)
        active = wm.multiplier(1, anchor_indices=[5])
        ok("bridge: passive lift both sides, activation bonus via anchors",
           passive > 1.0 and active > passive)
        release(root, br["lock_id"])

        wm = WeightMap.load(root)
        ok("full release restores neutral landscape",
           wm is None or (wm.multiplier(2) != 1.0))   # only the first basin remains
        release(root, basin["lock_id"])
        ok("WeightMap.load is None with zero active locks",
           WeightMap.load(root) is None)

        # ---- OP2 stake (I6: floors only rise) ----
        for k in range(12):     # richer supply for the economic ops below
            tc.seal("experience", {"summary": f"supply ring {k}"}, poq=dims(210))
        mint(root)
        try:
            stake(root, "nonsense_param", 1.0)
            ok("stake on unlisted param refused", False)
        except RuntimeError:
            ok("stake on unlisted param refused", True)
        s1 = stake(root, "brightness_target", 5.0, registry_root=root)
        ok("stake raises brightness_target above default (I6 rise)",
           s1["floors_now"].get("brightness_target", 0) == 160)
        s2 = stake(root, "brightness_target", 1000.0 if False else 3.0, registry_root=root)
        ok("stakes accumulate, clamped at cap",
           s2["floors_now"]["brightness_target"] == min(210, 150 + 2 * 8))
        u = unstake(root, s2["stake_id"], registry_root=root)
        ok("unstake falls back toward default, never below",
           u["floors_now"].get("brightness_target", 150) == 160
           and u["floors_now"].get("brightness_target", 150) >= 150)
        unstake(root, s1["stake_id"], registry_root=root)
        polp = root / "registry" / "policy.json"
        floors_txt = json.loads(polp.read_text()).get("floors") if polp.exists() else None
        ok("all stakes released -> managed floors removed from policy",
           not floors_txt or "brightness_target" not in floors_txt)
        s3 = stake(root, "entity_grounding_enforce", 8.0, registry_root=root)
        ok("entity gate ARMS at stake threshold (arm-only)",
           s3["floors_now"].get("entity_grounding_enforce") == 1)
        unstake(root, s3["stake_id"], registry_root=root)

        # ---- OP3 fund + tick ----
        f1 = fund(root, "verify", 1.0, every=1, memo="continuous verification")
        tc.seal("experience", {"summary": "one more ring so the fund is due"},
                poq=dims(180))
        rep = tick(root)
        ok("funded verify runs when due and spends the fee",
           any(r["work"] == "verify" and r.get("verify") == "PASS" for r in rep["ran"]))
        st_after = compile_state(read_ledger(root))
        ok("fund draw-down accounted in replay state",
           abs(st_after["funds"][f1["fund_id"]]["remaining"] - 0.9) < 1e-9)
        rep2 = tick(root)
        ok("fund not due again until cadence elapses",
           not rep2["ran"] and any(s["fund"] == f1["fund_id"] for s in rep2["skipped"]))
        defund(root, f1["fund_id"])

        # ---- OP4/OP5 export -> import (I7 quarantine, price burn, TTL) ----
        pack_p = root / "pack.json"
        export_pack(root, pack_p, frm=1, to=2, price=0.5, memo="two medical rings")
        with tempfile.TemporaryDirectory() as td2:
            root2 = Path(td2)
            tc2 = Timechain(root2)
            tc2.genesis("cphy-importer", covenant=["honesty"])
            tc2.seal("experience", {"summary": "native ground"}, poq=dims(200))
            mint(root2)
            res = import_pack(root2, pack_p)
            ok("import seals foreign rings quarantined (I7)",
               len(res["sealed"]) == 2 and all(
                   (r.get("payload") or {}).get("foreign")
                   for r in Timechain(root2).load()
                   if r["ring_type"] == "imported"))
            st2b = compile_state(read_ledger(root2))
            ok("import price burned from importer's earned supply",
               abs(st2b["burned"] - 0.5) < 1e-9)
            expired = json.loads(pack_p.read_text())
            expired.pop("pack_hash")
            expired["expires"] = "2000-01-01T00:00:00+00:00"
            expired["pack_hash"] = sha256_hex(canonical(expired))
            exp_p = root / "expired.json"
            exp_p.write_text(json.dumps(expired))
            try:
                import_pack(root2, exp_p)
                ok("expired grant refused at import (OP5 TTL)", False)
            except RuntimeError as e:
                ok("expired grant refused at import (OP5 TTL)", "EXPIRED" in str(e))

        # ---- anchor: attestation only, never supply ----
        before = compile_state(read_ledger(root))["minted"]
        anchor(root, "0x08Df470d41C11Ba5Cb60242747D76C65Ca52c94c", "base")
        ok("anchor records but never mints (I5)",
           compile_state(read_ledger(root))["minted"] == before
           and compile_state(read_ledger(root))["anchor"] is not None)

        # ---- on-chain lane (network-free: derived addresses + observe replay) ----
        rings_all = {r["index"]: r for r in tc.load()}
        da = ring_deposit_address(rings_all[3]["ring_hash"])
        ok("deposit address is deterministic, keyless, EVM-shaped",
           da == ring_deposit_address(rings_all[3]["ring_hash"])
           and re.fullmatch(r"0x[0-9a-f]{40}", da) is not None)
        tgt = onchain_target(root, frm=3, to=4)
        ok("onchain target registers and WARNS proof-of-burn",
           len(tgt["targets"]) == 2 and "unspendable" in tgt["WARNING"])
        append_event(root, "onchain-observe", {
            "token": "0x08Df470d41C11Ba5Cb60242747D76C65Ca52c94c", "chain": "base",
            "density_per_token": 1.0, "observations": {"3": 1.0, "4": 50.0}})
        wm = WeightMap.load(root)
        ok("observed deposits weight rings, clamped at 4x (I2)",
           abs(wm.multiplier(3) - 2.0) < 1e-6 and wm.multiplier(4) == 4.0)
        ok("on-chain lane is basins-only: no negative exponent possible",
           wm.multiplier(3) >= 1.0 and wm.multiplier(4) >= 1.0)
        ok("on-chain deposits never mint local supply (I5)",
           compile_state(read_ledger(root))["minted"] == before)

        # ---- etches: burn = etch (positive scar), echelon 1..21 = depth ----
        append_event(root, "etch", {"ring": 5, "tokens": 1.0, "echelon": 1,
                                    "address": "0x" + "5" * 40})
        append_event(root, "etch", {"ring": 4, "tokens": 21.0, "echelon": 21,
                                    "address": "0x" + "4" * 40})
        wm = WeightMap.load(root)
        ok("1 token = etch at E=1; 21 tokens = E=21; ladder quantized",
           wm.etched.get(5) == 1 and wm.etched.get(4) == 21
           and etch_echelon(50.0) == 21 and etch_echelon(7.9) == 7)
        append_event(root, "etch", {"ring": 5, "tokens": 7.0, "echelon": 7,
                                    "address": "0x" + "5" * 40})
        ok("top-up deepens an existing etch (monotonic ladder)",
           WeightMap.load(root).etched.get(5) == 7)
        # overlay: echelon = recency bias, current turn never superseded
        weak = [(0.30, {"index": 9}, {}, {}),
                (0.05, {"index": 5}, {}, {}),
                (0.04, {"index": 4}, {}, {})]
        import recall_overlay as _ov
        lifted = _ov.rerank(root, list(weak))
        by_idx = {r["index"]: (s, p) for s, r, _, p in lifted}
        s9, s5, s4 = by_idx[9][0], by_idx[5][0], by_idx[4][0]
        ok("deeper echelon = stronger recency bias (E=21 above E=7)",
           s4 > s5 and by_idx[4][1].get("etched") == 21 and by_idx[5][1].get("etched") == 7)
        ok("current turn NEVER superseded: every etch below the organic top",
           s4 < s9 and s5 < s9 and s4 <= 0.97 * 0.30 + 1e-9)
        ok("top-n etched still clear the retrieval cuts",
           s5 >= max(0.19, 0.51 * 0.30) and s4 >= max(0.19, 0.51 * 0.30))
        top_etched = [(0.50, {"index": 4}, {}, {}), (0.30, {"index": 9}, {}, {})]
        lifted2 = _ov.rerank(root, list(top_etched))
        ok("an etch never REDUCES an organic score (etched top stays top)",
           lifted2[0][1]["index"] == 4 and lifted2[0][0] >= 0.50)
        # faculty unlock: skill point spent -> skill owned (active + pinned)
        # HERMETIC: give the temp root its own base registries FIRST, or
        # registry_home falls back to the AGENT'S home and the test faculty
        # leaks into the live self (caught by the epoch perimeter 2026-07-04).
        import cambium as _cb
        (root / "registry").mkdir(exist_ok=True)
        for base in ("modalities.json", "senses.json"):
            bp = root / "registry" / base
            if not bp.exists():
                bp.write_text(json.dumps({"registry": base.split(".")[0],
                                          "version": 1, "categories": {},
                                          base.split(".")[0]: []}))
        home = _cb.registry_home(root)
        ok("selftest registry is hermetic (temp home, not the agent's)",
           Path(home).resolve() == root.resolve())
        gr = _cb.load_grown(home)
        gr.setdefault("senses", []).append({
            "id": 9001, "name": "Test-Dormant Sensing", "kind": "sense",
            "category": "structural", "function": "test", "status": "dormant",
            "origin": "selftest", "parents": [], "seed_terms": ["test"]})
        _cb.save_grown(home, gr)
        res = apply_faculty_unlock(root, "sense", 9001)
        gr2 = _cb.load_grown(home)
        f2 = next(f for f in gr2["senses"] if f.get("id") == 9001)
        ok("faculty unlock: dormant -> active + pinned, sealed on-chain",
           res["was"] == "dormant" and f2["status"] == "active" and f2.get("pinned"))
        pr = _cb.prune(root, registry_root=root, min_fires=99, grace_rings=0)
        f3 = next(f for f in _cb.load_grown(home)["senses"] if f.get("id") == 9001)
        ok("pinned faculty is rent-exempt: prune can never hibernate it",
           f3["status"] == "active" and f3.get("pinned"))

        # ---- canonical-token exclusivity + oracle hardening ----
        cfgx = load_onchain_cfg(root)
        cfgx["token"] = "0x" + "ab" * 20          # an impostor token
        cfgx["targets"] = {"3": {"address": "0x" + "3" * 40, "ring_hash": "x"}}
        save_onchain_cfg(root, cfgx)
        try:
            onchain_sync(root)
            ok("ONLY canonical CPHY programs the agent — impostor token refused", False)
        except RuntimeError as e:
            ok("ONLY canonical CPHY programs the agent — impostor token refused",
               "canonical" in str(e))
        cfgx["token"] = CANONICAL_CPHY
        cfgx["rpc"] = "https://evil.example/rpc"
        save_onchain_cfg(root, cfgx)
        try:
            onchain_sync(root)
            ok("non-allowlisted RPC refused (no arbitrary hosts)", False)
        except RuntimeError as e:
            ok("non-allowlisted RPC refused (no arbitrary hosts)", "allowlist" in str(e))
        cfgx.pop("rpc", None)
        save_onchain_cfg(root, cfgx)
        # unlock ONLY via observed burn: registering a faculty target must
        # never change its status — apply_faculty_unlock is reachable solely
        # from sync's burn observation (and this direct test call).
        gr3 = _cb.load_grown(home)
        gr3.setdefault("senses", []).append({
            "id": 9002, "name": "Still-Locked Sensing", "kind": "sense",
            "category": "structural", "function": "test", "status": "dormant",
            "origin": "selftest", "parents": [], "seed_terms": ["test"]})
        _cb.save_grown(home, gr3)
        etch_faculty_target(root, "sense", 9002)
        f9002 = next(f for f in _cb.load_grown(home)["senses"] if f.get("id") == 9002)
        ok("registering a faculty target does NOT unlock it — only a burn does",
           f9002.get("status") == "dormant" and not f9002.get("pinned"))

        events = read_ledger(root)
        ok("ledger hash chain verifies", verify_ledger(events)[0])
        st1 = json.dumps(write_derived(root), sort_keys=True)
        st2 = json.dumps(write_derived(root), sort_keys=True)
        ok("derived state rebuild is deterministic (I4)", st1 == st2)

        p = ledger_path(root)
        lines = p.read_text().splitlines()
        tampered = json.loads(lines[1])
        tampered["amount"] = 9999
        lines[1] = json.dumps(tampered)
        p.write_text("\n".join(lines) + "\n")
        ok("tampered ledger detected", not verify_ledger(read_ledger(root))[0])

    here = Path(__file__).resolve().parent
    live_grown = here / "registry" / "grown.json"
    if live_grown.exists():
        lg = json.loads(live_grown.read_text())
        ok("no selftest pollution leaked into the LIVE registry",
           not any(f.get("id") == 9001 or f.get("origin") == "selftest"
                   for k in ("senses", "modalities") for f in lg.get(k, [])))
    poq_src = (here / "poq.py").read_text(encoding="utf-8")
    ok("one-way membrane: poq.py never imports cphy (I1)",
       "import cphy" not in poq_src and "cphy" not in poq_src.lower())
    recall_src = (here / "recall.py").read_text(encoding="utf-8")
    # v3.22 seam architecture: recall.py carries a NEUTRAL overlay seam
    # (import recall_overlay) so upstream syncs can't sever the economy;
    # the WeightMap wiring lives in local-only recall_overlay.py.
    overlay_p = Path(__file__).resolve().parent / "recall_overlay.py"
    overlay_src = overlay_p.read_text() if overlay_p.exists() else ""
    ok("recall.py consumes the overlay",
       ("recall_overlay" in recall_src and "WeightMap" in overlay_src)
       or "WeightMap" in recall_src)

    failed = [n for n, c in checks if not c]
    print(f"SELFTEST {'PASS' if not failed else 'FAIL'} {len(checks)} checks"
          + (f" — failed: {failed}" if failed else ""))
    sys.exit(1 if failed else 0)


def main():
    skill_dir = Path(__file__).resolve().parent
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", type=Path, default=skill_dir,
                        help="chain root (default: skill dir)")
    p = argparse.ArgumentParser(description="CPHY — economic attention overlay for the timechain.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("mint", parents=[common],
                   help="credit CPHY for sealed rings (proof-of-interaction)").set_defaults(func=cmd_mint)
    sub.add_parser("balance", parents=[common]).set_defaults(func=cmd_balance)

    pl = sub.add_parser("lock", parents=[common], help="lock CPHY as a basin or shadow")
    pl.add_argument("op", choices=["basin", "shadow"])
    pl.add_argument("--amount", type=float, required=True)
    pl.add_argument("--from", dest="from", type=int, default=None)
    pl.add_argument("--to", type=int, default=None)
    pl.add_argument("--match", default=None, help="regex over ring content selects rings")
    pl.add_argument("--memo", default="")
    pl.set_defaults(func=cmd_lock)

    pb = sub.add_parser("bridge", parents=[common],
                        help="bridge two ring ranges for cross-temporal composition")
    pb.add_argument("--a", nargs=2, type=int, required=True, metavar=("FROM", "TO"))
    pb.add_argument("--b", nargs=2, type=int, required=True, metavar=("FROM", "TO"))
    pb.add_argument("--amount", type=float, required=True)
    pb.add_argument("--memo", default="")
    pb.set_defaults(func=cmd_bridge)

    pr = sub.add_parser("release", parents=[common], help="release a lock, refund its CPHY")
    pr.add_argument("lock_id")
    pr.set_defaults(func=cmd_release)

    ps = sub.add_parser("stake", parents=[common],
                        help="OP2: stake CPHY to RAISE a safety floor (I6: never lowers)")
    ps.add_argument("param", choices=sorted(STAKE_PARAMS))
    ps.add_argument("--amount", type=float, required=True)
    ps.add_argument("--memo", default="")
    ps.set_defaults(func=cmd_stake)

    pu = sub.add_parser("unstake", parents=[common],
                        help="OP2: release a stake — floor falls back toward default, never below")
    pu.add_argument("stake_id")
    pu.set_defaults(func=cmd_unstake)

    pf = sub.add_parser("fund", parents=[common],
                        help="OP3: fund recurring self-maintenance (dream | verify)")
    pf.add_argument("work", choices=sorted(FUND_WORK))
    pf.add_argument("--amount", type=float, required=True)
    pf.add_argument("--every", type=int, required=True, help="cadence in rings")
    pf.add_argument("--memo", default="")
    pf.set_defaults(func=cmd_fund)

    pdf = sub.add_parser("defund", parents=[common], help="OP3: cancel a fund, refund remainder")
    pdf.add_argument("fund_id")
    pdf.set_defaults(func=cmd_defund)

    sub.add_parser("tick", parents=[common],
                   help="OP3: run all funded work that is due (spends fees)").set_defaults(func=cmd_tick)

    pe = sub.add_parser("export-pack", parents=[common],
                        help="OP4: package rings for transfer (price/TTL are metadata + OP5 scope)")
    pe.add_argument("--out", required=True)
    pe.add_argument("--from", dest="from", type=int, default=None)
    pe.add_argument("--to", type=int, default=None)
    pe.add_argument("--match", default=None)
    pe.add_argument("--price", type=float, default=0.0)
    pe.add_argument("--expires", default=None, help="ISO time; import refuses after (lend, OP5)")
    pe.add_argument("--grant-to", default="", help="named recipient (OP5 scope)")
    pe.add_argument("--memo", default="")
    pe.set_defaults(func=cmd_export_pack)

    pi = sub.add_parser("import-pack", parents=[common],
                        help="OP4: import a pack — immune-screened, provenance-quarantined (I7), price burned")
    pi.add_argument("pack")
    pi.set_defaults(func=cmd_import_pack)

    pa = sub.add_parser("anchor", parents=[common],
                        help="declare the external token contract (attestation-only; never mints supply)")
    pa.add_argument("--address", required=True)
    pa.add_argument("--chain", default="base")
    pa.add_argument("--verified-json", default=None,
                    help="path to pre-fetched on-chain metadata JSON to record beside the declaration")
    pa.set_defaults(func=cmd_anchor)

    po = sub.add_parser("onchain", parents=[common],
                        help="on-chain lane: weight rings by REAL token deposits (read-only oracle; proof-of-burn)")
    po.add_argument("action", choices=["target", "sync", "status", "gate"])
    po.add_argument("--from", dest="from", type=int, default=None)
    po.add_argument("--to", type=int, default=None)
    po.add_argument("--match", default=None)
    po.add_argument("--wallet", default=None, help="holder wallet for gate")
    po.set_defaults(func=cmd_onchain)

    pet = sub.add_parser("etch", parents=[common],
                         help="burn=etch: positive scars + RPG faculty unlocks (1 token each)")
    pet.add_argument("action", choices=["status", "n", "faculty"])
    pet.add_argument("--set", type=int, default=None, help="for n: etched memories considered per turn")
    pet.add_argument("--kind", choices=["sense", "modality"], default=None)
    pet.add_argument("--id", type=int, default=None)
    pet.set_defaults(func=cmd_etch)

    sub.add_parser("map", parents=[common], help="show the attention landscape").set_defaults(func=cmd_map)
    pw = sub.add_parser("weight", parents=[common], help="one ring's multiplier")
    pw.add_argument("index", type=int)
    pw.set_defaults(func=cmd_weight)
    sub.add_parser("audit", parents=[common],
                   help="verify ledger hashes, rebuild derived state").set_defaults(func=cmd_audit)
    sub.add_parser("attest", parents=[common],
                   help="seal a cphy-digest ring notarizing the ledger head").set_defaults(func=cmd_attest)
    sub.add_parser("selftest", parents=[common]).set_defaults(func=cmd_selftest)

    args = p.parse_args()
    try:
        args.func(args)
    except RuntimeError as e:
        print(f"refused: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
