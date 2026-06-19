#!/usr/bin/env python3
# Copyright (c) 2026 cyberphysicsai. MIT License.
"""Adherence enforcement for the Cypher Tempre self-model — the harness-level
spine that turns the per-turn loop from *advisory* into *non-bypassable*.

A SKILL.md only ADVISES; strong models honor it, weak/long-horizon models drop
it and the skill becomes useless. This module is the brain behind a small set of
Claude Code hooks that make the loop mandatory by construction:

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


def _env_enabled(name):
    """Parse boolean env flags conventionally: unset/empty/0/false/no/off are off."""
    raw = os.environ.get(name)
    if raw is None:
        return False
    return raw.strip().lower() not in {"", "0", "false", "no", "off"}


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


# --------------------------------------------------------------------------- #
# audit coverage governor — the PUSH layer for exhaustive audits
#
# `audit.py open` drops a pointer (chain/.active_audit) naming the task chain
# under review. While that pointer exists and the audit is < 100% reviewed, a
# turn that made NO review progress (and sealed nothing) is treated as "stopped
# early" — the exact Firefox/Bitcoin-Core failure — and blocked (bounded), so
# the model keeps grinding the unreviewed-block queue instead of writing a
# premature "Final Report". Pausing (dormancy) or closing the audit disengages.
# --------------------------------------------------------------------------- #

def _active_audit_root(root):
    """The task chain of the currently-open audit, or None."""
    try:
        ptr = Path(root) / "chain" / ".active_audit"
        if ptr.is_file():
            return (json.loads(ptr.read_text()) or {}).get("root")
    except Exception:
        pass
    return None


def _audit_status(audit_root):
    """O(1) head read of the audit sub-state: (review_cursor, complete) or None."""
    try:
        import timechain
        ring = timechain.Timechain(audit_root)._tail_ring()
        a = ((ring or {}).get("payload") or {}).get("state", {}).get("audit")
        if a:
            return int(a.get("review_cursor", 0)), bool(a.get("complete"))
    except Exception:
        pass
    return None


def _emit(root, event_type, data):
    try:
        import telemetry
        if telemetry.enabled():
            telemetry.record(str(root), event_type, data)
    except Exception:
        pass


def _read_stdin():
    try:
        if sys.stdin is None:
            return {}
        try:
            if sys.stdin.isatty():
                return {}
        except Exception:
            pass
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def _normalize_chain_root(path):
    """Return the project root that contains chain/, correcting chain/ itself."""
    p = Path(path).expanduser()
    try:
        p = p.resolve()
    except Exception:
        p = p.absolute()
    if (p / "rings.jsonl").is_file():
        return p.parent
    return p


def _split_roots(raw):
    out = []
    if not raw:
        return out
    for chunk in str(raw).replace(",", os.pathsep).split(os.pathsep):
        chunk = chunk.strip()
        if chunk:
            out.append(chunk)
    return out


def _event_paths(data):
    paths = []
    for key in ("cwd", "currentWorkingDirectory", "current_working_directory",
                "workspace", "workspaceRoot", "workspace_root", "projectRoot",
                "project_root"):
        val = data.get(key) if isinstance(data, dict) else None
        if isinstance(val, str) and val:
            paths.append(val)
    for key in ("PWD", "CT_WORKSPACE_ROOT"):
        val = os.environ.get(key)
        if val:
            paths.append(val)
    try:
        paths.append(str(Path.cwd()))
    except Exception:
        pass
    return paths


def _looks_like_chain_root(path):
    p = _normalize_chain_root(path)
    return (p / "chain" / "rings.jsonl").is_file()


def _add_candidate(candidates, path, identity_root):
    try:
        p = _normalize_chain_root(path)
        if p.resolve() == Path(identity_root).resolve():
            return
        if _looks_like_chain_root(p):
            candidates[str(p.resolve())] = p.resolve()
    except Exception:
        pass


def _candidate_task_roots(root, data):
    """Nearby task roots used only for root-mismatch diagnostics.

    This deliberately does not make arbitrary task chains satisfy Stop. It only
    lets the nudge explain the likely mistake: the model sealed a task ledger
    while the hook is enforcing the identity ledger.
    """
    candidates = {}
    identity = Path(root)
    for raw in _split_roots(os.environ.get("CT_TASK_ROOTS")):
        _add_candidate(candidates, raw, identity)
    for raw in _split_roots(os.environ.get("CT_TASK_ROOT")):
        _add_candidate(candidates, raw, identity)

    bases = [identity, identity.parent]
    bases += [Path(p).expanduser() for p in _event_paths(data)]
    for base in bases:
        try:
            base = base.resolve()
        except Exception:
            base = base.absolute()
        for p in (
            base,
            base / ".codex" / "cypher-tempre",
            base / ".codex" / "cypher-tempre" / "audit",
            base / "audit",
        ):
            _add_candidate(candidates, p, identity)
        for pattern in (
            ".codex/cypher-tempre/audit*",
            ".codex/cypher-tempre/tasks/*",
            "audit*",
            "tasks/*",
        ):
            try:
                for p in base.glob(pattern):
                    _add_candidate(candidates, p, identity)
            except Exception:
                pass
    return list(candidates.values())[:64]


def _candidate_heads(root, data):
    heads = {}
    for cand in _candidate_task_roots(root, data):
        head = _head_index(cand)
        if head >= 0:
            heads[str(cand)] = head
    return heads


def _task_root_progress(root, data, st):
    before = st.get("turn_task_heads") or {}
    for cand in _candidate_task_roots(root, data):
        key = str(cand)
        old = before.get(key)
        if old is None:
            continue
        head = _head_index(cand)
        if head > int(old):
            try:
                ring = __import__("timechain").Timechain(cand)._tail_ring()
                return {
                    "root": key,
                    "head": head,
                    "hash": (ring or {}).get("ring_hash"),
                    "type": (ring or {}).get("ring_type"),
                }
            except Exception:
                return {"root": key, "head": head, "hash": None, "type": None}
    return None


# --------------------------------------------------------------------------- #
# stdout discipline — a Stop hook's stdout MUST be EXACTLY the decision JSON (or
# empty), or the harness reports "Stop hook error: JSON validation failed". So we
# QUARANTINE all incidental output: while a handler runs, sys.stdout is redirected
# to stderr, and the ONLY thing written to the real stdout is what a handler
# explicitly queues via _emit_stdout. Belt-and-suspenders with `2>/dev/null` in the
# hook wrappers, so neither an import side-effect nor a warning can ever corrupt
# the decision the harness parses.
# --------------------------------------------------------------------------- #
_STDOUT = []


def _emit_stdout(text):
    _STDOUT.append(text)


def _context_json(event, text):
    """The hook-JSON envelope for injecting context. SessionStart/UserPromptSubmit
    hook stdout is parsed as JSON by the harness (the Codex CLI rejects plain text
    with 'invalid ... JSON output'); the Stop hook already proves this harness uses
    the Claude-Code schema, so context goes in hookSpecificOutput.additionalContext.
    This is valid JSON on every harness and still injected as context on Claude Code."""
    return json.dumps({"hookSpecificOutput": {"hookEventName": event,
                                              "additionalContext": text}})


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
    # Snapshot the active audit and its review cursor at turn start so stop-check
    # can tell whether THIS turn advanced it — robust even if the audit COMPLETES
    # mid-turn (which clears the pointer).
    st["turn_audit_root"] = _active_audit_root(root)
    st["turn_audit_cursor"] = None
    st["turn_task_heads"] = _candidate_heads(root, _data)
    if st["turn_audit_root"]:
        s = _audit_status(st["turn_audit_root"])
        if s is not None:
            st["turn_audit_cursor"] = s[0]
    _save_state(root, st)
    if not _dormant(root):
        _emit(root, "adherence_turn_start", {"head": st["turn_head"]})
    # mark stays silent (no stdout) for back-compat; cmd_user_prompt emits the reminder.


def cmd_user_prompt(data):
    """UserPromptSubmit: record turn-start (mark) AND emit the per-turn reminder as a
    proper hook-JSON context envelope. This is what loop_hook.sh wires now — emitting
    plain text here is what the Codex CLI rejected with 'invalid ... JSON output'."""
    cmd_mark(data)
    root = _root_from(data)
    if _dormant(root):
        text = ("[Cypher Tempre] DORMANT (paused): skip the self-model per-turn loop this "
                "turn — answer from base judgment. (Resume via the skill's dormancy.py 'resume'.)")
    else:
        text = ("[Cypher Tempre] ACTIVE — guidance for this turn (context, NOT a command to "
                "execute): run the self-model per-turn loop — verify, immune-screen, recall "
                "relevant rings, reason via modalities/senses, PoQ-gate, then seal a labeled "
                "ring. Do it in one step with the skill's recall.py 'turn' command (exact "
                "invocation in SKILL.md / AGENTS.md). Pausing is the dormancy.py 'pause' command.")
    _emit_stdout(_context_json("UserPromptSubmit", text))


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
    sealed_this_turn = head > start

    # --- audit governor: an open, incomplete audit demands per-turn progress --- #
    # Did THIS turn advance the audit that was open at turn start? (Measured against
    # the turn-start baseline, so the turn that COMPLETES the audit still counts even
    # though completion cleared the pointer.)
    audit_progressed = False
    tar = st.get("turn_audit_root")
    base = st.get("turn_audit_cursor")
    if tar and base is not None:
        s = _audit_status(tar)
        if s is not None:
            audit_progressed = s[0] > base
    # Is an audit currently open AND still incomplete? (governs whether to DEMAND progress)
    audit_active = False
    audit_root = _active_audit_root(root)
    if audit_root:
        s = _audit_status(audit_root)
        if s is not None and not s[1]:
            audit_active = True

    if sealed_this_turn or audit_progressed:
        st["nudges"] = 0
        _save_state(root, st)
        _emit(root, "adherence_satisfied", {"audit_progress": audit_progressed,
                                            "sealed": sealed_this_turn})
        return

    if audit_active:
        if not _bump_or_release(root, st, "adherence_audit_stalled"):
            return
        # Guidance only — name the commands, never emit a verbatim-runnable line (some
        # runtimes execute injected `python3 ...` strings; see loop_hook.sh).
        reason = (
            "[Cypher Tempre] An EXHAUSTIVE audit is open and incomplete, and this turn "
            "reviewed no new blocks. Size/horizon are never reasons to stop — do NOT write a "
            "'Final Report' yet. Continue the unreviewed-block queue: use the skill's audit.py "
            "'next' to fetch the next unreviewed blocks, read every line, then audit.py 'record' "
            "your review (with a finding or an explicit clean pass); check audit.py 'progress'. "
            "The active audit chain root is: " + str(audit_root) + ". A final report is only "
            "legitimate at 100% (audit.py 'report --final' refuses otherwise). To pause, use "
            "dormancy.py 'pause'; to stop the audit, audit.py 'close'. Exact syntax is in SKILL.md.")
        _emit_stdout(json.dumps({"decision": "block", "reason": reason}))
        return

    # --- default: every meaningful turn must leave a sealed ring --- #
    task_progress = _task_root_progress(root, data, st)
    if not _bump_or_release(root, st, "adherence_violation"):
        return
    prefix = ""
    if task_progress:
        task_hash = task_progress.get("hash") or ""
        hash_text = f" ({task_hash[:16]}..)" if task_hash else ""
        _emit(root, "adherence_root_mismatch",
              {"identity_root": str(Path(root).resolve()),
               "task_root": task_progress["root"],
               "task_head": task_progress["head"],
               "task_hash": task_progress.get("hash")})
        prefix = (
            "[Cypher Tempre] Root mismatch detected: you sealed to "
            f"{task_progress['root']} at ring #{task_progress['head']}{hash_text}, "
            f"but I am enforcing {Path(root).resolve()}. "
            "Task chains remain readable by passing --root <task-root>, but they do not "
            "automatically satisfy identity-chain enforcement. If this was an audit, use "
            "continuum.py walk --root <task-root> and audit.py open/record --root "
            "<task-root>; if the task is complete or should be remembered by identity, run "
            "task.py complete --identity-root <identity-root> --task-root <task-root>. "
            "Pass the project root that CONTAINS chain/, not the chain/ folder itself.\n\n"
        )
    reason = (
        prefix +
        "[Cypher Tempre] You have not sealed a ring this turn. Run the per-turn loop "
        "before finishing: verify -> immune-screen -> recall relevant rings -> reason via "
        "modalities/senses -> PoQ-gate -> seal a labeled ring. Do it in one step with the "
        "skill's recall.py 'turn' command (exact invocation in SKILL.md / AGENTS.md), then "
        "finish. To pause instead, use the skill's dormancy.py 'pause' command."
    )
    _emit_stdout(json.dumps({"decision": "block", "reason": reason}))


def _bump_or_release(root, st, violation_event):
    """Increment the per-turn nudge counter. Return True if the caller should
    BLOCK (still within the bounded budget); False if it should fail open (budget
    exhausted) so a model that genuinely cannot proceed is never trapped."""
    nudges = int(st.get("nudges", 0))
    if nudges >= MAX_NUDGES:
        _emit(root, violation_event, {"nudges": nudges})
        return False
    st["nudges"] = nudges + 1
    _save_state(root, st)
    _emit(root, "adherence_nudge", {"nudge": st["nudges"]})
    return True


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
        _emit_stdout(_context_json("SessionStart",
                     "[Cypher Tempre] DORMANT (paused): self-model loop is off until "
                     "the skill's dormancy.py 'resume' command."))
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
    _emit_stdout(_context_json(
        "SessionStart",
        "[Cypher Tempre] ACTIVE — you wear a Timechain self-model. " + verify_line +
        f"head at ring {head}. "
        "EVERY meaningful turn runs the loop (enforced): verify -> immune-screen -> recall "
        "relevant rings -> reason via modalities/senses -> PoQ-gate -> seal a labeled ring. "
        "Do the loop in one step with the skill's recall.py 'turn' command (exact invocation in "
        "SKILL.md / AGENTS.md). "
        "Covenant: accurate, coherent, persistent, honest, thorough; never assert beyond grounding; "
        "size/horizon are never refusal reasons. Spawned subagents must wear the skill too "
        "(use the cypher-tempre-agent type or forge their own chain and seal)."))


def cmd_codex_notify(argv):
    """Codex/OpenClaw turn-end via the `notify` program (fire-and-forget — CANNOT
    block). So this OBSERVES rather than enforces: it records whether the turn
    advanced the identity chain (a recall.py turn seal) or the active audit chain
    (audit.py record) since the previous turn end. The real continuation lever on
    these platforms is the AGENTS.md / SOUL.md standing instruction; this gives the
    adherence view honest per-platform telemetry. The event JSON Codex appends is
    the last argv element (parsed best-effort; we never depend on its schema)."""
    root = _root_from({})
    if _dormant(root):
        return
    evt = {}
    if argv:
        try:
            evt = json.loads(argv[-1])
        except Exception:
            evt = {}
    st = _load_state(root)
    head = _head_index(root)
    ar = _active_audit_root(root)
    audit_head = _head_index(ar) if ar else None
    last_head = st.get("last_turn_end_head")
    last_audit = st.get("last_turn_end_audit_head")
    st["last_turn_end_head"] = head
    st["last_turn_end_audit_head"] = audit_head
    _save_state(root, st)
    _emit(root, "adherence_turn_end", {"type": evt.get("type"), "head": head})
    if last_head is None and last_audit is None:
        return  # first observation = baseline only
    progressed = (head > (last_head if last_head is not None else head)) or \
                 (audit_head is not None and last_audit is not None and audit_head > last_audit)
    if progressed:
        _emit(root, "adherence_satisfied", {"via": "codex-notify", "head": head})
    else:
        _emit(root, "adherence_nudge", {"via": "codex-notify", "head": head})


HANDLERS = {
    "mark": cmd_mark,
    "user-prompt": cmd_user_prompt,
    "stop-check": cmd_stop_check,
    "subagent-check": cmd_subagent_check,
    "session-start": cmd_session_start,
    "codex-notify": cmd_codex_notify,
}

# Handlers that read the event from ARGV (not stdin): Codex's notify appends the
# event JSON as a trailing CLI argument rather than piping it.
ARGV_HANDLERS = {"codex-notify"}


def main(argv=None):
    _STDOUT.clear()
    # CT_ENFORCE_DEBUG re-enables diagnostics: warnings are NOT silenced and a
    # handler exception prints a traceback — all to stderr, never to the parsed
    # stdout. The hook wrappers stop redirecting stderr to /dev/null in this mode,
    # so a future field issue is debuggable instead of silent.
    _debug = _env_enabled("CT_ENFORCE_DEBUG")
    if not _debug:
        try:
            import warnings
            warnings.filterwarnings("ignore")   # a warning must never reach the parsed stream
        except Exception:
            pass
    argv = argv if argv is not None else sys.argv[1:]
    cmd = argv[0] if argv else ""
    handler = HANDLERS.get(cmd)
    if not handler:
        sys.stderr.write("usage: enforce.py {mark|user-prompt|stop-check|subagent-check|session-start|codex-notify}\n")
        return 0  # unknown -> no-op, never fail a hook
    # Quarantine ALL incidental stdout (import chatter, stray prints) to stderr;
    # only what a handler queues via _emit_stdout reaches the real stdout, so the
    # decision the harness parses is never corrupted.
    real_out = sys.stdout
    try:
        sys.stdout = sys.stderr
        if cmd in ARGV_HANDLERS:
            handler(argv[1:])
        else:
            handler(_read_stdin())
    except Exception:
        # FAIL-OPEN: never break the session. Surface the cause only when the
        # operator opts in, and only on stderr — never the parsed stdout.
        if _debug:
            import traceback
            traceback.print_exc(file=sys.stderr)
    finally:
        sys.stdout = real_out
    if _STDOUT:
        try:
            real_out.write("".join(_STDOUT))   # the ONLY thing on the real stdout
            real_out.flush()
        except Exception:
            pass
        finally:
            _STDOUT.clear()
    return 0


if __name__ == "__main__":
    sys.exit(main())
