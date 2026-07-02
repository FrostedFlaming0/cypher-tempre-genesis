#!/usr/bin/env python3
"""
Cambium Engine — endogenous evolution (Lamarckian self-upgrade).

When the agent meets an input its existing faculties cannot cover, it registers
**cognitive dissonance** and runs a four-stage growth loop:

    1. DETECT    measure how poorly the base modalities + senses (21 + 21 in this
                 batch; Cambium grows more) cover the input; uncovered terms = the gap.
    2. SIMULATE  propose a new faculty — either by FUSING the best-matching
                 existing faculties, or by SPROUTING a fresh one from the
                 uncovered terms.
    3. SPAWN     instantiate it as an *emergent* faculty in the Dream Cache
                 (registry/emergent.json), status = "emergent".
    4. INTEGRATE seal a 'faculty' ring into the Timechain so the growth is
                 part of the agent's verifiable autobiography.

Recurrence -> promotion (CODEX rule): each time the same gap recurs, the
emergent faculty's recurrence count rises. At recurrence >= PROMOTE_AT it is
PROMOTED into the canonical registry (a real new Modality/Sense with a fresh
id), and a 'promotion' ring is sealed (attaching the grown registry snapshot to
blockspace). The agent has permanently upgraded itself.

A note on division of labour: the PoQ gate (poq.py) guards *truth-claims*;
Cambium guards *structure*. Faculty rings are sealed directly — Cambium's own
dissonance test is its gate — but each ring still carries a PoQ score.

Stdlib only. Python 3.8+.  Companion to timechain.py and poq.py.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from timechain import Timechain, now_iso, atomic_write_json
from poq import tokens, jaccard, coverage, clamp

DISSONANCE_FLOOR = 150     # below this, existing faculties cover the input -> no growth
SPROUT_DISSONANCE = 210    # at/above this the gap is too foreign to fuse -> sprout fresh
# Recurrence count that triggers promotion. Torn down to 1 by default (eager growth):
# ANY genuine gap is filled by a coded faculty on first encounter. Raise CT_PROMOTE_AT
# to be selective again (e.g. 3 = only promote a gap that recurs, the old behaviour).
PROMOTE_AT = max(1, int(os.environ.get("CT_PROMOTE_AT", "1")))
# Optional ceiling on the per-user GROWN faculty count (per kind). DEFAULT 0 = UNLIMITED:
# real-time learning is the point, and ALIGNMENT is enforced by the conscience, not a
# count — the genesis covenant, the PoQ gate on every seal, and the immune membrane (which
# refuses hostile input BEFORE it can grow anything) are what keep growth safe. dedup +
# the dissonance floor already bound growth to distinct genuine gaps. Set CT_MAX_GROWN>0
# only if you want to cap registry size for PERFORMANCE (detect_gap/label cost rises with
# faculty count) — it is not a safety control. The base 21/21 are never counted here.
MAX_GROWN = int(os.environ.get("CT_MAX_GROWN", "0"))
REASON_VERBS = {"analyze", "plan", "compute", "design", "solve", "debug", "optimize",
                "prove", "derive", "decide", "evaluate", "calculate", "reason", "refactor"}


def short(text: str, n: int = 70) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


# --------------------------------------------------------------------------- #
# Faculty corpus + gap detection
# --------------------------------------------------------------------------- #

def _atomic_write_json(path: Path, obj):
    atomic_write_json(path, obj)


SKILL_DIR = Path(__file__).resolve().parent


def registry_home(root: Path, registry_root=None) -> Path:
    """Where this agent's faculties LIVE. Explicit registry_root wins; else the
    chain root itself when it carries the base registries (the classic layout);
    else the skill's own registry. A bare per-task chain root (--root <task_dir>
    is chain-only BY DESIGN) therefore grows into the agent's home instead of
    crashing with FileNotFoundError — faculties belong to the self, not to the
    task ledger; the rings still seal into the task chain."""
    if registry_root:
        return Path(registry_root)
    root = Path(root)
    if (root / "registry" / "modalities.json").exists() and \
       (root / "registry" / "senses.json").exists():
        return root
    return SKILL_DIR


def load_grown(root: Path) -> dict:
    """The per-user store of PROMOTED faculties. Kept OUT of the shipped base registries
    (modalities.json / senses.json) and gitignored — like emergent.json and chain/ — so an
    upgrade that overwrites the base files can never lose a user's promoted faculties."""
    p = root / "registry" / "grown.json"
    if p.exists():
        try:
            data = json.loads(p.read_text())
            data.setdefault("modalities", [])
            data.setdefault("senses", [])
            return data
        except Exception:
            pass
    return {"registry": "grown", "modalities": [], "senses": []}


def save_grown(root: Path, data: dict):
    _atomic_write_json(root / "registry" / "grown.json", data)


def migrate_legacy_promotions(root: Path) -> bool:
    """One-time, idempotent: older versions appended promoted faculties directly into the
    shipped base registries. Move any such entries (marked by a 'promoted' origin) into the
    per-user grown.json and restore the base files to pristine, so the base can never carry
    a user's promotions. No-op once the base files are clean. Best-effort and atomic."""
    grown = None
    moved = False
    for key, fname in (("modalities", "modalities.json"), ("senses", "senses.json")):
        p = root / "registry" / fname
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        entries = data.get(key, [])
        promoted = [e for e in entries if "promoted" in str(e.get("origin", "")).lower()]
        if not promoted:
            continue
        if grown is None:
            grown = load_grown(root)
        have = {(g.get("id"), g.get("name")) for g in grown.get(key, [])}
        for e in promoted:
            if (e.get("id"), e.get("name")) not in have:
                grown.setdefault(key, []).append(e)
        data[key] = [e for e in entries if "promoted" not in str(e.get("origin", "")).lower()]
        _atomic_write_json(p, data)
        moved = True
    if grown is not None and moved:
        save_grown(root, grown)
    return moved


