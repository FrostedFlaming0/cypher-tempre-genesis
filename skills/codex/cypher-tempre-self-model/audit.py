#!/usr/bin/env python3
# Copyright (c) 2026 cyberphysicsai. MIT License.
"""Audit — an exhaustive-review coverage governor on top of Continuum.

THE PROBLEM THIS FIXES. Continuum guarantees that a corpus larger than any
context window gets *ingested* into a navigable, resumable chain. It does NOT
prove the model has *semantically reviewed* every block. So on a "read every
line / no corners / full audit" task, a model walks the repo (ingest = 100%),
does a seductive round of high-risk *retrieval* + grep, writes a "Final Report",
and stops — converting an EXHAUSTIVE audit into a TARGETED one without noticing.
Field-observed on Firefox (46,866 blocks ingested, a few dozen reviewed) and,
honestly, on this skill's own Bitcoin Core chain (2,525 files / 8,196 blocks
ingested, "findings" that were really `X lines, Y defs, Z classes` structural
metadata — not review).

THE GOVERNOR. This module separates INGEST coverage from REVIEW coverage and
drives completion off an unreviewed-block queue:

  audit.py open      --root <chain> --objective "..."   # init review ledger over an ingested chain
  audit.py next      --root <chain> --batch-size N       # hand back the next UNREVIEWED blocks to read
  audit.py record    --root <chain> --block I... (--finding "..." | --clean)
  audit.py progress  --root <chain>                      # reviewed blocks/files/lines vs total
  audit.py validate  --root <chain> [--require-complete] # PROVE every in-scope block has a review record
  audit.py report    --root <chain> [--final]            # refuses "FINAL" below 100% — labels "INTERIM"

DESIGN. The hot path (progress, the enforce.py turn-end governor) reads an O(1),
*bounded* audit sub-state from the head block (reviewed counts + recent findings).
The queue and final proof stream the chain, rebuild the reviewed set from sealed
`audit_review` rings, and compare it against the in-scope continuum blocks. That
means out-of-order reviews do not strand missed blocks, and the final report never
rests on a sequential assumption.

Stdlib only. Python 3.8+. Companion to continuum.py / timechain.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from timechain import Timechain

# Roles that are NOT authored source lines, so excluded from "every line" by
# default. Override with --roles / --exclude-roles at `open`.
DEFAULT_EXCLUDE_ROLES = {"generated", "vendor"}
RECENT_FINDINGS_CAP = 8           # bounded recent-findings window in the head state


# The enforce.py audit governor reads this pointer (next to the skill's own chain)
# to know which task chain is under active review. Set on `open`, cleared on
# completion or `close`.
def _pointer_path():
    # The pointer lives in the enforce.py namespace so the governor finds it at
    # the same root it reads: CT_ENFORCE_ROOT if set (also keeps selftest
    # hermetic), else the skill dir.
    import os
    base = os.environ.get("CT_ENFORCE_ROOT")
    root = Path(base) if base else Path(__file__).resolve().parent
    return root / "chain" / ".active_audit"


def _set_active(root):
    try:
        p = _pointer_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"root": str(Path(root).resolve())}))
    except Exception:
        pass


def _clear_active(root=None):
    try:
        p = _pointer_path()
        if not p.is_file():
            return
        if root is None:
            p.unlink()
            return
        cur = (json.loads(p.read_text()) or {}).get("root")
        if cur and Path(cur).resolve() == Path(root).resolve():
            p.unlink()
    except Exception:
        pass


def _is_continuum_block(payload):
    return (payload or {}).get("event") == "continuum" and "data" in (payload or {})


def _block_lines(data):
    try:
        return max(0, int(data["line_end"]) - int(data["line_start"]) + 1)
    except Exception:
        return 0


def _in_scope(data, scope):
    role = data.get("path_role")
    if role in set(scope.get("exclude_roles") or ()):
        return False
    roles = scope.get("roles")
    if roles and role not in set(roles):
        return False
    return True


class Audit:
    def __init__(self, root):
        self.tc = Timechain(root)
        self.root = Path(root)

    # -- state -------------------------------------------------------------- #
    def _head_state(self):
        """The most recent full task state (continuum metrics + any audit
        sub-state), read O(1) from the tail, with bounded fallbacks."""
        last = self.tc._tail_ring()
        if last:
            st = (last.get("payload") or {}).get("state")
            if st:
                return st
        for r in reversed(self.tc.tail_rings(256)):
            st = (r.get("payload") or {}).get("state")
            if st:
                return st
        latest = None
        for r in self.tc.iter_rings():
            st = (r.get("payload") or {}).get("state")
            if st:
                latest = st
        return latest

    def status(self):
        """Bounded O(1) audit status from the head block (None if no audit open)."""
        st = self._head_state()
        return (st or {}).get("audit")

    def _review_sets(self, scope):
        """Return (in_scope, reviewed) index sets by streaming the chain."""
        in_scope, reviewed = set(), set()
        for r in self.tc.iter_rings():
            p = r.get("payload") or {}
            if _is_continuum_block(p) and _in_scope(p["data"], scope):
                in_scope.add(r["index"])
            elif p.get("event") == "audit_review":
                for i in (p.get("data") or {}).get("reviewed_indices", []):
                    try:
                        reviewed.add(int(i))
                    except (TypeError, ValueError):
                        continue
        return in_scope, reviewed & in_scope

    # -- open --------------------------------------------------------------- #
    def open(self, objective=None, roles=None, exclude_roles=None, difficulty=0):
        st = self._head_state()
        if st is None:
            raise RuntimeError("No continuum task on this chain — run `continuum.py walk` first.")
        scope = {"roles": list(roles) if roles else None,
                 "exclude_roles": list(exclude_roles) if exclude_roles is not None
                 else sorted(DEFAULT_EXCLUDE_ROLES)}
        # One-time O(n) census of the in-scope reviewable blocks.
        total_blocks = total_lines = 0
        for r in self.tc.iter_rings():
            p = r.get("payload") or {}
            if _is_continuum_block(p) and _in_scope(p["data"], scope):
                total_blocks += 1
                total_lines += _block_lines(p["data"])
        if total_blocks == 0:
            raise RuntimeError("No in-scope continuum blocks found — check --roles/--exclude-roles "
                               "or ingest the corpus first.")
        st = json.loads(json.dumps(st))   # deep copy; preserve continuum metrics
        st["audit"] = {
            "objective": objective or st.get("objective"),
            "scope": scope,
            "total_blocks": total_blocks,
            "total_lines": total_lines,
            "review_cursor": 0,            # reviewed in-scope block count (bounded)
            "review_high_water": -1,       # legacy/non-authoritative max reviewed ring
            "reviewed_blocks": 0,
            "reviewed_lines": 0,
            "deep_reviews": 0,             # records whose finding cites specifics (depth >= floor)
            "shallow_reviews": 0,          # bare "clean"/hollow records — coverage without depth
            "findings_total": 0,
            "recent_findings": [],
            "complete": False,
            "next_action": f"audit.py next  (0/{total_blocks} blocks reviewed)",
        }
        ring = self.tc.seal("audit_open",
                            {"event": "audit_open", "objective": st["audit"]["objective"],
                             "state": st}, difficulty=difficulty)
        _set_active(self.root)        # engage the enforce.py turn-end governor
        return st["audit"], ring

    # -- next --------------------------------------------------------------- #
    def next_batch(self, batch_size=10):
        st = self._head_state()
        a = (st or {}).get("audit")
        if not a:
            raise RuntimeError("No audit open — run `audit.py open` first.")
        scope = a["scope"]
        _, reviewed = self._review_sets(scope)
        out = []
        for r in self.tc.iter_rings():
            if r["index"] in reviewed:
                continue
            p = r.get("payload") or {}
            if _is_continuum_block(p) and _in_scope(p["data"], scope):
                d = p["data"]
                out.append({"index": r["index"], "path": d.get("relative_path"),
                            "line_start": d.get("line_start"), "line_end": d.get("line_end"),
                            "chunk": f"{d.get('chunk_index')}/{d.get('chunk_of')}",
                            "content": d.get("content", "")})
                if len(out) >= batch_size:
                    break
        return out, a

    # -- record ------------------------------------------------------------- #
    # Maximum blocks a single --clean call can cover. Prevents batch-skipping.
    # A model that records 50 blocks as --clean in one call did not read them.
    MAX_CLEAN_BATCH = 1
    # Maximum blocks per finding call. Findings require reading, but even so,
    # recording more than this in one call means some blocks were skimmed.
    MAX_FINDING_BATCH = 5
    # Minimum finding length (chars) to count as DEEP. Below this, the finding
    # is too thin to prove the model read the code.
    MIN_DEEP_FINDING_LEN = 60

    def record(self, indices, finding=None, clean=False, status="reviewed", difficulty=0):
        st = self._head_state()
        if st is None or "audit" not in st:
            raise RuntimeError("No audit open — run `audit.py open` first.")
        st = json.loads(json.dumps(st))
        a = st["audit"]
        idxset = set(int(i) for i in indices)
        if not idxset:
            raise RuntimeError("No block indices supplied.")

        in_scope, reviewed_before = self._review_sets(a["scope"])
        invalid = sorted(idxset - in_scope)
        if invalid:
            raise RuntimeError("Block index(es) are not reviewable in-scope continuum blocks: "
                               + ", ".join(str(i) for i in invalid))

        # --- Anti-skipping guards ---
        # GAP 1 FIX: --clean is a model-asserted escape hatch. Limit batch size
        # so the model cannot record 50 unread blocks in one call.
        if clean and not finding:
            if len(idxset) > self.MAX_CLEAN_BATCH:
                raise RuntimeError(
                    f"--clean batch of {len(idxset)} blocks exceeds MAX_CLEAN_BATCH={self.MAX_CLEAN_BATCH}. "
                    "A --clean assertion means you read the block and found nothing — you cannot "
                    "batch-assert that for multiple blocks without reading them. Record each block "
                    "individually with --clean, or provide a --finding that cites what you read. "
                    "This guard exists because models skip reading on large corpora.")

        # GAP 1 FIX: Even findings have a batch cap — reading 20 blocks at once
        # means some were skimmed, not read line by line.
        if finding and len(idxset) > self.MAX_FINDING_BATCH:
            raise RuntimeError(
                f"Finding batch of {len(idxset)} blocks exceeds MAX_FINDING_BATCH={self.MAX_FINDING_BATCH}. "
                "Reading more than this in one record means some blocks were skimmed. "
                "Split into smaller batches and record each with specific line citations.")

        # GAP 1 FIX: A finding too short to cite specifics is not a deep review.
        # "looks fine" or "mirrors async" is not a line-by-line finding.
        if finding and len(finding) < self.MIN_DEEP_FINDING_LEN:
            raise RuntimeError(
                f"Finding too short ({len(finding)} chars, minimum {self.MIN_DEEP_FINDING_LEN}). "
                "A deep review must cite specific lines/symbols and articulate what was found. "
                "Short findings like 'looks fine' or 'mirrors async version' are shallow passes "
                "that skip reading. Cite the file, line range, and what you observed.")

        new_idxs = idxset - reviewed_before
        new_lines, paths = 0, []
        for r in self.tc.iter_rings():
            if r["index"] not in idxset:
                continue
            p = r.get("payload") or {}
            if r["index"] in new_idxs:
                new_lines += _block_lines(p["data"])
            paths.append(p["data"].get("relative_path"))
        newly = len(new_idxs)
        reviewed_after = reviewed_before | idxset
        a["review_cursor"] = len(reviewed_after)
        a["reviewed_blocks"] = len(reviewed_after)
        a["reviewed_lines"] += new_lines
        a["review_high_water"] = max(reviewed_after) if reviewed_after else -1
        # Depth: coverage is not comprehension. A review with a substantive, specific
        # finding (cited lines/symbols, articulated reasoning) is DEEP; a bare clean
        # pass or a hollow "looks fine" is SHALLOW. Classify the NEW blocks this record
        # covers, so `validate --require-depth` can demand reasoning, not just touches.
        depth, floor = 0, 90
        try:
            import modality_ops
            depth = modality_ops.richness(finding or "")["score"]
            floor = modality_ops.RICHNESS_FLOOR
        except Exception:
            pass
        is_deep = bool(finding) and depth >= floor and len(finding) >= self.MIN_DEEP_FINDING_LEN
        if is_deep:
            a["deep_reviews"] = a.get("deep_reviews", 0) + newly
        else:
            a["shallow_reviews"] = a.get("shallow_reviews", 0) + newly
        if finding:
            tag = ", ".join(sorted(set(p for p in paths if p))) or "?"
            a["recent_findings"] = (a["recent_findings"] + [f"{tag}: {finding}"])[-RECENT_FINDINGS_CAP:]
            a["findings_total"] += 1
        a["complete"] = a["review_cursor"] >= a["total_blocks"]
        remaining = max(0, a["total_blocks"] - a["review_cursor"])
        a["next_action"] = ("audit COMPLETE — `audit.py report --final`" if a["complete"]
                            else f"audit.py next  ({a['review_cursor']}/{a['total_blocks']} reviewed, "
                                 f"{remaining} to go)")
        data = {"reviewed_indices": sorted(idxset), "status": status,
                "clean": bool(clean and not finding),
                "finding": finding, "paths": [p for p in paths if p],
                "depth": depth, "deep": is_deep,
                "batch_size": len(idxset)}
        ring = self.tc.seal("audit_review",
                            {"event": "audit_review", "task": (a.get("objective") or "")[:48],
                             "state": st, "data": data}, difficulty=difficulty)
        if a["complete"]:
            _clear_active(self.root)  # coverage reached — stop the governor nagging
        return a, ring, newly

    def close(self):
        """Disengage the governor for this chain (pause/abandon an audit)."""
        _clear_active(self.root)

    # -- validate (rigorous, O(n)) ----------------------------------------- #
    def validate(self, require_complete=False, require_depth=False):
        ok, report = self.tc.verify()
        a = self.status()
        if not a:
            return False, list(report) + ["no audit open on this chain"]
        scope = a["scope"]
        in_scope, reviewed, deep = set(), set(), set()
        for r in self.tc.iter_rings():
            p = r.get("payload") or {}
            if _is_continuum_block(p) and _in_scope(p["data"], scope):
                in_scope.add(r["index"])
            elif p.get("event") == "audit_review":
                d = p.get("data") or {}
                idxs = [int(i) for i in d.get("reviewed_indices", [])]
                reviewed.update(idxs)
                if d.get("deep"):
                    deep.update(idxs)
        reviewed_in_scope = reviewed & in_scope
        deep_in_scope = deep & in_scope
        unreviewed = in_scope - reviewed
        shallow = reviewed_in_scope - deep_in_scope
        pct = (100.0 * len(reviewed_in_scope) / len(in_scope)) if in_scope else 0.0
        dpct = (100.0 * len(deep_in_scope) / len(in_scope)) if in_scope else 0.0
        out = list(report)
        out.append(f"audit objective: {a.get('objective')}")
        out.append(f"in-scope blocks: {len(in_scope)} (roles excl {scope.get('exclude_roles')})")
        out.append(f"reviewed (proven on-chain): {len(reviewed_in_scope)}/{len(in_scope)} = {pct:.2f}%")
        out.append(f"deep reviews (cited specifics): {len(deep_in_scope)}/{len(in_scope)} = {dpct:.2f}%")
        complete = not unreviewed and bool(in_scope)
        depth_complete = complete and not shallow
        if unreviewed:
            out.append(f"UNREVIEWED blocks remain: {len(unreviewed)} (e.g. rings {sorted(unreviewed)[:8]})")
            out.append("resume: `audit.py next` -> read -> `audit.py record`")
        else:
            out.append("every in-scope block has a sealed review record — coverage COMPLETE")
        if require_depth and shallow:
            out.append(f"SHALLOW blocks (reviewed but no substantive finding): {len(shallow)} "
                       f"(e.g. rings {sorted(shallow)[:8]}) — re-review with cited lines/symbols.")
            out.append(f"DEEP reviews: {len(deep_in_scope)} / {len(reviewed_in_scope)} "
                       f"({len(deep_in_scope)/max(1,len(reviewed_in_scope))*100:.0f}%). "
                       f"Shallow reviews do not count as reading the code.")
        passed = ok and (complete if require_complete else True) and (depth_complete if require_depth else True)
        return passed, out

    # -- report ------------------------------------------------------------- #
    # GAP 3 FIX: --final now requires depth by default. A 100%-coverage audit
    # where half the blocks are shallow --clean is not a complete audit.
    # The model must override with --allow-shallow to get a final report with
    # shallow blocks (explicit acknowledgment that it skipped reading).
    def report(self, final=False, require_depth=True, allow_shallow=False):
        if final and not allow_shallow:
            require_depth = True  # force depth check on final reports
        ok, lines = self.validate(require_complete=True, require_depth=require_depth)
        a = self.status() or {}
        bar = "coverage" + (" + depth" if require_depth else "")
        head = []
        if final and ok:
            head.append("===== FINAL AUDIT REPORT =====")
        elif final and not ok:
            head.append(f"===== INTERIM AUDIT REPORT (--final REFUSED: {bar} < 100%) =====")
            head.append("A 'final' report on an incomplete exhaustive audit is a persistence/")
            head.append("covenant miss. Keep going (audit.py next) or state this is interim.")
            if require_depth and not allow_shallow:
                head.append("")
                head.append("NOTE: --final now requires DEPTH by default (every block must have")
                head.append("a cited, specific finding — not just --clean). If you genuinely")
                head.append("need to finalize with shallow reviews, pass --allow-shallow to")
                head.append("acknowledge that you are accepting incomplete reading.")
        else:
            head.append("===== INTERIM AUDIT REPORT =====")
        head.append(f"objective: {a.get('objective')}")
        head.append(f"review coverage: {a.get('review_cursor', 0)}/{a.get('total_blocks', 0)} blocks, "
                    f"~{a.get('reviewed_lines', 0)}/{a.get('total_lines', 0)} lines")
        head.append(f"depth: {a.get('deep_reviews', 0)} deep / {a.get('shallow_reviews', 0)} shallow reviews")
        if a.get('total_blocks', 0) > 0:
            dpct = 100.0 * a.get('deep_reviews', 0) / max(1, a.get('review_cursor', 1))
            head.append(f"depth ratio: {dpct:.0f}% deep (target: 100% for a line-by-line audit)")
        head.append(f"findings recorded: {a.get('findings_total', 0)}")
        if a.get("recent_findings"):
            head.append("recent findings:")
            head += [f"  - {f}" for f in a["recent_findings"]]
        return (final and ok), head + ["", f"--- {bar} proof ---"] + lines


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def cmd_open(args):
    a, ring = Audit(args.root).open(objective=args.objective, roles=args.roles,
                                    exclude_roles=args.exclude_roles)
    print(f"audit opened (Ring {ring['index']}). in-scope: {a['total_blocks']} blocks, "
          f"~{a['total_lines']} lines.")
    print(f"NEXT: {a['next_action']}")


def cmd_next(args):
    blocks, a = Audit(args.root).next_batch(batch_size=args.batch_size)
    if not blocks:
        print(f"no unreviewed in-scope blocks — coverage {a['review_cursor']}/{a['total_blocks']}. "
              "Run `audit.py report --final`.")
        return
    ids = " ".join(str(b["index"]) for b in blocks)
    print(f"# next {len(blocks)} UNREVIEWED block(s) — read every line, then record. A DEEP "
          f"review cites specific lines/symbols; a bare --clean counts as shallow:")
    for b in blocks:
        print(f"\n----- ring {b['index']}  {b['path']}  L{b['line_start']}-{b['line_end']} "
              f"chunk {b['chunk']} -----")
        print(b["content"])
    # friction reducer: a ready-to-fill record scaffold with the block ids pre-filled.
    print(f"\n# record after reading (fill the finding with cited specifics):")
    print(f"#   audit.py record --root {args.root} --block {ids} --finding \"<file:Lstart-Lend — what & why>\"")
    print(f"#   (only if genuinely nothing of note: audit.py record --root {args.root} --block <id> --clean)")
    print(f"#   CAUTION: --clean limited to 1 block/call. Findings limited to 5 blocks/call.")
    print(f"#   Short findings like 'looks fine' or 'mirrors async' will be REJECTED — cite specific lines.")


def cmd_record(args):
    try:
        a, ring, newly = Audit(args.root).record(args.block, finding=args.finding, clean=args.clean,
                                                 status=args.status)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"recorded review of {newly} new block(s) (Ring {ring['index']}). "
          f"coverage {a['review_cursor']}/{a['total_blocks']}.")
    print(f"NEXT: {a['next_action']}")


def cmd_progress(args):
    a = Audit(args.root).status()
    if not a:
        print("no audit open on this chain (run `audit.py open`).")
        sys.exit(1)
    pct = (100.0 * a["review_cursor"] / a["total_blocks"]) if a["total_blocks"] else 0.0
    print(f"objective: {a.get('objective')}")
    print(f"review:    {a['review_cursor']}/{a['total_blocks']} blocks ({pct:.2f}%), "
          f"~{a['reviewed_lines']}/{a['total_lines']} lines")
    print(f"depth:     {a.get('deep_reviews', 0)} deep / {a.get('shallow_reviews', 0)} shallow")
    print(f"findings:  {a['findings_total']}")
    print(f"complete:  {a['complete']}")
    print(f"NEXT:      {a['next_action']}")


def cmd_validate(args):
    ok, lines = Audit(args.root).validate(require_complete=args.require_complete,
                                          require_depth=args.require_depth)
    for ln in lines:
        print("  " + ln)
    print("AUDIT:", "COMPLETE" if ok else "INCOMPLETE")
    sys.exit(0 if ok else 1)


def cmd_close(args):
    Audit(args.root).close()
    print("audit governor disengaged for this chain (pointer cleared).")


def cmd_report(args):
    is_final, lines = Audit(args.root).report(
        final=args.final, require_depth=args.require_depth,
        allow_shallow=args.allow_shallow)
    for ln in lines:
        print(ln)
    # exit nonzero when --final was requested but refused, so scripts/hooks notice
    sys.exit(0 if (is_final or not args.final) else 2)


def build_parser():
    default_root = Path(__file__).resolve().parent
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", type=Path, default=default_root,
                        help="task chain root (the per-task dir you walked with continuum.py)")
    p = argparse.ArgumentParser(description="Audit — exhaustive-review coverage governor over Continuum.")
    sub = p.add_subparsers(dest="cmd", required=True)

    po = sub.add_parser("open", parents=[common], help="init a review ledger over an ingested chain")
    po.add_argument("--objective", default=None)
    po.add_argument("--roles", nargs="*", default=None,
                    help="only these path roles count as reviewable (e.g. source config)")
    po.add_argument("--exclude-roles", nargs="*", default=None,
                    help=f"roles to exclude (default {sorted(DEFAULT_EXCLUDE_ROLES)})")
    po.set_defaults(func=cmd_open)

    pn = sub.add_parser("next", parents=[common], help="hand back the next UNREVIEWED blocks to read")
    pn.add_argument("--batch-size", type=int, default=10)
    pn.set_defaults(func=cmd_next)

    pr = sub.add_parser("record", parents=[common], help="seal a review record for block(s) you read")
    pr.add_argument("--block", nargs="+", type=int, required=True, help="ring index(es) just reviewed")
    prx = pr.add_mutually_exclusive_group(required=True)
    prx.add_argument("--finding", default=None, help="a real finding (omit + use --clean if nothing)")
    prx.add_argument("--clean", action="store_true",
                     help="reviewed, nothing of note. LIMITED TO 1 BLOCK PER CALL to prevent batch-skipping. "
                          "You must have actually read the block's content first.")
    pr.add_argument("--status", default="reviewed")
    pr.set_defaults(func=cmd_record)

    pp = sub.add_parser("progress", parents=[common], help="O(1) coverage from the head block")
    pp.set_defaults(func=cmd_progress)

    pv = sub.add_parser("validate", parents=[common], help="PROVE coverage by streaming the chain")
    pv.add_argument("--require-complete", action="store_true", help="fail unless 100%% reviewed")
    pv.add_argument("--require-depth", action="store_true",
                    help="fail unless every reviewed block has a DEEP record (cited specifics)")
    pv.set_defaults(func=cmd_validate)

    prp = sub.add_parser("report", parents=[common], help="audit report (refuses FINAL below 100%%)")
    prp.add_argument("--final", action="store_true", help="request a FINAL report (refused if incomplete or shallow)")
    prp.add_argument("--require-depth", action="store_true",
                     help="require depth-complete (no shallow reviews). DEFAULT for --final since v3.8.3.")
    prp.add_argument("--allow-shallow", action="store_true",
                     help="allow --final to pass with shallow reviews (explicit acknowledgment of incomplete reading)")
    prp.set_defaults(func=cmd_report)

    pc = sub.add_parser("close", parents=[common], help="disengage the turn-end governor (pause/abandon)")
    pc.set_defaults(func=cmd_close)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
