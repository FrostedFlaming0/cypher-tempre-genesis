"""op_need — the mid-turn op-write trigger.

The structural half of the per-turn loop's growth: when a turn reveals genuine need for
a COMPUTATION (not just a new word), surface an AUTHOR-OP prompt so the model can author a
richer faculty op THIS turn. It fires on the OPERATION and on dropped structured signal —
detected on the turn's input + thought — NOT on vocabulary novelty in the sealed summary
(the failure mode that coupled op-authoring to fill_gap and fired on familiar words).

Three layers; the trigger fires if ANY trips:

  Layer 1 — Computational-Shape Sensing (modality_ops.comp_shape): an operation verb /
            (struct-noun + aggregate cue) over >=2 operands. STRONG verbs fire alone;
            WEAK verbs need corroboration. Keys the prompt to the operation.
  Layer 2 — Computed-insufficiency: a bare markers faculty ACTUALLY FIRED on this turn
            (callers pass the fired bare-markers faculties as `faculty_terms`) while the
            same text carries >=2 numbers or >=2 code-symbols that op cannot compute over.
            Without a fired bare-markers faculty there is no insufficiency to point at —
            numbers in ordinary prose must not trip the trigger. (Entities excluded —
            proper-noun noise.)
  Layer 3 — Self-declaration seam: the model passes --computed-need "<desc>"; deterministic
            fire. The seam doctrine — the model supplies the judgment the code cannot.

No code is authored here: the trigger automates the WHEN; the model authors the op (via
`cambium.py autoexec`). Fail-open by construction — callers wrap in try/except and the
helpers never raise on bad input.
"""
from __future__ import annotations

try:
    import modality_ops as _mo
except Exception:                       # pragma: no cover - import guard
    _mo = None


def layer1_shape(text: str) -> dict:
    """Operation-shape detection. Delegates to modality_ops.comp_shape (the shared
    Computational-Shape detector); kept in modality_ops so it can later be promoted to a
    registered faculty without changing this trigger."""
    if _mo is None:
        return {"fired": False, "detail": "modality_ops unavailable"}
    try:
        return _mo.comp_shape(text or "")
    except Exception:
        return {"fired": False, "detail": "comp_shape error"}


def layer2_insufficiency(text: str, faculty_terms=None) -> dict:
    """A bare markers op returns only {hits,count}. If one ACTUALLY FIRED this turn
    (`faculty_terms` = the fired bare-markers faculties, supplied by the caller) while the
    same text carries >=2 numbers or >=2 code-symbols, that op ignored structure it could
    compute over -> op-authoring-worthy, pointed at the specific faculty. With no fired
    bare-markers faculty there is nothing that ignored the signal — plain prose carrying
    two numbers must NOT trip the trigger (the measured 4/5 false-fire mode of the
    unguarded version). Entities (capitalized prose words) are EXCLUDED to avoid
    proper-noun false flags."""
    if _mo is None:
        return {"fired": False, "detail": "modality_ops unavailable"}
    try:
        fired_markers = [t for t in (faculty_terms or [])
                         if isinstance(t, str) and t.strip()]
        if not fired_markers:
            return {"fired": False,
                    "detail": "no bare-markers faculty fired — nothing ignored the structure"}
        nums, syms = _mo.numbers(text or ""), _mo.symbols(text or "")
        dropped = []
        if len(nums) >= 2:
            dropped.append(f"{len(nums)} quantities {nums[:4]}")
        if len(syms) >= 2:
            dropped.append(f"{len(syms)} symbols {syms[:4]}")
        return {"fired": bool(dropped),
                "detail": (f"bare-markers {fired_markers[:3]} emitted presence only; "
                           "richer primitives found: "
                           + "; ".join(dropped)) if dropped else "no structured signal dropped"}
    except Exception:
        return {"fired": False, "detail": "insufficiency error"}


def layer3_declared(computed_need) -> dict:
    need = (computed_need or "").strip() if isinstance(computed_need, str) else ""
    return {"fired": bool(need), "detail": f"declared: {need}" if need else "none declared"}


def op_need(input_text: str, thought: str = "", faculty_terms=None,
            computed_need=None) -> dict:
    """Combine the three layers over (input + thought). Returns
    {fire, reasons, L1, L2, L3}. fire = L1 or L2 or L3."""
    substrate = f"{input_text or ''} {thought or ''}".strip()
    l1 = layer1_shape(substrate)
    l2 = layer2_insufficiency(substrate, faculty_terms)
    l3 = layer3_declared(computed_need)
    fire = bool(l1.get("fired") or l2.get("fired") or l3.get("fired"))
    reasons = []
    if l1.get("fired"):
        reasons.append("operation-shape (L1): " + l1.get("detail", ""))
    if l2.get("fired"):
        reasons.append("computed-insufficiency (L2): " + l2.get("detail", ""))
    if l3.get("fired"):
        reasons.append("self-declared (L3): " + l3.get("detail", ""))
    return {"fire": fire, "reasons": reasons, "L1": l1, "L2": l2, "L3": l3}