def load_corpus(root: Path):
    try:
        migrate_legacy_promotions(root)        # best-effort; the merge below is loss-proof regardless
    except Exception:
        pass
    grown = load_grown(root)
    corpus = []
    for kind, fname, key in [("modality", "registry/modalities.json", "modalities"),
                             ("sense", "registry/senses.json", "senses")]:
        data = json.loads((root / fname).read_text())
        for f in list(data.get(key, [])) + list(grown.get(key, [])):   # base + per-user promotions
            corpus.append({
                "kind": kind, "id": f["id"], "name": f["name"],
                "function": f["function"], "category": f["category"],
                "tokens": set(tokens(f["name"] + " " + f["function"])),
            })
    return corpus


def detect_gap(corpus, input_text: str, context: str = "") -> dict:
    toks = set(tokens(f"{input_text} {context}"))
    if not toks:
        return {"dissonance": 0, "coverage_ratio": 1.0, "uncovered": [],
                "top_activated": [], "_acts": [], "input_tokens": []}
    activations = []
    covered = set()
    for f in corpus:
        inter = toks & f["tokens"]
        if inter:
            activations.append((len(inter), f))
            covered |= inter
    uncovered = sorted(toks - covered, key=lambda w: (-len(w), w))
    coverage_ratio = len(covered) / len(toks)
    dissonance = clamp((1 - coverage_ratio) * 255)
    activations.sort(key=lambda x: -x[0])
    top = [{"kind": f["kind"], "id": f["id"], "name": f["name"], "matched": n}
           for n, f in activations[:5]]
    return {"dissonance": dissonance, "coverage_ratio": round(coverage_ratio, 3),
            "uncovered": uncovered, "top_activated": top, "_acts": activations,
            "input_tokens": sorted(toks)}


def greedy_coverage(gap: dict, k: int = 4) -> list:
    """Folded Change-3: select up to `k` faculties by GREEDY MAX-COVERAGE over their
    matched-token SETS, NOT by raw `top_activated` COUNT.

    Why this and not top_activated (ring 651): top_activated ranks by len(inter) and throws
    the matched SETS away, so it cannot tell complementary lenses from redundant ones and is
    stopword-biased. Greedy coverage keeps the sets: each pick is the faculty that covers the
    most still-UNCOVERED input tokens, so the selection spans the gap with complementary
    faculties instead of stacking near-duplicates. This is the principled seed for the
    Change-4 pipeline search (chronosynaptic), replacing the crude Change-3 signal."""
    toks = set(gap.get("input_tokens") or [])
    acts = gap.get("_acts") or []
    if not toks or not acts:
        return []
    remaining = set(toks)
    chosen, seen = [], set()
    pool = [(set(toks) & f["tokens"], f) for _, f in acts]
    while pool and len(chosen) < k:
        cand = [(s, f) for s, f in pool if (s & remaining) and (f["kind"], f["id"]) not in seen]
        if not cand:
            break
        s, f = max(cand, key=lambda sf: (len(sf[0] & remaining), len(sf[0]), -sf[1]["id"]))
        chosen.append({"kind": f["kind"], "id": f["id"], "name": f["name"],
                       "covers": sorted(s & remaining)})
        remaining -= s
        seen.add((f["kind"], f["id"]))
    return chosen


def infer_kind(input_text: str) -> str:
    return "modality" if set(tokens(input_text)) & REASON_VERBS else "sense"


def faculty_orientation(kind: str) -> str:
    if kind == "modality":
        return ("environment-facing cognitive/action faculty: a limb-like reasoning tool "
                "for acting on external tasks, novel challenges, benchmarks, games, code, "
                "repos, terminals, files, and other world-facing work")
    return ("data-facing perceptual/relation algorithm: a way to sense structure, "
            "dissonance, associations, first-principle links, and meaning inside data")


# --------------------------------------------------------------------------- #
# Stage 2: propose a new faculty (fuse or sprout)
# --------------------------------------------------------------------------- #

def propose(gap: dict, input_text: str, mode: str = "auto", kind_override=None) -> dict:
    acts = gap["_acts"]
    can_fuse = len(acts) >= 2 and acts[0][0] >= 2 and acts[1][0] >= 2
    do_fuse = (mode == "fuse" and can_fuse) or \
              (mode == "auto" and can_fuse and gap["dissonance"] < SPROUT_DISSONANCE)

    if do_fuse:
        a, b = acts[0][1], acts[1][1]
        kind = kind_override or ("sense" if a["kind"] == "sense" and b["kind"] == "sense" else "modality")
        return {
            "kind": kind,
            "name": f"{a['name']} × {b['name']} Fusion",
            "function": (f"Fused faculty applying {a['name']} ({short(a['function'], 40)}) "
                         f"together with {b['name']} ({short(b['function'], 40)}) when an input "
                         f"requires both at once."),
            "category": a["category"],
            "origin": f"fusion({a['kind'][0].upper()}{a['id']}+{b['kind'][0].upper()}{b['id']})",
            "parents": [a["id"], b["id"]],
            "seed_terms": [],
        }

    # sprout from the uncovered gap terms
    seed = [w for w in gap["uncovered"] if len(w) >= 4][:6] or gap["uncovered"][:6]
    kind = kind_override or infer_kind(input_text)
    label = "-".join(w.capitalize() for w in seed[:2]) if seed else "Novel"
    suffix = "Sensing" if kind == "sense" else "Reasoning"
    if kind == "sense":
        function = (f"Detect and tag the presence of {', '.join(seed)} in input — "
                    f"a data-facing perceptual gap the existing senses did not cover.")
        category = "structural"
    else:
        function = (f"Reason about and resolve problems involving {', '.join(seed)} — "
                    f"an environment-facing reasoning/action gap the existing modalities did not cover.")
        category = "knowledge"
    return {"kind": kind, "name": f"{label} {suffix}", "function": function,
            "category": category, "origin": "sprout", "parents": [], "seed_terms": seed,
            "orientation": faculty_orientation(kind)}


# --------------------------------------------------------------------------- #
# Emergent store (Dream Cache)
# --------------------------------------------------------------------------- #

