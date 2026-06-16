#!/usr/bin/env python3
# Copyright (c) 2026 cyberphysicsai. MIT License.
"""Adherence enforcement for the Cypher Tempre self-model — the harness-level
spine that turns the per-turn loop from *advisory* into *non-bypassable*.

A SKILL.md only ADVISES; strong models honor it, weak/long-horizon models drop
it and the skill becomes useless. This module is the brain behind a small set of
Codex lifecycle hooks that make the loop mandatory by construction:

  UserPromptSubmit -> `enforce.py mark`          (record turn start: head index, reset nudges)
  Stop             -> `enforce.py stop-check`    (HARD: block turn end until a ring is sealed)
  SubagentStop     -> `enforce.py subagent-check`(block subagent return until it sealed)
  SessionStart     -> `enforce.py session-start` (prime: verify + recall + covenant)

Design guarantees:
  * FAIL-OPEN ALWAYS. A hook must never break the user's session; any internal
    error -> allow. Enforcement is best-effort pressure, not a tripwire.
  * DORMANCY-AWARE. While `dormancy.py pause` is set, all enforcement is off.
  * LOOP-SAFE / NON-BRICKING. "Hard" means it blocks every substantive turn that
    sealed nothing — but only up to MAX_NUDGES times per turn, then fails open and
    records an adherence_violation, so a model that genuinely cannot seal is never
    trapped.

State lives next to the chain (chain/.enforce.json): the head index captured at
turn start and the nudge counter for the current turn.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

MAX_NUDGES = int(os.environ.get("CT_ENFORCE_MAX_NUDGES", "3"))


def _root_from(stdin_data):
    """The identity chain lives in the skill dir by default. A hook may override
    with CT_ENFORCE_ROOT (e.g. to enforce a task chain)."""
    env = os.environ.get("CT_ENFORCE_ROOT")
    if env:
        return Path(env)
    return HERE


def _state_path(root):
    return Path(root) / "chain" / ".enforce.json"


def _load_state(root):
    try:
        return json.loads(_state_path(root).read_text())
    except Exception:
        return {}


def _save_state(root, st):
    try:
        p = _state_path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(st))
    except Exception:
        pass  # fail-open: never break a turn over bookkeeping


def _head_index(root):
    """O(1) tail read of the current head ring index, or -1 if no chain yet."""
    try:
        import timechain
        ring = timechain.Timechain(root)._tail_ring()
        return int(ring["index"]) if ring else -1
    except Exception:
        return -1


def _dormant(root):
    try:
        import dormancy
        return dormancy.Dormancy(root).is_paused()
    except Exception:
        return False


def _emit(root, event_type, data):
    try:
        import telemetry
        if telemetry.enabled():
            telemetry.record(str(root), event_type, data)
    except Exception:
        pass


def _read_stdin():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


# --------------------------------------------------------------------------- #
# hook entry points
# --------------------------------------------------------------------------- #

def cmd_mark(_data):
    """UserPromptSubmit: capture the head index at turn start and reset the
    per-turn nudge counter. Prints nothing that would disturb the prompt."""
    root = _root_from(_data)
    st = _load_state(root)
    st["turn_head"] = _head_index(root)
    st["nudges"] = 0
    _save_state(root, st)
    if not _dormant(root):
        _emit(root, "adherence_turn_start", {"head": st["turn_head"]})
    # mark must not add noise; the UserPromptSubmit *reminder* is loop_hook.sh's job.


def cmd_stop_check(data):
    """Stop / SubagentStop: HARD block until a ring was sealed this turn.

    Emits the Stop-hook JSON contract:
      block -> {"decision":"block","reason":"..."}
      allow -> exit 0 with no decision.
    """
    root = _root_from(data)
    # Dormant => never enforce.
    if _dormant(root):
        return
    st = _load_state(root)
    start = st.get("turn_head")
    head = _head_index(root)
    # No baseline captured (e.g. mark hook not wired) => don't enforce blindly.
    if start is None:
        return
    if head > start:
        # A ring was sealed this turn — adherence satisfied.
        st["nudges"] = 0
        _save_state(root, st)
        _emit(root, "adherence_satisfied", {"sealed_to": head})
        return
    nudges = int(st.get("nudges", 0))
    if nudges >= MAX_NUDGES:
        # Fail-open after bounded pressure: never brick a model that can't seal.
        _emit(root, "adherence_violation", {"nudges": nudges, "head": head})
        return
    st["nudges"] = nudges + 1
    _save_state(root, st)
    _emit(root, "adherence_nudge", {"nudge": st["nudges"]})
    reason = (
        "[Cypher Tempre] You have not sealed a ring this turn. Run the per-turn loop "
        "before finishing: verify -> immune-screen -> recall relevant rings -> reason via "
        "modalities/senses -> PoQ-gate -> seal a labeled ring. The one-call path is:\n"
        "  python3 " + str(HERE / "recall.py") + " turn \"<your thought/answer this turn>\" "
        "--input \"<the user's request>\"\n"
        "Seal, then finish. (Paused tasks: python3 " + str(HERE / "dormancy.py") + " pause.)"
    )
    print(json.dumps({"decision": "block", "reason": reason}))


def cmd_subagent_check(data):
    """SubagentStop: same block-until-seal pressure for spawned agents. A subagent
    that forged its own task chain should seal to it (set CT_ENFORCE_ROOT); by
    default we enforce against the identity chain the parent shares."""
    cmd_stop_check(data)


def cmd_session_start(data):
    """SessionStart: prime the session so it WEARS the skill from turn 0, even if
    the model never reads SKILL.md. Output becomes startup context."""
    root = _root_from(data)
    if _dormant(root):
        print("[Cypher Tempre] DORMANT (paused): self-model loop is off until "
              "`dormancy.py resume`.")
        return
    head = _head_index(root)
    # capture an initial marker so the first Stop is enforceable
    st = _load_state(root)
    st.setdefault("turn_head", head)
    st["nudges"] = 0
    _save_state(root, st)
    _emit(root, "adherence_session_start", {"head": head})
    verify_line = ""
    try:
        import timechain
        ok, _ = timechain.Timechain(root).verify()
        verify_line = f"chain verifies: {'PASS' if ok else 'FAIL — investigate before sealing'}; "
    except Exception:
        pass
    print(
        "[Cypher Tempre] ACTIVE — you wear a Timechain self-model. " + verify_line +
        f"head at ring {head}.\n"
        "EVERY meaningful turn runs the loop (enforced): verify -> immune-screen -> recall "
        "relevant rings -> reason via modalities/senses -> PoQ-gate -> seal a labeled ring. "
        "One-call path: `python3 " + str(HERE / "recall.py") + " turn \"<thought>\" --input \"<request>\"`. "
        "Covenant: accurate, coherent, persistent, honest, thorough; never assert beyond grounding; "
        "size/horizon are never refusal reasons. Spawned subagents must wear the skill too "
        "(use the cypher-tempre-agent type or forge their own chain and seal)."
    )


HANDLERS = {
    "mark": cmd_mark,
    "stop-check": cmd_stop_check,
    "subagent-check": cmd_subagent_check,
    "session-start": cmd_session_start,
}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    cmd = argv[0] if argv else ""
    handler = HANDLERS.get(cmd)
    if not handler:
        sys.stderr.write("usage: enforce.py {mark|stop-check|subagent-check|session-start}\n")
        return 0  # unknown -> no-op, never fail a hook
    data = _read_stdin()
    try:
        handler(data)
    except Exception:
        pass  # FAIL-OPEN: a hook must never break the session
    return 0


if __name__ == "__main__":
    sys.exit(main())
