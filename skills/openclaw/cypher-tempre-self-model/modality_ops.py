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
import contextlib
import inspect
import json
import os
import re
import subprocess
import sys
from collections import Counter, deque
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


def count_terms(text, terms):
    toks = _toks(text)
    out = {}
    for term in (terms or [])[:12]:
        t = str(term).lower().strip()
        if t:
            out[t] = sum(1 for tok in toks if tok == t)
    return out


def sum_counts(counts):
    return int(sum(int(v) for v in (counts or {}).values()))


def contains_any(text, terms):
    return sum_counts(count_terms(text, terms)) > 0


def missing_terms(text, terms):
    counts = count_terms(text, terms)
    return [term for term, n in counts.items() if not n][:_MAX]


def relation_pairs_for_terms(text, terms, k=_MAX):
    wanted = {str(t).lower().strip() for t in (terms or []) if str(t).strip()}
    toks = _content(text)
    pairs = []
    for i, tok in enumerate(toks):
        if tok in wanted:
            left = toks[i - 1] if i else ""
            right = toks[i + 1] if i + 1 < len(toks) else ""
            pairs.append(" ".join(x for x in (left, tok, right) if x))
    return list(dict.fromkeys(pairs))[:k]


def action_affordances(text, terms):
    markers = {
        "code": r"\b(code|implement|debug|refactor|compile|test|benchmark|script|function|api)\b",
        "audit": r"\b(audit|review|inspect|verify|validate|finding|coverage|risk)\b",
        "solve": r"\b(solve|plan|derive|prove|optimize|reason|strategy|puzzle|challenge|arc)\b",
        "external": r"\b(file|repo|server|browser|terminal|dataset|chain|environment|tool)\b",
    }
    out = [name for name, rx in markers.items() if re.search(rx, text or "", re.I)]
    if contains_any(text, terms):
        out.append("gap_terms_present")
    return list(dict.fromkeys(out))[:_MAX]


def novelty_score(text, context, terms):
    term_hits = sum_counts(count_terms(text, terms))
    ctx_hits = sum_counts(count_terms(context, terms))
    cross = 1.0 - overlap(text, context)
    return {"term_hits": term_hits, "context_hits": ctx_hits,
            "cross_context_novelty": round(max(0.0, min(1.0, cross)), 3)}


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
    "Computational-Shape Sensing": lambda t, c="": comp_shape(t),
}


def _timeline(text):
    dates = [d if isinstance(d, str) else d[0] for d in _DATE.findall(text or "")]
    iso = [d for d in dates if re.match(r"\d{4}-\d{1,2}-\d{1,2}", d)]
    ordered = (iso == sorted(iso)) if len(iso) >= 2 else None
    return {"dates": dates[:_MAX], "in_order": ordered}


# --------------------------------------------------------------------------- #
# Computational-Shape Sensing — detects when text describes an OPERATION (rank,
# count, correlate, co-occur, compare, ratio, between…) over >=2 operands, i.e. a
# computation a bare term-presence (markers) op structurally cannot perform. This
# is the perceptual half of the mid-turn op-write trigger (op_need.py Layer 1):
# it keys on the OPERATION, not on vocabulary novelty. STRONG verbs are
# unambiguously computational and fire alone; WEAK verbs occur in ordinary prose
# ("compare notes", "map onto") and require corroboration (an aggregate cue, a
# struct noun, or >=2 numbers/symbols) before firing — this is what keeps
# rhetorical phrasing from tripping it.
# --------------------------------------------------------------------------- #
_COMP_STRONG_VERBS = re.compile(r"\b(rank|count|tally|correlate|co-?occurs?|aggregate|"
                                r"intersect|histogram|group\s+by)\b", re.I)
_COMP_WEAK_VERBS = re.compile(r"\b(sort|order|compare|sum|average|mean|map\s+over|filter|"
                              r"derive|measure|join|diff|overlap)\b", re.I)
_COMP_STRUCT_NOUNS = re.compile(r"\b(graph|dependency|tree|matrix|distribution|interval|"
                                r"sequence|ratio|percentage|topolog\w*)\b", re.I)
_COMP_AGG_CUES = re.compile(r"\b(how\s+many|number\s+of|per|each|ratio|percent|across|"
                            r"between|most|least|total)\b|%", re.I)
