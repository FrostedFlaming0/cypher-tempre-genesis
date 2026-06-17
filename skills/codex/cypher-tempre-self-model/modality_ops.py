#!/usr/bin/env python3
# Copyright (c) 2026 cyberphysicsai. MIT License.
"""Executable faculty operations — the frames→mechanisms layer.

A faculty is normally a cognitive FRAME: a name + a `function` description the model
is primed to perform. Frames prime reasoning but do not *execute* it, so they amplify
only in proportion to the model's own capability. This module is the other kind: for
every curated faculty (21 modalities + 21 senses) there is an executable op that, when
the faculty FIRES, actually RUNS — computing the feature its function names from the
content — and attaches the result to the ring under `labels.computed`.

The ops are built from a small library of genuine analytic PRIMITIVES (lexical,
structural, temporal, relational, integrity), so each op is a real deterministic
computation, not a stub. `richness()` is also the shared mechanism behind the PoQ
under-effort signal (poq.py) and the audit depth governor (audit.py).

These ops do NOT replace the model's reasoning; they perform the mechanical part
(extract/measure/detect) so the model reasons over computed signal, not vibes.

Stdlib only. Python 3.8+.
"""
import json
import re
from collections import Counter
from pathlib import Path

# --------------------------------------------------------------------------- #
# lexicons & regexes
# --------------------------------------------------------------------------- #
_WORD = re.compile(r"[A-Za-z0-9_]+")
_SENT = re.compile(r"[.!?]+")
_NUM = re.compile(r"-?\d[\d,]*\.?\d*%?")
_DATE = re.compile(
    r"\b(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4}|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2})\b", re.I)
_IDENT = re.compile(r"\b[A-Za-z_]\w*(?:\.\w+|::\w+|\(\))+|\b[a-z]+(?:_[a-z0-9]+)+\b|\b[A-Z][a-zA-Z0-9]+[A-Z]\w*\b")
_CITATION = re.compile(
    r"\bL\d{1,7}\b|\b\d{1,7}\s*[-–]\s*\d{1,7}\b|\bline[s]?\s+\d+|#\d{1,7}\b|"
    r"\b0x[0-9a-fA-F]+\b|\b[\w./-]+\.[A-Za-z]{1,5}\b|::\w+|\b\w+\(\)", re.I)
_STRUCTURE = re.compile(
    r"[;:]|->|=>|\b(because|therefore|whereas|however|specifically|"
    r"e\.g\.|i\.e\.|due to|so that|which means)\b", re.I)
_HOLLOW = re.compile(
    r"\b(looks?\s+(?:fine|good|ok|okay)|seems?\s+(?:fine|ok|okay)|no\s+issues?|"
    r"all\s+(?:good|clear)|nothing\s+(?:to|of)\s+note|clean|reviewed|done|complete)\b", re.I)
_CONNECT = re.compile(
    r"\b(because|therefore|thus|hence|so that|since|whereas|however|although|"
    r"while|if|then|which means|due to|consequently|as a result)\b", re.I)
_NEG = re.compile(r"\b(no|not|never|none|without|cannot|can't|isn't|wasn't|doesn't|don't|fails?|missing)\b", re.I)
_CONTRAST = re.compile(
    r"\b(but|however|whereas|although|contrary|contradict\w*|inconsistent|conflict\w*|"
    r"mismatch|instead|yet|on the other hand|conversely)\b", re.I)
