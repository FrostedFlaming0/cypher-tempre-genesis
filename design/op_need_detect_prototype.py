"""Prototype: mid-turn op-write trigger via three detection layers.

Goal: fire AUTHOR-OP on genuine STRUCTURAL-COMPUTATION need (detected on input+thought),
NOT on vocabulary novelty in the sealed summary. Fire if ANY layer trips.

Layer 1 — Computational-Shape Sensing: operation verb / (struct-noun + aggregate cue)
          paired with >=2 content operands. Markers ops structurally cannot do these.
Layer 2 — Computed-insufficiency: a bare markers op returned only presence while richer
          primitives (numbers/symbols/concepts/entities) find structure it dropped.
Layer 3 — Self-declaration seam: the model declares a computed-need; deterministic fire.
"""
import re, sys
from pathlib import Path

ROOT = Path("/home/james/.claude/skills/cypher-tempre-self-model")
sys.path.insert(0, str(ROOT))
import modality_ops as mo

# ---------------- Layer 1: Computational-Shape Sensing ----------------
# STRONG verbs are unambiguously computational -> fire alone (with >=2 operands).
# WEAK verbs occur in ordinary prose ("compare notes", "map onto") -> require corroboration
# (an aggregate cue OR a struct noun OR >=2 numbers/symbols) before firing.
STRONG_VERBS = re.compile(r"\b(rank|count|tally|correlate|co-?occurs?|aggregate|intersect|"
                          r"histogram|group\s+by)\b", re.I)
WEAK_VERBS = re.compile(r"\b(sort|order|compare|sum|average|mean|map\s+over|filter|derive|"
                        r"measure|join|diff|overlap)\b", re.I)
STRUCT_NOUNS = re.compile(r"\b(graph|dependency|tree|matrix|distribution|interval|sequence|"
                          r"ratio|percentage|topolog\w*)\b", re.I)
AGG_CUES = re.compile(r"\b(how\s+many|number\s+of|per|each|ratio|percent|across|between|"
                      r"most|least|total)\b|%", re.I)
_CUE_WORDS = set(re.findall(r"[a-z]+", STRONG_VERBS.pattern + WEAK_VERBS.pattern +
                            AGG_CUES.pattern + STRUCT_NOUNS.pattern))

def layer1_shape(text):
    t = text or ""
    strong = STRONG_VERBS.search(t)
    weak = WEAK_VERBS.search(t)
    struct = STRUCT_NOUNS.search(t)
    agg = AGG_CUES.search(t)
    n_struct = len(mo.numbers(t)) + len(mo.symbols(t))
    corroborated = bool(agg) or bool(struct) or n_struct >= 2
    gate = bool(strong) or (bool(weak) and corroborated)
    content = [w for w in mo._content(t) if w not in _CUE_WORDS]
    operands = list(dict.fromkeys(content))
    fired = gate and len(operands) >= 2
    why = []
    if strong: why.append(f"strong-verb='{strong.group(0)}'")
    if weak and corroborated:
        why.append(f"weak-verb='{weak.group(0)}'+corrob({'agg' if agg else ''}"
                   f"{'/struct' if struct else ''}{'/nums' if n_struct>=2 else ''})")
    elif weak:
        why.append(f"weak-verb='{weak.group(0)}'(uncorroborated)")
    return {"fired": fired, "operands": len(operands),
            "detail": (", ".join(why) or "no operation signature") +
                      f"; operands={len(operands)}"}

# ---------------- Layer 2: Computed-insufficiency ----------------
def layer2_insufficiency(text, faculty_terms):
    """A bare markers faculty returns only {hits,count}. If the SAME text carries
    quantitative/relational structure (>=2 numbers or >=2 code-symbols) that a markers op
    cannot compute over, the faculty is op-authoring-worthy. Entities (capitalized prose
    words) are EXCLUDED — too noisy (proper nouns trip on ordinary narration)."""
    op = mo.build_op({"primitive": "markers", "terms": faculty_terms})
    markers_out = op(text, "") if op else {"hits": [], "count": 0}
    nums, syms = mo.numbers(text), mo.symbols(text)
    dropped = []
    if len(nums) >= 2: dropped.append(f"{len(nums)} quantities {nums[:4]}")
    if len(syms) >= 2: dropped.append(f"{len(syms)} symbols {syms[:4]}")
    fired = bool(dropped)
    return {"fired": fired,
            "detail": ("markers emitted presence only; richer primitives found: " +
                       "; ".join(dropped)) if dropped else "no structured signal dropped"}

# ---------------- Layer 3: Self-declaration seam ----------------
def layer3_declared(computed_need):
    return {"fired": bool(computed_need),
            "detail": f"declared: {computed_need}" if computed_need else "none declared"}

# ---------------- Combined trigger ----------------
def op_need(input_text, thought="", faculty_terms=None, computed_need=None):
    substrate = f"{input_text} {thought}".strip()
    l1 = layer1_shape(substrate)
    l2 = layer2_insufficiency(substrate, faculty_terms or ["gap"])
    l3 = layer3_declared(computed_need)
    fire = l1["fired"] or l2["fired"] or l3["fired"]   # any layer trips the trigger
    return {"FIRE": fire, "L1": l1, "L2": l2, "L3": l3}

# ============================ TRUTH TABLE ============================
CASES = [
    # (label, expect_fire, input, thought, faculty_terms, computed_need)
    ("STRUCT: granularity-check task", True,
     "rank dependency graph nodes by how many symbols import each module", "", None, None),
    ("STRUCT: overconfident-risk", True,
     "detect when a confident assertion co-occurs with a high-risk action", "", None, None),
    ("STRUCT: quantitative thought (L2 backstop)", True,
     "summarize the audit", "found bugs in 5 of 8 modules, 62% across 3 services, 12 call-sites",
     ["bug", "module"], None),
    ("STRUCT: self-declared need (L3)", True,
     "explain the proposal", "I computed Jaccard overlap of matched-token sets and greedy coverage",
     None, "pairwise set-overlap + greedy max-coverage selection over faculties"),
    ("LEXICAL: plan prose (neg control)", False,
     "give a better explanation of the four changes",
     "Composite specs as data plus an expanded combinator menu staying in the no-exec safe lane",
     None, None),
    ("LEXICAL: narrative summary (neg control)", False,
     "refresh my memory on the composability proposal",
     "Refreshed James in plain terms; faculties talk to each other and combinations are saved",
     None, None),
    ("LEXICAL: rhetorical 'compare' (false-pos guard)", False,
     "let's compare notes later and keep it observational", "", None, None),
    ("LEXICAL: greeting", False, "thanks, that makes sense", "", None, None),
]

print("=" * 92)
ok = 0
for label, expect, inp, thought, terms, need in CASES:
    r = op_need(inp, thought, terms, need)
    fire = r["FIRE"]
    passed = (fire == expect)
    ok += passed
    print(f"[{'PASS' if passed else 'FAIL'}] {label}")
    print(f"      expect={'FIRE' if expect else 'quiet'}  got={'FIRE' if fire else 'quiet'}")
    print(f"      L1 {('FIRE ' if r['L1']['fired'] else 'quiet')}: {r['L1']['detail']}")
    print(f"      L2 {('flag ' if r['L2']['fired'] else 'quiet')}: {r['L2']['detail']}")
    print(f"      L3 {('FIRE ' if r['L3']['fired'] else 'quiet')}: {r['L3']['detail']}")
    print()
print("=" * 92)
print(f"RESULT: {ok}/{len(CASES)} cases match expectation")