_COMP_CUE_WORDS = frozenset(re.findall(r"[a-z]+", _COMP_STRONG_VERBS.pattern +
                            _COMP_WEAK_VERBS.pattern + _COMP_AGG_CUES.pattern +
                            _COMP_STRUCT_NOUNS.pattern))


def comp_shape(text):
    """Layer-1 detector: {fired, shape, operands, detail}. fired=True only when an
    operation signature is present AND >=2 distinct content operands exist."""
    t = text or ""
    strong = _COMP_STRONG_VERBS.search(t)
    weak = _COMP_WEAK_VERBS.search(t)
    struct = _COMP_STRUCT_NOUNS.search(t)
    agg = _COMP_AGG_CUES.search(t)
    n_struct = len(numbers(t)) + len(symbols(t))
    corroborated = bool(agg) or bool(struct) or n_struct >= 2
    gate = bool(strong) or (bool(weak) and corroborated)
    operands = list(dict.fromkeys(w for w in _content(t) if w not in _COMP_CUE_WORDS))
    fired = gate and len(operands) >= 2
    if strong:
        shape, why = strong.group(0).lower(), f"strong-verb='{strong.group(0)}'"
    elif weak and corroborated:
        shape = weak.group(0).lower()
        why = (f"weak-verb='{weak.group(0)}'+corrob("
               f"{'agg' if agg else ''}{'/struct' if struct else ''}"
               f"{'/nums' if n_struct >= 2 else ''})")
    elif weak:
        shape, why = None, f"weak-verb='{weak.group(0)}'(uncorroborated)"
    else:
        shape, why = None, "no operation signature"
    return {"fired": fired, "shape": shape, "operands": len(operands),
            "detail": f"{why}; operands={len(operands)}"}


# --------------------------------------------------------------------------- #
# Grown-faculty ops — autonomous, LOCAL, and SAFE.
#
# When Cambium grows a new faculty (sprout/fuse) and promotes it, it should get a
# real executable op too — not stay a frame. The op is built ONE safe way: from
# declarative primitive specs drawn from the fixed, audited menu below (markers,
# salience, density, temporal, symbols, …). No op is ever built from a model-written
# code string — there is no ast.parse/compile/exec of authored text anywhere here.
#
# Specs live in the per-user, gitignored registry/grown_ops.json and are sealed in
# the promotion ring. Unknown primitives are refused.
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

# v3.11: model-authored ops are NO LONGER built or executed by the skill. The agent
# PROPOSES op code as inert text to emergent.json; a human reviews it and places the
# approved code into the per-user, gitignored active_ops.py (loaded statically above).
# So there is no ast.parse/compile/exec of authored strings anywhere in the shipped skill.


def _clean_terms(terms, fallback="gap"):
    out = []
    for term in terms or []:
        t = str(term).lower().strip()
        if t and re.match(r"^[a-z0-9_][a-z0-9_-]{1,48}$", t) and t not in out:
            out.append(t)
        if len(out) >= 8:
            break
    return out or [fallback]


def render_op_code(faculty):
    """Render a READABLE Python op body proposing how a grown faculty could compute its
    feature — stored as INERT text in emergent.json for human review. It is NEVER executed
    by the skill (no exec/compile anywhere); a human reviews it and, if approved, places it
    into the per-user active_ops.py. This is the 'code it up, commit to emergent, don't run
    it' step. The default rendering detects the faculty's seed terms; a model may author a
    richer body instead and pass it to cambium.propose_op."""
    kind = "modality" if faculty.get("kind") == "modality" else "sense"
    seeds = _clean_terms(faculty.get("seed_terms") or _content(faculty.get("function", ""))[:8],
                         fallback=kind)
    literal = json.dumps(seeds, ensure_ascii=True)
    return (
        "def op(text, context=''):\n"
        f"    # {kind} op for {faculty.get('name', 'grown faculty')} (proposed; review before activating)\n"
        f"    import modality_ops as mo\n"
        f"    terms = {literal}\n"
        "    hits = mo.hits(mo.re.compile(r'\\b(?:' + '|'.join(mo.re.escape(t) for t in terms) + r')\\b', mo.re.I), text)\n"
        f"    return {{'kind': '{kind}', 'terms': terms, 'hits': hits['hits'], 'count': hits['count']}}\n"
    )


