#!/usr/bin/env python3
# Copyright (c) 2026 cyberphysicsai. MIT License.
"""Executable modality operations — the frames→mechanisms layer.

Most faculties are cognitive FRAMES: a name + a `function` description the model is
primed to perform. They prime reasoning, but they do not *execute* it — so they
amplify only in proportion to the model's own capability. This module is the start
of the other kind: faculties that, when they fire, actually RUN and attach a
computed result to the ring, so a piece of the reasoning is performed by code.

v3.4 ships ONE executable modality end to end — **Richness Scoring** — whose op
computes a depth/richness score from content. The same `richness()` function is the
shared mechanism behind the PoQ under-effort signal (poq.py) and the audit depth
governor (audit.py), so "exhaustive" can be made to mean "reasoned about", not just
"touched". Adding more executable faculties is a matter of registering ops here.

Stdlib only. Python 3.8+.
"""
import re

_WORD = re.compile(r"[A-Za-z0-9_]+")
# Signals of specific, grounded reasoning (vs vague hand-waving): line/range refs,
# ring refs, hex/addresses, file paths, scoped names, function calls.
_CITATION = re.compile(
    r"\bL\d{1,7}\b|\b\d{1,7}\s*[-–]\s*\d{1,7}\b|\bline[s]?\s+\d+|#\d{1,7}\b|"
    r"\b0x[0-9a-fA-F]+\b|\b[\w./-]+\.[A-Za-z]{1,5}\b|::\w+|\b\w+\(\)", re.I)
# Markers of articulated reasoning rather than a verdict with no body.
_STRUCTURE = re.compile(
    r"[;:]|->|=>|\b(because|therefore|whereas|however|specifically|"
    r"e\.g\.|i\.e\.|due to|so that|which means)\b", re.I)
# Hollow completion/clean claims — a verdict with no supporting substance.
_HOLLOW = re.compile(
    r"\b(looks?\s+(?:fine|good|ok|okay)|seems?\s+(?:fine|ok|okay)|no\s+issues?|"
    r"all\s+(?:good|clear)|nothing\s+(?:to|of)\s+note|clean|reviewed|done|complete)\b", re.I)

RICHNESS_FLOOR = 90        # below this, a completion/clean claim is treated as shallow


def richness(text, context=""):
    """Compute a 0–255 depth score for a piece of reasoning, plus its signals.

    Rewards length (capped), lexical diversity, and specificity (cited lines/symbols,
    articulated structure). A bare "looks fine / reviewed / clean" with no substance
    is capped low by construction — the asymmetry the conscience otherwise misses."""
    text = text or ""
    toks = [t.lower() for t in _WORD.findall(text)]
    n = len(toks)
    uniq = len(set(toks))
    unique_ratio = (uniq / n) if n else 0.0
    has_citation = bool(_CITATION.search(text))
    structural = len(_STRUCTURE.findall(text))
    hollow = bool(_HOLLOW.search(text)) and n < 25 and not has_citation
    length_component = min(120, n * 2)              # ~60+ tokens saturates
    diversity_component = int(unique_ratio * 60)
    specificity = (50 if has_citation else 0) + min(25, structural * 5)
    score = min(255, length_component + diversity_component + specificity)
    if hollow:
        score = min(score, 50)                      # a verdict with no body is shallow
    return {
        "score": int(score), "tokens": n, "unique_ratio": round(unique_ratio, 3),
        "has_citation": has_citation, "structural": structural, "hollow": hollow,
    }


def is_shallow(text, floor=RICHNESS_FLOOR):
    return richness(text)["score"] < floor


# modality name -> executable op: op(text, context) -> dict merged into the ring labels.
OPS = {
    "Richness Scoring": lambda text, context="": {"richness": richness(text, context)},
}


def run_for(name, text, context=""):
    """Run the executable op for a fired modality `name`, or None if it has none."""
    op = OPS.get(name)
    if not op:
        return None
    try:
        return op(text, context)
    except Exception:
        return None      # an op must never break labeling/sealing


def run_all(fired_names, text, context=""):
    """Run every executable op among the fired modality names; return {name: result}."""
    out = {}
    for nm in fired_names or []:
        r = run_for(nm, text, context)
        if r is not None:
            out[nm] = r
    return out