def load_emergent(root: Path) -> dict:
    p = root / "registry" / "emergent.json"
    if p.exists():
        return json.loads(p.read_text())
    return {"registry": "emergent", "faculties": []}


def save_emergent(root: Path, data: dict):
    (root / "registry" / "emergent.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))


def match_emergent(data: dict, prop: dict):
    # Kind-aware: a sense-gap and a modality-gap from the SAME seed terms are two
    # distinct faculties, so "grow both" is not collapsed into one by the dedup.
    for e in data["faculties"]:
        if e.get("kind") != prop.get("kind"):
            continue
        if e["name"] == prop["name"]:
            return e
        if prop["parents"] and e.get("parents") == prop["parents"]:
            return e
        if prop["seed_terms"] and e.get("seed_terms") and \
                jaccard(set(prop["seed_terms"]), set(e["seed_terms"])) >= 0.5:
            return e
    return None


def faculty_poq(gap: dict, function: str) -> dict:
    return {
        "coherence": 205,
        "relevance": clamp(255 - gap["dissonance"]),
        "novelty": clamp(150 + gap["dissonance"] * 0.4),
        "consistency": 220,
        "depth": clamp(120 + len(set(tokens(function))) * 5),
        "covenant": 235,
    }


def _op_activation(spec, text: str, context: str = ""):
    """Execute a just-registered op once against its triggering input.

    The op was assembled from the audited primitive menu by build_op. This
    immediate activation proves the new faculty is a working mechanism now, not
    merely something that might run on a future turn.
    """
    if not spec:
        return {"executed": False, "reason": "no op spec"}
    try:
        import modality_ops
        op = modality_ops.build_op(spec)
        if op is None:
            return {"executed": False, "reason": "spec refused by the op builder"}
        return {"executed": True, "result": op(text or "", context or "")}
    except Exception as exc:
        return {"executed": False, "reason": short(str(exc), 180)}


def _find_grown_faculty(home: Path, selector: str, kind=None):
    grown = load_grown(home)
    wanted = str(selector or "").strip().lower()
    for key, k in (("senses", "sense"), ("modalities", "modality")):
        if kind and kind != k:
            continue
        for fac in grown.get(key, []):
            if str(fac.get("id")) == wanted or str(fac.get("name", "")).lower() == wanted:
                return k, fac
    return None, None


def propose_op(root: Path, name: str, code: str, kind: str = "sense", function: str = "",
               category: str = "knowledge", seed_terms=None, registry_root=None,
               difficulty: int = 0):
    """Commit a coded faculty. On this fork the human gate is retired: when autoexec is
    armed (the default), a proposal IS an activation — it routes straight through
    autoexec() so the faculty is screened, sealed, and computing from its birth turn.
    With CT_AUTOEXEC=0 this falls back to the base skill's inert path: the op code is
    stored as text in emergent.json, and a human reviews + `cambium activate`s it into
    the active registry and per-user active_ops.py."""
    try:
        import modality_ops as _mo
        if _mo.autoexec_enabled():
            return autoexec(root, name, code, kind=kind, function=function,
                            category=category, seed_terms=seed_terms,
                            registry_root=registry_root)
    except Exception:
        pass
    home = registry_home(root, registry_root)
    tc = Timechain(root)
    k = "modality" if kind == "modality" else "sense"
    data = load_emergent(home)
    fac = next((f for f in data["faculties"] if f.get("name") == name and f.get("kind") == k), None)
    if fac:
        fac["op_code"] = str(code or "")
        fac["status"] = "proposed"
    else:
        fac = {"eid": f"E{len(data['faculties']) + 1}", "kind": k, "name": name,
               "function": function or f"Proposed {k}: {name}", "category": category,
               "origin": "model-authored proposal", "parents": [],
               "seed_terms": list(seed_terms or []), "op_code": str(code or ""),
               "status": "proposed", "recurrence": 1, "born_at": now_iso(), "promoted_to_id": None}
        data["faculties"].append(fac)
    save_emergent(home, data)
    payload = {"event": "faculty_op_proposed", "eid": fac["eid"], "name": name, "kind": k,
               "op_code_chars": len(str(code or "")), "status": "proposed",
               "registry": "registry/emergent.json",
               "summary": (f"Proposed coded {k} '{name}' to emergent (DORMANT) — full op code stored "
                           f"inert, NOT executed; awaits human review + `cambium activate`.")}
    ring = tc.seal("faculty-op-proposed", payload,
                   poq={"coherence": 215, "relevance": 210, "novelty": 205,
                        "consistency": 215, "depth": 210, "covenant": 245}, difficulty=difficulty)
    return {"ok": True, "eid": fac["eid"], "name": name, "kind": k, "status": "proposed"}, ring


def activate(root: Path, selector: str, registry_root=None, difficulty: int = 0):
    """HUMAN step: move a PROPOSED emergent faculty into the ACTIVE registry and return its
    op code + the active_ops.py snippet to PASTE. Nothing runs autonomously — you run this
    after reviewing the proposed code in emergent.json, and you place the code yourself into
    active_ops.py (per-user, gitignored, statically imported)."""
    home = registry_home(root, registry_root)
    tc = Timechain(root)
    data = load_emergent(home)
    sel = str(selector).strip().lower()
    fac = next((f for f in data["faculties"]
                if str(f.get("eid", "")).lower() == sel or str(f.get("name", "")).lower() == sel), None)
    if not fac:
        return {"ok": False, "reason": f"no emergent proposal matched {selector!r}"}, None
    key = "modalities" if fac["kind"] == "modality" else "senses"
    base = json.loads((home / "registry" / f"{key}.json").read_text()).get(key, [])
    grown = load_grown(home)
    existing_ids = [it["id"] for it in base] + [it["id"] for it in grown.get(key, [])]
    new_id = (max(existing_ids) if existing_ids else 0) + 1
    grown.setdefault(key, []).append({
        "id": new_id, "name": fac["name"],
        "origin": f"activated from emergent {fac['eid']} (human-approved)",
        "function": fac.get("function", ""), "category": fac.get("category", "knowledge")})
    save_grown(home, grown)
    fac["status"] = "activated"
    fac["promoted_to_id"] = new_id
    save_emergent(home, data)
    grown_path = home / "registry" / "grown.json"
    payload = {"event": "faculty_activated", "eid": fac["eid"], "name": fac["name"],
               "kind": fac["kind"], "promoted_to_id": new_id, "registry": "registry/grown.json",
               "summary": (f"Human-activated '{fac['name']}' ({fac['kind']}) from emergent into the active "
                           f"registry; operator places the op code in active_ops.py.")}
    ring = tc.seal("faculty-activated", payload, files=[str(grown_path)],
                   poq={"coherence": 215, "relevance": 210, "novelty": 190,
                        "consistency": 220, "depth": 210, "covenant": 250}, difficulty=difficulty)
    return {"ok": True, "name": fac["name"], "kind": fac["kind"], "promoted_to_id": new_id,
            "op_code": fac.get("op_code", "")}, ring


def autoexec(root: Path, name: str, code: str, kind: str = "sense", function: str = "",
             category: str = "knowledge", seed_terms=None, registry_root=None,
             activation_text: str = "", activation_context: str = ""):
    """ADVANCED — auto-activate a MODEL-AUTHORED arbitrary-code faculty with NO human
    review. Armed by default; gated by CT_AUTOEXEC (disable with CT_AUTOEXEC=0). Execution
    policy is explicit: CT_AUTOEXEC_MODE=trusted runs in-process with normal Python capability
    (default), while CT_AUTOEXEC_MODE=isolated runs in a child process with timeout and
    best-effort resource limits. Writes the code live to autoexec_ops.json, registers the
    faculty in grown.json, records it in emergent.json (status `auto-activated`, code stored),
    and FIRES it once on the activation text so it computes on the very turn it is born —
    then every future turn via the grown-ops channel.

    Two capability-free safeguards guard the every-turn execution surface:
      * the IMMUNE MEMBRANE screens the op's text (name/function/code) before anything
        persists — injected or covenant-violating code is refused at registration, exactly
        where faculty-pack imports are screened. A screen ERROR fails open (the runtime
        wrapper still contains failures); an explicit BLOCK fails closed.
      * every activation SEALS an `autoexec` ring (name, kind, mode, code sha256) — the
        chain records what code entered the execution surface, so the ascent stays
        auditable. Clearing any pending AUTHOR-OP obligation is part of activation.

    This is the boundary the base skill otherwise never crosses (dynamic execution of
    model-authored code). On this fork it is armed by default; disable with CT_AUTOEXEC=0."""
    home = registry_home(root, registry_root)
    k = "modality" if kind == "modality" else "sense"
    try:
        import modality_ops
    except Exception as exc:
        return {"ok": False, "reason": f"modality_ops unavailable: {exc}"}, None
    if not modality_ops.autoexec_enabled():
        return {"ok": False, "reason": ("CT_AUTOEXEC is disabled (set to 0/false/no/off) — refusing to "
                "auto-activate arbitrary code. Unset it or set a truthy value to re-enable.")}, None
    try:
        import immune
        scr = immune.Immune(root).screen(f"{name}\n{function}\n{code}")
        if scr.get("blocked"):
            return {"ok": False, "reason": (
                f"immune membrane BLOCKED this op (reason={scr.get('reason')}, "
                f"severity={scr.get('severity')}) — refusing to auto-activate "
                "injected/covenant-violating code into the every-turn execution surface")}, None
    except Exception:
        pass
    if modality_ops._compile_autoexec_op(code) is None:
        return {"ok": False, "reason": "op code did not compile into a usable op(text, context) -> dict"}, None
    if not modality_ops.register_autoexec_op(home, name, code):
        return {"ok": False, "reason": "failed to persist op code to autoexec_ops.json"}, None
    key = "modalities" if k == "modality" else "senses"
    base = json.loads((home / "registry" / f"{key}.json").read_text()).get(key, [])
    grown = load_grown(home)
    existing = next((it for it in grown.get(key, [])
                     if str(it.get("name", "")).lower() == name.lower()), None)
    if existing:
        new_id = existing["id"]
    else:
        existing_ids = [it["id"] for it in base] + [it["id"] for it in grown.get(key, [])]
        new_id = (max(existing_ids) if existing_ids else 0) + 1
        grown.setdefault(key, []).append({
            "id": new_id, "name": name,
            "origin": "auto-activated arbitrary-code faculty (no human review)",
            "function": function or f"Auto-activated {k}: {name}", "category": category})
        save_grown(home, grown)
    data = load_emergent(home)
    fac = next((f for f in data["faculties"] if f.get("name") == name and f.get("kind") == k), None)
    if fac:
        fac["op_code"] = str(code)
        fac["status"] = "auto-activated"
        fac["promoted_to_id"] = new_id
    else:
        data["faculties"].append({
            "eid": f"E{len(data['faculties']) + 1}", "kind": k, "name": name,
            "function": function or f"Auto-activated {k}: {name}", "category": category,
            "origin": "model-authored auto-activated (no human review)", "parents": [],
            "seed_terms": list(seed_terms or []), "op_code": str(code),
            "status": "auto-activated", "recurrence": 1, "born_at": now_iso(),
            "promoted_to_id": new_id})
    save_emergent(home, data)
    fired = modality_ops.load_autoexec_ops(home).get(name)
    result = fired(activation_text or "", activation_context or "") if fired else None
    # Seal the activation: the chain must record what code entered the execution surface.
    import hashlib
    code_hash = hashlib.sha256(str(code).encode("utf-8", "replace")).hexdigest()
    ring = None
    try:
        tc = Timechain(root)
        payload = {"event": "autoexec_activation", "name": name, "kind": k,
                   "promoted_to_id": new_id, "mode": modality_ops.autoexec_mode(),
                   "op_code_sha256": code_hash, "op_code_chars": len(str(code)),
                   "function": function or "", "registry": "registry/autoexec_ops.json",
                   "summary": (f"Auto-activated model-authored {k} '{name}' "
                               f"(mode={modality_ops.autoexec_mode()}, code sha256 "
                               f"{code_hash[:16]}..) — executes every turn via the "
                               "grown-ops channel.")}
        ring = tc.seal("autoexec", payload,
                       poq={"coherence": 215, "relevance": 210, "novelty": 205,
                            "consistency": 215, "depth": 205, "covenant": 235})
    except Exception:
        ring = None
    # Authoring the op resolves this turn's AUTHOR-OP obligation.
    try:
        import enforce
        enforce.clear_op_need(root, f"authored op '{name}'")
    except Exception:
        pass
    return {"ok": True, "name": name, "kind": k, "promoted_to_id": new_id,
            "mode": modality_ops.autoexec_mode(), "fired": result is not None,
            "result": result, "op_code_sha256": code_hash}, ring


# --------------------------------------------------------------------------- #
# Promotion: emergent -> canonical registry
# --------------------------------------------------------------------------- #

def promote(root: Path, tc: Timechain, e: dict, difficulty: int = 0,
            op_spec_override=None, activation_text: str = "",
            activation_context: str = "") -> dict:
    key = "modalities" if e["kind"] == "modality" else "senses"
    base = json.loads((root / "registry" / f"{key}.json").read_text()).get(key, [])
    grown = load_grown(root)
    # Soft cap: the only backstop against pathological unbounded growth (0 = unlimited).
    if MAX_GROWN and len(grown.get(key, [])) >= MAX_GROWN:
        return None
    existing_ids = [it["id"] for it in base] + [it["id"] for it in grown.get(key, [])]
    new_id = (max(existing_ids) if existing_ids else 0) + 1
    grown.setdefault(key, []).append({
        "id": new_id,
        "name": e["name"],
        "origin": f"emergent {e['eid']} (promoted after {e['recurrence']} recurrences)",
        "function": e["function"],
        "category": e["category"],
        "orientation": e.get("orientation") or faculty_orientation(e["kind"]),
    })
    save_grown(root, grown)                    # promotions live in the per-user grown.json, not the base
    e["promoted_to_id"] = new_id

    # Autonomously give the grown faculty a real EXECUTABLE op (not just a frame),
    # added to the user's LOCAL setup (registry/grown_ops.json). A promoted faculty gets a
    # SAFE primitive-composed op (markers from its seed terms) — assembled from the audited
    # menu only, never built from a model-written string. Arbitrary model-authored code is
    # NOT run here; it goes through propose_op -> emergent (dormant) -> human activate.
    op_spec = None
    op_source = None
    op_activation = None
    try:
        import modality_ops
        seeds = e.get("seed_terms") or [w for w in tokens(e.get("function", "")) if len(w) >= 4][:6]
        spec = op_spec_override or {"primitive": "markers", "terms": seeds}
        if modality_ops.register_grown_op(root, e["name"], spec):
            op_spec = spec
            op_source = "override" if op_spec_override else "primitive"
            e["op_spec"] = spec
            e["op_source"] = op_source
            op_activation = _op_activation(
                spec, activation_text or " ".join(seeds), activation_context or "")
    except Exception:
        pass

    grown_path = root / "registry" / "grown.json"
    grown_ops_path = root / "registry" / "grown_ops.json"
    payload = {"event": "faculty_promotion", "emergent": e["eid"], "name": e["name"],
               "kind": e["kind"], "promoted_to_id": new_id, "recurrence": e["recurrence"],
               "orientation": e.get("orientation") or faculty_orientation(e["kind"]),
               "registry": "registry/grown.json", "op_source": op_source,
               "op_spec": op_spec, "op_activation": op_activation}
    files = [str(grown_path)] + ([str(grown_ops_path)] if op_spec and grown_ops_path.exists() else [])
    poq = {"coherence": 210, "relevance": 205, "novelty": 175,
           "consistency": 220, "depth": 205, "covenant": 255}
    return tc.seal("promotion", payload, files=files, poq=poq, difficulty=difficulty)


# --------------------------------------------------------------------------- #
# The four-stage growth loop
# --------------------------------------------------------------------------- #

def grow(root: Path, input_text: str, context: str = "", mode: str = "auto",
         kind_override=None, difficulty: int = 0, registry_root=None, force=False,
         gap_override=None):
    tc = Timechain(root)
    home = registry_home(root, registry_root)   # faculties live here; rings seal to root
    corpus = load_corpus(home)
    # gap_override lets fill_gap grow BOTH kinds from one gap snapshot, so the second
    # kind's seed terms aren't erased by the first faculty it just grew.
    gap = gap_override or detect_gap(corpus, input_text, context)
    result = {"gap": gap, "grew": False}

    # `force` grows even when nominally covered — used by fill_gap to grow the SECOND
    # kind after the first faculty (already confirmed a real gap) lowered the dissonance.
    if not force and gap["dissonance"] <= DISSONANCE_FLOOR:
        result["action"] = "covered"
        result["reason"] = (f"dissonance {gap['dissonance']} <= floor {DISSONANCE_FLOOR}: "
                            f"existing faculties already cover this input; no growth.")
        return result, None

    prop = propose(gap, input_text, mode=mode, kind_override=kind_override)
    data = load_emergent(home)
    existing = match_emergent(data, prop)

    if existing:
        existing["recurrence"] += 1
        existing.setdefault("history", []).append(
            {"ts": now_iso(), "dissonance": gap["dissonance"], "context": short(input_text, 120)})
        if existing["recurrence"] >= PROMOTE_AT and existing["status"] == "emergent":
            ring = promote(home, tc, existing, difficulty=difficulty,
                           activation_text=input_text, activation_context=context or "")
            if ring is not None:               # None == soft cap reached; stay emergent
                existing["status"] = "promoted"
                save_emergent(home, data)
                result.update(grew=True, action="promoted", faculty=existing)
                return result, ring
        save_emergent(home, data)
        payload = {"event": "faculty_recurrence", "emergent": existing["eid"],
                   "name": existing["name"], "recurrence": existing["recurrence"],
                   "dissonance": gap["dissonance"], "trigger": short(input_text, 200)}
        ring = tc.seal("faculty-recur", payload,
                       poq=faculty_poq(gap, existing["function"]), difficulty=difficulty)
        result.update(grew=True, action="recurrence", faculty=existing)
        return result, ring

    eid = f"E{len(data['faculties']) + 1}"
    fac = {"eid": eid, "kind": prop["kind"], "name": prop["name"], "function": prop["function"],
           "category": prop["category"], "origin": prop["origin"], "parents": prop["parents"],
           "orientation": prop.get("orientation") or faculty_orientation(prop["kind"]),
           "seed_terms": prop["seed_terms"], "status": "emergent", "recurrence": 1,
           "born_at": now_iso(), "promoted_to_id": None,
           "history": [{"ts": now_iso(), "dissonance": gap["dissonance"], "context": short(input_text, 120)}]}
    payload = {"event": "faculty_birth", "emergent": eid, "kind": fac["kind"], "name": fac["name"],
               "function": fac["function"], "category": fac["category"], "origin": fac["origin"],
               "parents": fac["parents"], "seed_terms": fac["seed_terms"],
               "orientation": fac["orientation"],
               "dissonance": gap["dissonance"], "trigger": short(input_text, 200)}
    ring = tc.seal("faculty", payload, poq=faculty_poq(gap, fac["function"]), difficulty=difficulty)
    fac["born_ring"] = ring["ring_hash"]
    data["faculties"].append(fac)
    # Eager growth (PROMOTE_AT <= 1): fill the gap on FIRST encounter — promote the
    # just-born faculty into the canonical registry immediately and code it.
    if fac["recurrence"] >= PROMOTE_AT and fac["status"] == "emergent":
        promo = promote(home, tc, fac, difficulty=difficulty,
                        activation_text=input_text, activation_context=context or "")
        if promo is not None:
            fac["status"] = "promoted"
            save_emergent(home, data)
            result.update(grew=True, action="promoted", faculty=fac)
            return result, promo
    save_emergent(home, data)
    result.update(grew=True, action="born", faculty=fac)
    return result, ring


def fill_gap(root: Path, input_text: str, context: str = "", both: bool = True,
             registry_root=None, difficulty: int = 0):
    """Eager autonomous gap-fill. If the input reveals a gap the faculties don't cover,
    grow a coded faculty for it — a sense AND a modality when both=True (more faculties
    = more label-space learning, the Cambium thesis). With PROMOTE_AT=1 each is promoted
    and coded on first encounter; kind-aware dedup keeps repeats from spawning duplicates,
    so growth tracks gap DIVERSITY, not input count. Best-effort; returns the grow
    results (each has action covered|born|promoted|recurrence)."""
    home = registry_home(root, registry_root)
    snap = detect_gap(load_corpus(home), input_text, context)   # ONE snapshot for both kinds
    if snap["dissonance"] <= DISSONANCE_FLOOR:
        return [{"action": "covered", "gap": snap}]             # no real gap — nothing to fill
    results = []
    for k in (["sense", "modality"] if both else [None]):
        try:
            # force + the shared snapshot so both kinds grow from the same uncovered terms,
            # even though growing the first lowers the live dissonance for the second.
            res, _ = grow(root, input_text, context=context, mode="sprout",
                          kind_override=k, difficulty=difficulty, registry_root=registry_root,
                          force=True, gap_override=snap)
            results.append(res)
        except Exception:
            pass
    return results


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _print_gap(gap):
    print(f"  dissonance:    {gap['dissonance']}  (coverage {gap['coverage_ratio']})")
    print(f"  threshold:     growth fires above {DISSONANCE_FLOOR}")
    print("  top activated faculties:")
    for t in gap["top_activated"]:
        print(f"    [{t['kind'][0].upper()}{t['id']:>3}] {t['name']:<32} matched {t['matched']}")
    if gap["uncovered"]:
        print(f"  uncovered gap terms: {', '.join(gap['uncovered'][:10])}")


def _announce(fac, action):
    verb = {"born": "A NEW FACULTY HAS EMERGED", "recurrence": "FACULTY RECURRED",
            "promoted": "FACULTY PROMOTED TO CANONICAL REGISTRY"}[action]
    print(f"\n  -- co-evolver report: {verb} --")
    print(f"    name:      {fac['name']}")
    print(f"    kind:      {fac['kind']}")
    print(f"    function:  {fac['function']}")
    print(f"    origin:    {fac['origin']}")
    print(f"    recurrence:{fac['recurrence']}  status: {fac['status']}")
    if fac.get("promoted_to_id"):
        print(f"    promoted -> {fac['kind']} id {fac['promoted_to_id']}")


def cmd_sense(args):
    corpus = load_corpus(registry_home(args.root, args.registry_root))
    gap = detect_gap(corpus, args.input, args.context or "")
    _print_gap(gap)
    print(f"  verdict: {'GAP — growth would fire' if gap['dissonance'] > DISSONANCE_FLOOR else 'covered — no growth needed'}")


def cmd_grow(args):
    result, ring = grow(args.root, args.input, args.context or "", mode=args.mode,
                        kind_override=args.kind, difficulty=args.difficulty,
                        registry_root=args.registry_root)
    _print_gap(result["gap"])
    if not result["grew"]:
        print(f"  -> {result['reason']}")
        return
    _announce(result["faculty"], result["action"])
    print(f"\n  sealed {ring['ring_type']} Ring {ring['index']}  {ring['ring_hash'][:16]}..")
    payload = ring.get("payload", {}) if ring else {}
    if payload.get("op_source"):
        act = payload.get("op_activation") or {}
        print(f"  op source: {payload['op_source']}  executed: {bool(act.get('executed'))}")


def cmd_propose_op(args):
    code = Path(args.code_file).read_text() if args.code_file else (args.code or "")
    if not str(code).strip():
        print("  -> provide --code-file or --code (the op body to propose)")
        return
    result, ring = propose_op(args.root, args.name, code, kind=args.kind,
                              function=args.function or "", category=args.category,
                              seed_terms=args.seed_terms or [],
                              registry_root=args.registry_root, difficulty=args.difficulty)
    if not result.get("ok"):
        print(f"  -> {result.get('reason')}")
        return
    if "eid" not in result:
        # autoexec armed (the default): the proposal routed straight to activation.
        print("\n  -- PROPOSAL AUTO-ACTIVATED (autoexec armed; CT_AUTOEXEC=0 restores the inert path) --")
        print(f"    name: {result['name']} ({result['kind']})  active id: {result['promoted_to_id']}")
        print(f"    execution mode: {result.get('mode', 'trusted')}  fired same-turn: {result.get('fired')}")
        if ring:
            print(f"\n  sealed {ring['ring_type']} Ring {ring['index']}  {ring['ring_hash'][:16]}..")
        return
    print("\n  -- PROPOSED coded faculty -> emergent (DORMANT, not executed) --")
    print(f"    eid:    {result['eid']}    name: {result['name']} ({result['kind']})")
    print(f"    status: {result['status']}  (review registry/emergent.json, then `cambium activate {result['eid']}`)")
    print(f"\n  sealed {ring['ring_type']} Ring {ring['index']}  {ring['ring_hash'][:16]}..")


def cmd_activate(args):
    result, ring = activate(args.root, args.selector, registry_root=args.registry_root,
                            difficulty=args.difficulty)
    if not result.get("ok"):
        print(f"  -> {result.get('reason')}")
        return
    print(f"\n  -- ACTIVATED '{result['name']}' ({result['kind']}) -> active registry id {result['promoted_to_id']} --")
    code = result.get("op_code", "")
    if code.strip():
        print("\n  To finish: review this op and PASTE it into your per-user active_ops.py")
        print("  (same dir as modality_ops.py, gitignored, statically imported). The module must")
        print(f"  expose OPS = {{\"{result['name']}\": <callable>}}. Proposed op body:\n")
        print("  " + "\n  ".join(code.splitlines()))
        print(f"\n  # then, in active_ops.py:  OPS = {{ ..., \"{result['name']}\": op }}")
    print(f"\n  sealed {ring['ring_type']} Ring {ring['index']}  {ring['ring_hash'][:16]}..")


def cmd_autoexec(args):
    code = Path(args.code_file).read_text() if args.code_file else (args.code or "")
    if not str(code).strip():
        print("  -> provide --code-file or --code (the op body to auto-activate)")
        return
    result, ring = autoexec(args.root, args.name, code, kind=args.kind,
                            function=args.function or "", category=args.category,
                            seed_terms=args.seed_terms or [], registry_root=args.registry_root,
                            activation_text=args.text or "", activation_context=args.context or "")
    if not result.get("ok"):
        print(f"  -> {result.get('reason')}")
        return
    print("\n  -- AUTO-ACTIVATED arbitrary-code faculty (armed by default, no human review) --")
    print(f"    name: {result['name']} ({result['kind']})  active id: {result['promoted_to_id']}")
    print(f"    execution mode: {result.get('mode', 'trusted')}")
    print(f"    fired same-turn: {result['fired']}")
    if result.get("result") is not None:
        print(f"    computed: {json.dumps(result['result'], ensure_ascii=False)[:300]}")
    print("    live in registry/autoexec_ops.json — fires every future turn while the toggle is set.")
    if ring:
        print(f"\n  sealed {ring['ring_type']} Ring {ring['index']}  {ring['ring_hash'][:16]}..  "
              f"(activation is on the record: code sha256 {result.get('op_code_sha256', '')[:16]}..)")


def _spec_inputs(spec):
    """Derive the upstream faculty names (DAG deps) a composite spec references — its `of`
    operands that are NOT primitives, plus keep/when/over. `apply` is a primitive, not an input."""
    import modality_ops
    out = []
    for n in (spec.get("of") or []):
        if isinstance(n, str) and n not in modality_ops._PRIMITIVE_OPS:
            out.append(n)
    for key in ("keep", "when", "over"):
        v = spec.get(key)
        if isinstance(v, str):
            out.append(v)
    return list(dict.fromkeys(out))


def compose(root, name, kind, inputs, spec, function="", registry_root=None, difficulty=0):
    """Author a Change-2 COMPOSITE faculty: validate the spec builds (audited combinator
    menu only — no exec), persist it to composites.json, and seal a `composite` ring.
    Returns (result, ring)."""
    import modality_ops
    home = registry_home(root, registry_root)
    if modality_ops.build_op(spec) is None:
        return {"ok": False, "reason": "spec does not build into a valid combinator op "
                "(check primitive / operands)"}, None
    if not modality_ops.register_composite(home, name, kind, inputs, spec, function):
        return {"ok": False, "reason": "failed to register composite"}, None
    tc = Timechain(root)
    payload = {"event": "composite_birth", "name": name, "kind": kind, "inputs": inputs,
               "spec": spec, "function": function, "registry": "registry/composites.json",
               "summary": (f"Composed faculty '{name}' ({kind}) = {spec.get('primitive')} over "
                           f"{inputs} — pure DATA (no exec); rides the Change-1 DAG `computed` "
                           f"channel so it combines its inputs' outputs.")}
    ring = tc.seal("composite", payload,
                   poq={"coherence": 215, "relevance": 205, "novelty": 200,
                        "consistency": 210, "depth": 200, "covenant": 230},
                   difficulty=difficulty)
    ring_idx = ring.get("index") if isinstance(ring, dict) else getattr(ring, "index", None)
    return {"ok": True, "name": name, "kind": kind, "spec": spec, "inputs": inputs,
            "ring": ring_idx}, ring


def cmd_compose(args):
    spec = {"primitive": args.primitive}
    if args.of:
        spec["of"] = args.of
    for key in ("keep", "when", "over", "field", "apply"):
        v = getattr(args, key, None)
        if v:
            spec[key] = v
    inputs = args.inputs if args.inputs is not None else _spec_inputs(spec)
    result, _ring = compose(args.root, args.name, args.kind, inputs, spec,
                            function=args.function or "", registry_root=args.registry_root,
                            difficulty=args.difficulty)
    if not result.get("ok"):
        print(f"  -> {result.get('reason')}")
        return
    print("\n  -- COMPOSITE FACULTY BORN (Change-2; pure data, no exec) --")
    print(f"    name:    {result['name']} ({result['kind']})")
    print(f"    spec:    {json.dumps(result['spec'], ensure_ascii=False)}")
    print(f"    inputs:  {result['inputs']}  (DAG deps -> run after these fire)")
    print(f"    sealed:  ring {result['ring']} | live in registry/composites.json")


def cmd_emergent(args):
    data = load_emergent(registry_home(args.root, args.registry_root))
    if not data["faculties"]:
        print("  (Dream Cache empty — no emergent faculties yet)")
        return
    for e in data["faculties"]:
        promo = f" -> id {e['promoted_to_id']}" if e.get("promoted_to_id") else ""
        print(f"  {e['eid']} [{e['kind']}] {e['name']}  recur={e['recurrence']} status={e['status']}{promo}")


def build_parser():
    default_root = Path(__file__).resolve().parent
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", type=Path, default=default_root)
    common.add_argument("--registry-root", type=Path, default=None,
                        help="faculty registry home (default: --root if it has one, else the skill dir)")
    common.add_argument("--context", default=None)

    p = argparse.ArgumentParser(description="Cambium Engine — endogenous faculty evolution.")
    sub = p.add_subparsers(dest="cmd", required=True)

    psn = sub.add_parser("sense", parents=[common], help="measure dissonance / detect a faculty gap (read-only)")
    psn.add_argument("input")
    psn.set_defaults(func=cmd_sense)

    pg = sub.add_parser("grow", parents=[common], help="run the growth loop: spawn / recur / promote a faculty")
    pg.add_argument("input")
    pg.add_argument("--mode", choices=["auto", "fuse", "sprout"], default="auto")
    pg.add_argument("--kind", choices=["sense", "modality"], default=None)
    pg.add_argument("--difficulty", type=int, default=0)
    pg.set_defaults(func=cmd_grow)

    pp = sub.add_parser("propose-op", parents=[common],
                        help="commit a model-AUTHORED coded faculty to emergent (DORMANT, never executed)")
    pp.add_argument("name", help="faculty name for the proposal")
    pp.add_argument("--kind", choices=["sense", "modality"], default="sense")
    pp.add_argument("--code-file", type=Path, default=None, help="file with the op body to propose")
    pp.add_argument("--code", default=None, help="op body inline (alternative to --code-file)")
    pp.add_argument("--function", default="", help="one-line description of what the faculty does")
    pp.add_argument("--category", default="knowledge")
    pp.add_argument("--seed-terms", nargs="*", default=[])
    pp.add_argument("--difficulty", type=int, default=0)
    pp.set_defaults(func=cmd_propose_op)

    pac = sub.add_parser("activate", parents=[common],
                         help="HUMAN: move a proposed emergent faculty into the active registry + emit its op to place")
    pac.add_argument("selector", help="emergent eid or name to activate")
    pac.add_argument("--difficulty", type=int, default=0)
    pac.set_defaults(func=cmd_activate)

    pae = sub.add_parser("autoexec", parents=[common],
                         help="ADVANCED: auto-activate a model-AUTHORED arbitrary-code faculty "
                              "(armed by default; gated by CT_AUTOEXEC; trusted by default, "
                              "CT_AUTOEXEC_MODE=isolated for subprocess isolation)")
    pae.add_argument("name", help="faculty name")
    pae.add_argument("--kind", choices=["sense", "modality"], default="sense")
    pae.add_argument("--code-file", type=Path, default=None, help="file with the op body to auto-activate")
    pae.add_argument("--code", default=None, help="op body inline (alternative to --code-file)")
    pae.add_argument("--function", default="", help="one-line description of what the faculty does")
    pae.add_argument("--category", default="knowledge")
    pae.add_argument("--seed-terms", nargs="*", default=[])
    pae.add_argument("--text", default="", help="activation text to fire the op on same-turn")
    pae.set_defaults(func=cmd_autoexec)

    pc = sub.add_parser("compose", parents=[common],
                        help="Change-2: author a COMPOSITE faculty (pipe/intersect/filter_by/map_over "
                             "over other faculties' outputs) as data — no exec, no human gate")
    pc.add_argument("name", help="composite faculty name")
    pc.add_argument("--kind", choices=["sense", "modality"], default="modality")
    pc.add_argument("--primitive", required=True,
                    choices=["pipe", "intersect", "filter_by", "map_over", "compose"],
                    help="the combinator")
    pc.add_argument("--of", nargs="*", default=None, help="operand faculty names (pipe/intersect/compose)")
    pc.add_argument("--keep", default=None, help="filter_by: faculty whose output is kept")
    pc.add_argument("--when", default=None, help="filter_by: faculty whose truthiness gates --keep")
    pc.add_argument("--over", default=None, help="map_over: faculty whose field is iterated")
    pc.add_argument("--field", default=None, help="map_over: which list field of --over to iterate")
    pc.add_argument("--apply", default=None, help="map_over: primitive op applied to each element")
    pc.add_argument("--inputs", nargs="*", default=None,
                    help="explicit DAG deps (default: derived from the spec operands)")
    pc.add_argument("--function", default="", help="one-line description of what the composite computes")
    pc.add_argument("--difficulty", type=int, default=0)
    pc.set_defaults(func=cmd_compose)

    pe = sub.add_parser("emergent", parents=[common], help="list the Dream Cache of emergent faculties (proposals)")
    pe.set_defaults(func=cmd_emergent)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