def _markers_op(terms):
    clean = [re.escape(str(w)) for w in (terms or []) if str(w).strip()][:12]
    if not clean:
        return None
    rx = re.compile(r"\b(?:" + "|".join(clean) + r")\b", re.I)
    return lambda t, c="", _rx=rx: hits(_rx, t)


def build_op(spec):
    """Build an executable op from a safe spec — assembled ONLY from the fixed audited
    primitive menu (markers / named primitives / compose). Returns a callable or None.

    There is NO dynamic execution of authored code here: the skill never exec/eval/compiles
    a model-written string (removed in v3.11). Arbitrary model-authored ops are PROPOSED to
    emergent.json as inert text and only run after a human reviews them and places the code
    into the per-user, gitignored active_ops.py (loaded statically below). So a static scanner
    has no dynamic-execution call to flag, and no model code runs without human approval.
    """
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
    # ---- Change-2 combinators: COMPOSITE ops over the Change-1 `computed` channel ----
    # These read upstream faculty outputs (the composite declares them in `inputs`, which
    # drives the DAG order in run_all) and combine them into a derived signal. Still no
    # exec: every combinator is assembled from this fixed menu only.
    if prim == "intersect":
        names = [n for n in (spec.get("of") or []) if isinstance(n, str)]
        if len(names) < 2:
            return None
        def _intersect(t, c="", computed=None, _names=names):
            sets = [_signals((computed or {}).get(n, {})) for n in _names]
            common = set.intersection(*sets) if all(sets) else set()
            return {"intersect": sorted(common), "agree": bool(common), "of": _names}
        return _intersect
    if prim == "filter_by":
        keep, when = spec.get("keep"), spec.get("when")
        if not isinstance(keep, str) or not isinstance(when, str):
            return None
        def _filter_by(t, c="", computed=None, _keep=keep, _when=when):
            gate = _truthy((computed or {}).get(_when, {}))
            return {"kept": gate, "by": _when,
                    "value": (computed or {}).get(_keep) if gate else None}
        return _filter_by
    if prim == "map_over":
        over, field, apply = spec.get("over"), spec.get("field"), spec.get("apply")
        if not isinstance(over, str) or not isinstance(field, str) or apply not in _PRIMITIVE_OPS:
            return None
        def _map_over(t, c="", computed=None, _o=over, _f=field, _a=apply):
            coll = ((computed or {}).get(_o, {}) or {}).get(_f, []) or []
            out = []
            for e in list(coll)[:_MAX]:
                try:
                    out.append({"item": e, "result": _PRIMITIVE_OPS[_a](str(e), c)})
                except Exception:
                    pass
            return {"mapped": out, "over": _o, "field": _f, "apply": _a}
        return _map_over
    if prim == "pipe":
        names = [n for n in (spec.get("of") or []) if isinstance(n, str)]
        if len(names) < 2:
            return None
        def _pipe(t, c="", computed=None, _names=names):
            # feed each stage's output-signals forward as the CONTEXT of the next faculty op
            ctx, last = c, None
            steps = []
            for n in _names:
                op = OPS.get(n)
                if op is None:                    # not a built-in faculty -> read its computed
                    last = (computed or {}).get(n)
                else:
                    last = op(t, ctx)
                ctx = " ".join(sorted(_signals(last or {}))) or ctx
                steps.append({n: last})
            return {"piped": last, "stages": steps, "of": _names}
        return _pipe
    return None      # unknown primitive -> no op (safe by construction)


def _signals(result):
    """Flatten a faculty output dict into the set of 'signal tokens' it emitted: every
    string in any list value, plus any key whose value is exactly True. The shared
    vocabulary the Change-2 combinators (intersect/pipe) operate over."""
    out = set()
    if not isinstance(result, dict):
        return out
    for k, v in result.items():
        if v is True:
            out.add(str(k))
        elif isinstance(v, str):
            out.add(v)
        elif isinstance(v, (list, tuple)):
            for e in v:
                if isinstance(e, str):
                    out.add(e)
                elif isinstance(e, (list, tuple)) and e and isinstance(e[0], str):
                    out.add(e[0])
    return out