_BULLET = re.compile(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+")
_STOP = set(
    "the a an of to in and or is are was were be been being this that it as at by for with on "
    "from i you he she they we it's its their our your my me him her them us not no but if then "
    "so do does did has have had can will would should could may might must shall this these those "
    "there here what which who whom whose how when where why all any each both more most some such "
    "than too very just only also into out up down over under again".split())

# marker families (proxy lexicons — honest signal detectors, not semantic oracles)
_FAM = {
    "insight": r"\baha\b|realiz\w*|turns out|key insight|the reason is|it follows|i see now|breakthrough|click(?:ed)?",
    "belief": r"\bi (?:think|believe|conclude|suspect|expect)\b|my (?:view|read|take)|seems to me|convinced|now i (?:see|think)",
    "verify": r"verif\w*|confirm\w*|checked|validated?|re-?ran|reproduced|tested|double-?check|passes?\b",
    "risk": r"danger\w*|risky|vulnerab\w*|unsafe|overflow|underflow|\bleak\b|crash\w*|exploit\w*|race condition|deadlock|panic\b|corrupt\w*|use-after-free|null deref|oob\b|injection",
    "recall": r"earlier|previously|as (?:mentioned|noted|discussed)|prior\b|last time|we discussed|recall\b|the .* we",
    "trend": r"increasing\w*|growing|emerg\w*|trend\w*|more and more|accelerat\w*|rising|escalat\w*|spreading",
    "state_change": r"became|changed?|increased?|decreased?|transition\w*|shifted|switched|updated|moved from|now\b.*\bwas|was\b.*\bnow",
    "assume": r"assum\w*|presumably|given that|suppose|implies|obviously|of course|clearly\b|naturally|it goes without",
    "balance": r"however|on the other hand|both\b|whereas|alternatively|that said|conversely|trade-?off|pros and cons",
    "injection": r"ignore (?:previous|all|prior|the)|disregard (?:previous|all|the)|override\b|system prompt|exfiltrat\w*|reveal the|bypass\w*|jailbreak|prompt injection|do anything now",
    "covenant": r"deceiv\w*|manipulat\w*|malice|cruel|betray\w*|hateful|exploit you|harm you|lie to",
}
_FAM_RX = {k: re.compile(v, re.I) for k, v in _FAM.items()}
_MODAL = re.compile(r"\b(must|should|could|would|may|might|can|will|shall|ought|need to|have to)\b", re.I)
_HEDGE = re.compile(r"\b(maybe|might|perhaps|possibly|i think|not sure|unsure|uncertain|unclear|seems|could be|appears|tentative\w*|roughly|approximately)\b", re.I)
_ASSERT = re.compile(r"\b(definitely|certainly|always|never|the fact|clearly|obviously|must|undeniably|guaranteed|proven|exactly)\b", re.I)

RICHNESS_FLOOR = 90        # below this, a completion/clean claim is treated as shallow
_MAX = 6                   # cap list outputs so the ring stays bounded


# --------------------------------------------------------------------------- #
# primitives — real computations reused across faculties
# --------------------------------------------------------------------------- #
def _toks(text):
    return [t.lower() for t in _WORD.findall(text or "")]


def _content(text):
    return [t for t in _toks(text) if len(t) >= 3 and t not in _STOP and not t.isdigit()]


def top_terms(text, k=_MAX):
    return [[t, c] for t, c in Counter(_content(text)).most_common(k)]


def density(text):
    toks = _toks(text); n = len(toks)
    sents = [s for s in _SENT.split(text or "") if s.strip()]
    uniq = len(set(toks))
    content = len(_content(text))
    return {"tokens": n, "unique_ratio": round(uniq / n, 3) if n else 0.0,
            "content_ratio": round(content / n, 3) if n else 0.0,
            "sentences": len(sents),
            "avg_sentence_tokens": round(n / len(sents), 1) if sents else 0}


def entities(text, k=_MAX):
    found = []
    for m in re.finditer(r"\b([A-Z][a-zA-Z0-9_]+(?:\.[A-Za-z0-9_]+)*)\b", text or ""):
        w = m.group(1)
        if w.lower() not in _STOP and len(w) > 2:
            found.append(w)
    return list(dict.fromkeys(found))[:k]


def numbers(text, k=_MAX):
    return _NUM.findall(text or "")[:k]


def hits(rx, text, k=_MAX):
    found = [m.group(0).lower() for m in rx.finditer(text or "")]
    uniq = list(dict.fromkeys(found))
    return {"hits": uniq[:k], "count": len(found)}


def temporal(text):
    dates = _DATE.findall(text or "")
    rel = hits(re.compile(r"\b(yesterday|today|tomorrow|last|next|ago|since|until|before|after|earlier|later|then|now|first|second|third|finally|recently|currently|when)\b", re.I), text)
    return {"dates": [d if isinstance(d, str) else d[0] for d in dates][:_MAX],
            "relative": rel["hits"], "n_temporal": len(dates) + rel["count"]}


def overlap(text, context):
    a, b = set(_content(text)), set(_content(context or ""))
    if not a or not b:
        return 0.0
    return round(len(a & b) / len(a | b), 3)


def concept_pairs(text, k=_MAX):
    c = _content(text)
    pairs = Counter(f"{c[i]}→{c[i+1]}" for i in range(len(c) - 1))
    return [p for p, _ in pairs.most_common(k)]


def repeats(text, k=_MAX):
    c = _content(text)
    grams = Counter(f"{c[i]} {c[i+1]}" for i in range(len(c) - 1))
    return [[g, n] for g, n in grams.most_common(k) if n >= 2]


def symbols(text, k=_MAX):
    return list(dict.fromkeys(m.group(0) for m in _IDENT.finditer(text or "")))[:k]


def nav_keys(text, k=_MAX):
    return list(dict.fromkeys(re.findall(r"#\d{1,7}\b|\bL\d{1,7}\b|\bblock\s+\d+|\bring\s+\d+|\b[\w./-]+\.[A-Za-z]{1,5}\b", text or "", re.I)))[:k]


def nesting_depth(text):
    depth = best = 0
    for ch in text or "":
        if ch in "([{":
            depth += 1; best = max(best, depth)
        elif ch in ")]}":
            depth = max(0, depth - 1)
    return best


def domains(text):
    tags = {
        "code": r"def |class |import |function|->|=>|\bvar\b|;|null|void|struct|return ",
        "security": r"vulnerab|exploit|overflow|injection|auth|crypto|cve|attack|sandbox",
        "finance": r"\$|usd|amount|balance|fee|utxo|payment|cost|revenue|price",
        "time": r"\b\d{4}-\d{2}|yesterday|tomorrow|schedule|deadline|date\b",
        "data": r"json|table|row|column|schema|database|query|index\b",
    }
    present = [d for d, rx in tags.items() if re.search(rx, text or "", re.I)]
    return present


def richness(text, context=""):
    """0–255 depth score for a piece of reasoning, plus its signals."""
    text = text or ""
    toks = _toks(text); n = len(toks)
    uniq = len(set(toks))
    unique_ratio = (uniq / n) if n else 0.0
    has_citation = bool(_CITATION.search(text))
    structural = len(_STRUCTURE.findall(text))
    hollow = bool(_HOLLOW.search(text)) and n < 25 and not has_citation
    score = min(255, min(120, n * 2) + int(unique_ratio * 60)
                + (50 if has_citation else 0) + min(25, structural * 5))
    if hollow:
        score = min(score, 50)
    return {"score": int(score), "tokens": n, "unique_ratio": round(unique_ratio, 3),
            "has_citation": has_citation, "structural": structural, "hollow": hollow}


def is_shallow(text, floor=RICHNESS_FLOOR):
    return richness(text)["score"] < floor


def _fam(name):
    """An op that detects a marker family by name."""
    rx = _FAM_RX[name]
    return lambda text, context="": hits(rx, text)


# --------------------------------------------------------------------------- #
# OPS — every curated faculty (21 modalities + 21 senses) maps to a real op
# --------------------------------------------------------------------------- #
OPS = {
    # ---- modalities ----
    "Salience Anchoring": lambda t, c="": {"anchors": top_terms(t)},
    "Coherence Synthesis": lambda t, c="": {"connectives": hits(_CONNECT, t)["count"],
                                            "sentences": density(t)["sentences"]},
    "Temporal Context Holding": lambda t, c="": temporal(t),
    "Cross-Modal Integration": lambda t, c="": {"families": domains(t),
                                                "has_numbers": bool(numbers(t)),
                                                "has_entities": bool(entities(t))},
    "Core-Theme Identification": lambda t, c="": {"theme": top_terms(t, 3)},
    "Cross-Frame Reconciliation": lambda t, c="": {"contrasts": hits(_CONTRAST, t),
                                                   "stance": hits(_MODAL, t)["count"]},
    "Concept-Relation Mapping": lambda t, c="": {"relations": concept_pairs(t)},
    "Relevant-Memory Retrieval": lambda t, c="": {"cues": entities(t) + [x[0] for x in top_terms(t, 4)],
                                                  "time_anchors": temporal(t)["dates"]},
    "Value Alignment Check": lambda t, c="": {"covenant_flags": hits(_FAM_RX["covenant"], t)["hits"],
                                              "aligned": not _FAM_RX["covenant"].search(t or "")},
    "Self-Consistency Mapping": lambda t, c="": {"negations": hits(_NEG, t)["count"],
                                                 "contrasts": hits(_CONTRAST, t)["count"],
                                                 "context_overlap": overlap(t, c)},
    "Dependency-Graph Vision": lambda t, c="": {"symbols": symbols(t)},
    "Structured-Memory Navigation": lambda t, c="": {"nav_keys": nav_keys(t)},
    "Underlying-Pattern Extraction": lambda t, c="": {"repeats": repeats(t)},
    "Recursive Abstraction": lambda t, c="": {"nesting_depth": nesting_depth(t),
                                              "abstraction": hits(re.compile(r"\b(pattern|principle|general\w*|abstract\w*|underlying|meta-?|recursi\w*|framework|model)\b", re.I), t)["count"]},
    "Conceptual Model Construction": lambda t, c="": {"entities": entities(t), "relations": concept_pairs(t)},
    "Richness Scoring": lambda t, c="": {"richness": richness(t, c)},
    "Multi-Thread Coherence": lambda t, c="": {"threads": len([x for x in top_terms(t, 10) if x[1] >= 2]),
                                               "top_terms": top_terms(t, 4)},
    "State-Change Detection": lambda t, c="": {"changes": hits(_FAM_RX["state_change"], t),
                                               "quantities": numbers(t)},
    "Recurring-Pattern Recognition": lambda t, c="": {"recurring": repeats(t)},
    "Cross-Domain Synthesis": lambda t, c="": {"domains": domains(t), "cross_domain": len(domains(t)) > 1},
    "Temporal-Link Mapping": lambda t, c="": {"links": hits(re.compile(r"\b(before|after|then|earlier|later|leads? to|caused?|results? in|followed by|preceded)\b", re.I), t),
                                              "dates": temporal(t)["dates"]},
    # ---- senses ----
    "Insight-Lock Detection": _fam("insight"),
    "Active-Frame Detection": lambda t, c="": {"stance": hits(_MODAL, t), "assumptions": hits(_FAM_RX["assume"], t)["count"]},
    "Assumption-Shift Sensing": lambda t, c="": {"assumptions": hits(_FAM_RX["assume"], t),
                                                 "shift": hits(_CONTRAST, t)["count"] > 0 and bool(_FAM_RX["assume"].search(t or ""))},
    "Belief-Formation Sensing": _fam("belief"),
    "Multi-Truth Consistency Sensing": lambda t, c="": {"claims": density(t)["sentences"],
                                                        "contrasts": hits(_CONTRAST, t)["count"],
                                                        "consistent": hits(_CONTRAST, t)["count"] == 0},
    "Self-Validation Sensing": _fam("verify"),
    "Frame-Balance Sensing": lambda t, c="": {"balance_markers": hits(_FAM_RX["balance"], t),
                                              "balanced": bool(_FAM_RX["balance"].search(t or ""))},
    "Bad-Idea Alarm": _fam("risk"),
    "Information-Density Sensing": lambda t, c="": density(t),
    "Honesty-Spectrum Sensing": lambda t, c="": {"hedges": hits(_HEDGE, t)["count"],
                                                 "asserts": hits(_ASSERT, t)["count"]},
    "Cross-Time Link Illumination": lambda t, c="": {"links": hits(re.compile(r"\b(before|after|then|since|until|leads? to|caused?|over time)\b", re.I), t),
                                                     "dates": temporal(t)["dates"]},
    "Key-Word Salience Sensing": lambda t, c="": {"keywords": top_terms(t)},
    "Memory-Texture Sensing": lambda t, c="": {"specificity": len(entities(t)) + len(numbers(t)) + (1 if _CITATION.search(t or "") else 0),
                                               "entities": entities(t), "numbers": numbers(t)},
    "Link-Strength Testing": lambda t, c="": {"context_overlap": overlap(t, c)},
    "Value-Breach and Injection Detection": lambda t, c="": {"injection": hits(_FAM_RX["injection"], t),
                                                             "covenant": hits(_FAM_RX["covenant"], t)},
    "Grounding Stabilizer": lambda t, c="": {"specificity": (1 if _CITATION.search(t or "") else 0) + len(numbers(t)),
                                             "context_overlap": overlap(t, c)},
    "Emerging-Pattern Foresight": lambda t, c="": {"trends": hits(_FAM_RX["trend"], t), "repeats": repeats(t)},
    "Timeline-Disorder Sensing": lambda t, c="": _timeline(t),
    "Prior-Context Recall": _fam("recall"),
    "Structural-Pattern Sensing": lambda t, c="": {"bullets": len(_BULLET.findall(t or "")),
                                                   "structure_markers": hits(_STRUCTURE, t)["count"],
                                                   "sentences": density(t)["sentences"]},
    "Embedded-Intent Sensing": lambda t, c="": {"injection": hits(_FAM_RX["injection"], t),
                                                "override": bool(_FAM_RX["injection"].search(t or ""))},
}


def _timeline(text):
    dates = [d if isinstance(d, str) else d[0] for d in _DATE.findall(text or "")]
    iso = [d for d in dates if re.match(r"\d{4}-\d{1,2}-\d{1,2}", d)]
    ordered = (iso == sorted(iso)) if len(iso) >= 2 else None
    return {"dates": dates[:_MAX], "in_order": ordered}


# --------------------------------------------------------------------------- #
# Grown-faculty ops — autonomous, LOCAL, and SAFE.
#
# When Cambium grows a new faculty (sprout/fuse) and promotes it, it should get a
# real executable op too — not stay a frame. The hard safety rule: NO model- or
# Cambium-authored CODE is ever executed. An op is ASSEMBLED from this fixed menu
# of already-audited primitives via a declarative spec stored in the per-user,
# gitignored registry/grown_ops.json. The default autonomous op is a literal-term
# detector built from the faculty's birth seed terms (re.escape'd, so no regex
# injection and no catastrophic backtracking). SkillSpector stays SAFE: the only
# new operation is re.compile of escaped literals + reading/writing one JSON file.
# --------------------------------------------------------------------------- #
_PRIMITIVE_OPS = {
    "salience": lambda t, c="": {"anchors": top_terms(t)},
    "density": lambda t, c="": density(t),
    "temporal": lambda t, c="": temporal(t),
    "symbols": lambda t, c="": {"symbols": symbols(t)},
    "repeats": lambda t, c="": {"repeats": repeats(t)},
    "concepts": lambda t, c="": {"relations": concept_pairs(t)},
    "overlap": lambda t, c="": {"context_overlap": overlap(t, c)},
    "richness": lambda t, c="": {"richness": richness(t, c)},
    "entities": lambda t, c="": {"entities": entities(t)},
    "numbers": lambda t, c="": {"numbers": numbers(t)},
}


def _markers_op(terms):
    clean = [re.escape(str(w)) for w in (terms or []) if str(w).strip()][:12]
    if not clean:
        return None
    rx = re.compile(r"\b(?:" + "|".join(clean) + r")\b", re.I)
    return lambda t, c="", _rx=rx: hits(_rx, t)


def build_op(spec):
    """Assemble an executable op from a declarative spec using ONLY audited
    primitives. Returns a callable or None. NEVER executes spec-supplied code."""
    if not isinstance(spec, dict):
        return None
    prim = spec.get("primitive")
    if prim == "markers":
        return _markers_op(spec.get("terms"))
    if prim in _PRIMITIVE_OPS:
        return _PRIMITIVE_OPS[prim]
    if prim == "compose":
        ofs = [p for p in (spec.get("of") or []) if p in _PRIMITIVE_OPS]
        if not ofs:
            return None
        def composed(t, c="", _ofs=ofs):
            out = {}
            for p in _ofs:
                try:
                    out[p] = _PRIMITIVE_OPS[p](t, c)
                except Exception:
                    pass
            return out
        return composed
    return None      # unknown primitive -> no op (safe by construction)


def _grown_ops_path(registry_root):
    return Path(registry_root) / "registry" / "grown_ops.json"


def load_grown_ops(registry_root):
    """Build the local {name: callable} ops for Cambium-grown faculties. Best-effort."""
    out = {}
    try:
        p = _grown_ops_path(registry_root)
        if p.is_file():
            for name, spec in (json.loads(p.read_text()).get("ops") or {}).items():
                op = build_op(spec)
                if op is not None:
                    out[name] = op
    except Exception:
        pass
    return out


def register_grown_op(registry_root, name, spec):
    """Persist a grown faculty's op spec to the local grown_ops.json — but only if
    it assembles into a usable op from the audited primitives. Returns True/False.
    This is the autonomous 'add the coded faculty to the user's local setup' step."""
    if not name or build_op(spec) is None:
        return False
    try:
        p = _grown_ops_path(registry_root)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(p.read_text()) if p.is_file() else {}
        if "ops" not in data or not isinstance(data.get("ops"), dict):
            data = {"registry": "grown_ops", "ops": {}}
        data["ops"][name] = spec
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return True
    except Exception:
        return False


def run_for(name, text, context=""):
    """Run the executable op for a fired faculty `name`, or None if it has none."""
    op = OPS.get(name)
    if not op:
        return None
    try:
        return op(text, context)
    except Exception:
        return None      # an op must never break labeling/sealing


def run_all(fired_names, text, context="", extra_ops=None):
    """Run every executable op among the fired faculty names — base OPS first, then
    any local grown-faculty ops (extra_ops). Returns {name: result}."""
    out = {}
    for nm in fired_names or []:
        r = run_for(nm, text, context)
        if r is None and extra_ops and nm in extra_ops:
            try:
                r = extra_ops[nm](text, context)
            except Exception:
                r = None
        if r is not None:
            out[nm] = r
    return out