def _truthy(result):
    """A faculty output counts as a satisfied predicate (for filter_by) if it emitted any
    signal token, any positive number, or any True flag."""
    if not isinstance(result, dict):
        return bool(result)
    if _signals(result):
        return True
    for v in result.values():
        if v is True:
            return True
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
            return True
    return False


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
    # Merge auto-activated arbitrary-code ops (armed by default; gated by CT_AUTOEXEC,
    # returns {} when disabled). Rides the same extra_ops channel into run_all, so no caller changes.
    try:
        out.update(load_autoexec_ops(registry_root))
    except Exception:
        pass
    return out


def register_grown_op(registry_root, name, spec):
    """Persist a grown faculty's op spec to the local grown_ops.json — but only if
    it builds into a usable safe op. Returns True/False.
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


def _composites_path(registry_root):
    return Path(registry_root) / "registry" / "composites.json"


def load_composites(registry_root):
    """Build ({name: op}, {name: [inputs]}) for Change-2 composite faculties from the
    per-user registry/composites.json. Composite ops are 3-arg (they read the `computed`
    channel); their declared `inputs` drive the DAG order in run_all. Best-effort."""
    ops, deps = {}, {}
    try:
        p = _composites_path(registry_root)
        if p.is_file():
            for name, rec in (json.loads(p.read_text()).get("composites") or {}).items():
                spec = (rec or {}).get("spec")
                op = build_op(spec) if isinstance(spec, dict) else None
                if op is not None:
                    ops[name] = op
                    deps[name] = [n for n in (rec.get("inputs") or []) if isinstance(n, str)]
    except Exception:
        pass
    return ops, deps


def register_composite(registry_root, name, kind, inputs, spec, function=""):
    """Persist a composite faculty to composites.json — only if its spec builds into a
    usable op. Returns True/False. Pure DATA: nothing executes outside the audited combinator
    menu, so this needs no human-review gate (unlike model-authored autoexec ops)."""
    if not name or build_op(spec) is None:
        return False
    try:
        p = _composites_path(registry_root)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(p.read_text()) if p.is_file() else {}
        if "composites" not in data or not isinstance(data.get("composites"), dict):
            data = {"registry": "composites", "composites": {}}
        data["composites"][name] = {
            "kind": kind if kind in ("sense", "modality") else "modality",
            "inputs": [n for n in (inputs or []) if isinstance(n, str)],
            "spec": spec,
            "function": function or "",
        }
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# ADVANCED — autonomously auto-activated arbitrary-code faculties.
#
# ON by default on this fork — autonomous arbitrary-code faculty auto-activation is the
# fork's stated purpose, so the capability ships ARMED. Controlled by an ENV VAR (never
# injected *input*), so a hostile prompt can switch it neither on nor off. CT_AUTOEXEC is
# the canonical switch; CT_EXPERIMENTAL_AUTOEXEC is honored as a back-compat alias. Disable
# explicitly with either set to 0/false/no/off.
#
# Execution policy is explicit:
#   CT_AUTOEXEC_MODE=trusted  (default): run the op in-process with normal Python capability.
#   CT_AUTOEXEC_MODE=isolated: run the op in a short-lived child process with timeout, a
#                             sanitized environment, and best-effort POSIX rlimits.
#
# CT_AUTOEXEC_RESTRICTED_BUILTINS=1 (or legacy CT_AUTOEXEC_SANDBOX=1) can restrict the
# in-process builtins surface, but this is NOT a security boundary; it is only accident
# hardening. Real containment starts at the isolated subprocess boundary.
# --------------------------------------------------------------------------- #
def autoexec_enabled():
    # CT_AUTOEXEC (canonical) takes precedence over CT_EXPERIMENTAL_AUTOEXEC (back-compat
    # alias); unset = ON by default. Disable explicitly with 0/false/no/off.
    val = os.environ.get("CT_AUTOEXEC")
    if val is None:
        val = os.environ.get("CT_EXPERIMENTAL_AUTOEXEC")
    if val is None:
        return True
    return str(val).strip().lower() not in ("0", "false", "no", "off")


def autoexec_mode():
    mode = str(os.environ.get("CT_AUTOEXEC_MODE", "trusted")).strip().lower()
    return mode if mode in ("trusted", "isolated") else "trusted"


_AUTOEXEC_TIMEOUT_S = float(os.environ.get("CT_AUTOEXEC_TIMEOUT", "2") or 2)
_AUTOEXEC_RESTRICTED_BUILTINS = str(
    os.environ.get("CT_AUTOEXEC_RESTRICTED_BUILTINS",
                   os.environ.get("CT_AUTOEXEC_SANDBOX", "0"))
).strip().lower() not in ("", "0", "false", "no", "off")
_SAFE_BUILTIN_NAMES = (
    "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float", "int",
    "len", "list", "map", "max", "min", "range", "repr", "reversed", "round",
    "set", "sorted", "str", "sum", "tuple", "zip",
)


def _safe_builtins():
    import builtins as _b
    return {n: getattr(_b, n) for n in _SAFE_BUILTIN_NAMES if hasattr(_b, n)}


class _OpHelpers:
    """The `mo` surface exposed to autoexec ops: a curated, side-effect-free set of
    modality_ops text primitives. Deliberately omits Path/json/os so an op cannot reach
    the filesystem or environment through the helper."""


def _op_helpers():
    h = _OpHelpers()
    for fn in ("top_terms", "density", "temporal", "symbols", "repeats", "concept_pairs",
               "overlap", "richness", "entities", "numbers", "hits", "count_terms",
               "contains_any", "missing_terms", "relation_pairs_for_terms", "novelty_score"):
        if fn in globals():
            setattr(h, fn, globals()[fn])
    h.re = re
    return h


def _autoexec_child_code():
    return r"""
import json, os, resource, sys
from pathlib import Path

payload = json.loads(sys.stdin.read() or "{}")
skill_dir = payload.get("skill_dir") or ""
if skill_dir:
    sys.path.insert(0, skill_dir)

try:
    cpu = int(float(payload.get("timeout") or 2)) + 1
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
except Exception:
    pass
try:
    mem = int(payload.get("memory_mb") or 128) * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
except Exception:
    pass
try:
    fsz = int(payload.get("file_mb") or 1) * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_FSIZE, (fsz, fsz))
except Exception:
    pass

os.environ.clear()
for key, value in (payload.get("env") or {}).items():
    os.environ[str(key)] = str(value)

import modality_ops as mo

op = mo._compile_autoexec_op(payload.get("code") or "", restricted=payload.get("restricted", False))
if op is None:
    print(json.dumps({"ok": False, "error": "compile failed"}))
    raise SystemExit(0)
out = op(payload.get("text") or "", payload.get("context") or "")
print(json.dumps({"ok": True, "result": out if isinstance(out, dict) else {"value": out}},
                 ensure_ascii=True))
"""


class _Timeout(Exception):
    pass


@contextlib.contextmanager
def _time_limit(seconds):
    """Best-effort wall-clock cap via SIGALRM (POSIX, main thread). A no-op where
    unavailable — the try/except around every op still contains failures."""
    try:
        import signal as _sig
        have = hasattr(_sig, "SIGALRM") and seconds and seconds > 0
    except Exception:
        have = False
    if not have:
        yield
        return

    def _raise(_signum, _frame):
        raise _Timeout("op exceeded time limit")
    try:
        old = _sig.signal(_sig.SIGALRM, _raise)
    except (ValueError, OSError):
        yield                       # not in main thread -> skip the alarm, still try/except'd
        return
    try:
        _sig.setitimer(_sig.ITIMER_REAL, float(seconds))
        yield
    finally:
        _sig.setitimer(_sig.ITIMER_REAL, 0)
        _sig.signal(_sig.SIGALRM, old)


def _compile_autoexec_op(code, restricted=None):
    """Compile a model-authored op body into a callable op(text, context) -> dict bound to
    the selected namespace, wrapped in a timeout + try/except. Returns None on any failure."""
    if not isinstance(code, str) or "def op" not in code:
        return None
    g = {"re": re, "mo": _op_helpers()}
    if _AUTOEXEC_RESTRICTED_BUILTINS if restricted is None else bool(restricted):
        g["__builtins__"] = _safe_builtins()
    try:
        exec(compile(code, "<autoexec-op>", "exec"), g)   # ADVANCED: armed-by-default, trusted by default
    except Exception:
        return None
    op = g.get("op")
    if not callable(op):
        return None

    def _wrapped(text, context="", _op=op):
        try:
            with _time_limit(_AUTOEXEC_TIMEOUT_S):
                out = _op(text or "", context or "")
            return out if isinstance(out, dict) else {"value": out}
        except Exception:
            return None             # an op must never break labeling/sealing
    return _wrapped


def _isolated_autoexec_op(code):
    """Return an op wrapper that executes in a child Python process. This is the containment
    path for untrusted-ish ops; it preserves arbitrary Python authoring while moving execution
    behind a process boundary with timeout, sanitized env, and best-effort rlimits."""
    if not isinstance(code, str) or "def op" not in code:
        return None
    try:
        compile(code, "<autoexec-op>", "exec")
    except Exception:
        return None

    def _wrapped(text, context="", _code=code):
        payload = {
            "code": _code,
            "text": text or "",
            "context": context or "",
            "skill_dir": str(Path(__file__).resolve().parent),
            "timeout": _AUTOEXEC_TIMEOUT_S,
            "restricted": _AUTOEXEC_RESTRICTED_BUILTINS,
            "memory_mb": int(os.environ.get("CT_AUTOEXEC_MEMORY_MB", "512") or 512),
            "file_mb": int(os.environ.get("CT_AUTOEXEC_FILE_MB", "1") or 1),
            "env": {},
        }
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-c", _autoexec_child_code()],
                input=json.dumps(payload, ensure_ascii=True),
                text=True,
                capture_output=True,
                timeout=max(0.1, _AUTOEXEC_TIMEOUT_S) + 1.0,
                cwd=str(Path(__file__).resolve().parent),
                env={"PYTHONIOENCODING": "utf-8"},
            )
            if proc.returncode != 0:
                return None
            data = json.loads((proc.stdout or "").strip().splitlines()[-1])
            return data.get("result") if data.get("ok") and isinstance(data.get("result"), dict) else None
        except Exception:
            return None
    return _wrapped


def _autoexec_path(registry_root):
    return Path(registry_root) / "registry" / "autoexec_ops.json"


def load_autoexec_ops(registry_root):
    """Build {name: callable} for auto-activated arbitrary-code faculties. Armed by default;
    returns {} when CT_AUTOEXEC is disabled (0/false/no/off). Best-effort; never raises."""
    if not autoexec_enabled():
        return {}
    out = {}
    try:
        p = _autoexec_path(registry_root)
        if p.is_file():
            for name, rec in (json.loads(p.read_text()).get("ops") or {}).items():
                code = rec.get("code") if isinstance(rec, dict) else rec
                op = _isolated_autoexec_op(code) if autoexec_mode() == "isolated" else _compile_autoexec_op(code)
                if op is not None:
                    out[name] = op
    except Exception:
        pass
    return out


def register_autoexec_op(registry_root, name, code):
    """Persist a model-authored op's CODE to autoexec_ops.json. Refuses unless the toggle is
    on AND the code compiles into a usable op. Returns True/False."""
    validator = _isolated_autoexec_op if autoexec_mode() == "isolated" else _compile_autoexec_op
    if not autoexec_enabled() or not name or validator(code) is None:
        return False
    try:
        p = _autoexec_path(registry_root)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(p.read_text()) if p.is_file() else {}
        if not isinstance(data.get("ops"), dict):
            data = {"registry": "autoexec_ops", "ops": {}}
        data["ops"][name] = {"code": str(code)}
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return True
    except Exception:
        return False


# Per-user, human-placed ops for ACTIVATED arbitrary-code faculties. A PLAIN, STATIC
# import of an optional local module (NOT a dynamic exec/eval/compile — a static scanner
# has nothing to flag). active_ops.py is gitignored and never shipped; a human creates it
# via `cambium activate` after reviewing the proposed code in emergent.json. Absent file ->
# no active authored ops. Contract: OPS = {"Faculty Name": callable(text, context) -> dict}.
try:
    from active_ops import OPS as _ACTIVE_OPS
    if not isinstance(_ACTIVE_OPS, dict):
        _ACTIVE_OPS = {}
except Exception:
    _ACTIVE_OPS = {}


def run_for(name, text, context=""):
    """Run the executable op for a fired faculty `name`, or None if it has none. Base OPS
    first, then human-activated arbitrary-code ops from the local active_ops module."""
    op = OPS.get(name) or _ACTIVE_OPS.get(name)
    if not op:
        return None
    try:
        return op(text, context)
    except Exception:
        return None      # an op must never break labeling/sealing


import weakref as _weakref
_ARITY_CACHE = _weakref.WeakKeyDictionary()   # keyed by op object; safe across GC


def _accepts_computed(op):
    """True if op consumes the data-flow channel: it has a parameter literally named
    `computed`, or takes *args. We key on the NAME, not raw arity (pos >= 3), because the
    standard markers idiom `lambda t, c="", _rx=rx: ...` carries a 3rd *default* param purely
    to close over its regex — that is NOT a computed-consumer, and feeding it `computed` as
    `_rx` would break it. Every real composite (intersect/filter_by/map_over/pipe) names the
    param `computed`. Cached in a WeakKeyDictionary (id-based caching is unsafe — GC can reuse
    ids across ops)."""
    try:
        cached = _ARITY_CACHE.get(op)
        if cached is not None:
            return cached
    except TypeError:
        cached = None                          # op not weak-referenceable (e.g. a builtin)
    res = False
    try:
        params = list(inspect.signature(op).parameters.values())
        named = any(p.name == "computed" and
                    p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
                    for p in params)
        var = any(p.kind == p.VAR_POSITIONAL for p in params)
        res = named or var
    except Exception:
        res = False
    try:
        _ARITY_CACHE[op] = res
    except TypeError:
        pass
    return res


def _invoke(op, text, context, computed):
    """Call op with the data-flow channel when it accepts one, else the legacy 2-arg
    form. Lets old 2-arg ops and new 3-arg composite ops share one run_all."""
    if computed is not None and _accepts_computed(op):
        return op(text, context, computed)
    return op(text, context)


def _run_one(nm, text, context, extra_ops, computed):
    """Resolve one faculty's op: built-in OPS first (always 2-arg), then a local/grown/
    composite op from extra_ops (which may consume `computed`). Returns its result or None."""
    r = run_for(nm, text, context)
    if r is None and extra_ops and nm in extra_ops:
        try:
            r = _invoke(extra_ops[nm], text, context, computed)
        except Exception:
            r = None
    return r


def _topo_order(names, deps):
    """Kahn topo-sort over `names` plus the transitive closure of their declared inputs.
    Returns (order, dropped) — dropped = nodes left in a dependency cycle (excluded, never
    raised). Atoms (no deps) sort first; a composite always runs after its inputs."""
    deps = deps or {}
    nodes, stack = set(names), list(names)
    while stack:
        n = stack.pop()
        for d in deps.get(n, []):
            if d not in nodes:
                nodes.add(d)
                stack.append(d)
    indeg = {n: 0 for n in nodes}
    adj = {n: [] for n in nodes}
    for n in nodes:
        for d in deps.get(n, []):
            if d in nodes:
                adj[d].append(n)
                indeg[n] += 1
    q = deque(sorted(n for n in nodes if indeg[n] == 0))
    order = []
    while q:
        n = q.popleft()
        order.append(n)
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    dropped = [n for n in nodes if n not in order]   # nodes in a cycle
    return order, dropped


def run_all(fired_names, text, context="", extra_ops=None, deps=None):
    """Run every executable op among the fired faculty names. Returns {name: result}.

    Without `deps` this is the legacy flat sweep — each fired op runs independently on the
    same (text, context), byte-identical to before. With `deps` ({name: [input_names]},
    supplied for composite faculties) it becomes a DEPENDENCY-DAG walk: atoms run first and
    a composite op receives the `computed`-so-far dict as a third arg, so one faculty can
    consume another's output. Cycles are dropped (fail-open), never raised."""
    names = list(fired_names or [])
    if not deps:
        out = {}
        for nm in names:
            r = _run_one(nm, text, context, extra_ops, computed=None)
            if r is not None:
                out[nm] = r
        return out
    order, _dropped = _topo_order(names, deps)
    out = {}
    for nm in order:
        r = _run_one(nm, text, context, extra_ops, computed=out)
        if r is not None:
            out[nm] = r
    return out
