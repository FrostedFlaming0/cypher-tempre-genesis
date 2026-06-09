#!/usr/bin/env python3
"""
Self-test — exercise all eleven mechanisms end-to-end on a throwaway chain and assert the
core invariants. Run from the skill directory:  python3 selftest.py
Exit 0 = all green. Stdlib only.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import timechain, poq, cambium, chronosynaptic, continuum, recall, consensus, immune, embed, hippocampus, dormancy

SKILL = Path(__file__).resolve().parent
_ok = True


def check(name, cond):
    global _ok
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    _ok = _ok and bool(cond)


def main():
    root = Path(tempfile.mkdtemp(prefix="ct_selftest_"))
    shutil.copytree(SKILL / "registry", root / "registry")   # faculties for cambium/chronosynaptic
    try:
        # 1. Timechain — genesis + verify
        tc = timechain.Timechain(root)
        tc.genesis(name="selftest")
        check("timechain: genesis sealed", tc.height() == 1)

        # 2. PoQ — gate + seal a grounded thought
        verdict, ring = poq.gate_and_seal(
            tc, "I verified my selftest chain and this grounded note is consistent with it.",
            context="selftest",
            external_scores={"coherence": 220, "relevance": 225, "novelty": 180,
                             "consistency": 220, "depth": 205, "covenant": 245})
        check("poq: sealed a ring", ring is not None)
        check("timechain: chain verifies", tc.verify()[0])

        # 3. Cambium — dissonance on a foreign input
        corpus = cambium.load_corpus(SKILL)
        gap = cambium.detect_gap(corpus, "quaternion slerp gimbal kinematics actuator torque encoder")
        check("cambium: detects dissonance on foreign input", gap["dissonance"] > 100)

        # 4. Continuum — ingest + task-aware validate
        c = continuum.Continuum(root)
        c.open_task("selftest task", items_total=1)
        sealed, _ = c.ingest("doc", "alpha beta gamma\n" * 80, finding="x")
        check("continuum: ingested data-height blocks", len(sealed) >= 1)
        check("continuum: coherent", c.validate()[0])

        # 4b. Codebase cartography — relative paths, line ranges, chunk ids, file hashes.
        code_root = root / "sample-code"
        (code_root / "src" / "wallet").mkdir(parents=True)
        (code_root / "src" / "net_processing").mkdir(parents=True)
        (code_root / "tests").mkdir(parents=True)
        secret = "sk-proj-" + ("A" * 40)
        (code_root / "src" / "wallet" / "main.py").write_text(
            ("wallet alpha spend coin\n" * 900) + f"OPENAI_API_KEY={secret}\n"
        )
        (code_root / "src" / "net_processing" / "peer.py").write_text("network peer relay message\n" * 120)
        (code_root / "tests" / "test_wallet.py").write_text("wallet alpha test fixture\n" * 80)
        c2 = continuum.Continuum(root)
        _, walked = c2.walk(code_root, (".py",), "cartography selftest")
        check("continuum: walked nested code paths", len(walked) == 3)
        wallet_blocks = [
            r for r in c2.tc.load()
            if r.get("payload", {}).get("data", {}).get("relative_path") == "src/wallet/main.py"
        ]
        wd = wallet_blocks[0]["payload"]["data"] if wallet_blocks else {}
        check("continuum: stores relative_path not basename", wd.get("relative_path") == "src/wallet/main.py")
        check("continuum: stores file/chunk indices", wd.get("file_index") and wd.get("chunk_index") and wd.get("chunk_of"))
        check("continuum: stores line range", wd.get("line_start") == 1 and wd.get("line_end") >= wd.get("line_start"))
        check("continuum: stores path metadata", wd.get("top_dir") == "src" and wd.get("extension") == ".py" and wd.get("language") == "python")
        check("continuum: stores path role", wd.get("path_role") == "source" and wd.get("is_test") is False)
        check("continuum: stores git/hash metadata", "git_commit" in wd and len(wd.get("content_hash", "")) == 64)
        check("continuum: separates chunk and file hashes",
              len(wd.get("file_content_hash", "")) == 64 and wd.get("content_hash") != wd.get("file_content_hash"))
        redacted = [
            r for r in wallet_blocks
            if r.get("payload", {}).get("data", {}).get("redacted")
        ]
        check("continuum: redacts secrets before sealing",
              redacted and secret not in redacted[0]["payload"]["data"]["content"])
        c3 = continuum.Continuum(root)
        _, changed = c3.walk(code_root, (".py",), "cartography changed-only", changed_only=True)
        check("continuum: changed-only skips unchanged files", len(changed) == 0)

        # 5. Recall — self-label + retrieve (lexical and embedding)
        rec = recall.Recall(root, registry_root=SKILL)
        lab = rec.label("proof of work difficulty target")
        check("recall: produces labels", "keywords" in lab and lab["keywords"])
        check("recall: retrieve runs", "blocks" in rec.retrieve("alpha beta", embed=False))
        check("recall: embedding retrieve runs", "blocks" in rec.retrieve("alpha beta", embed=True))
        carto = rec.retrieve("wallet alpha", path="src/wallet/main.py", role="source", max_blocks=1, neighbors=1)
        check("recall: path filter returns matching path",
              carto["blocks"] and carto["blocks"][0]["location"]["relative_path"] == "src/wallet/main.py")
        check("recall: excerpt is source text not metadata",
              carto["blocks"] and carto["blocks"][0]["excerpt"].startswith("wallet alpha"))
        check("recall: returns neighboring chunks around a hit",
              bool(carto["blocks"][0].get("neighbors")))
        test_hit = rec.retrieve("wallet alpha", role="test", max_blocks=1, neighbors=0)
        check("recall: role filter can target tests",
              test_hit["blocks"] and test_hit["blocks"][0]["location"]["path_role"] == "test")
        source_check = rec.verify_source(code_root, carto["blocks"][0]["index"])
        check("recall: source validation verifies current file", source_check["verdict"] == "verified")

        # 6. Embed — morphology beats unrelated
        e = embed.get_embedder("hashing")
        rel = embed.cosine(e.embed("validate a block"), e.embed("block validation"))
        unrel = embed.cosine(e.embed("validate a block"), e.embed("fee wallet policy"))
        check("embed: morphology > unrelated", rel > unrel)

        # 7. Chronosynaptic — fork + collapse
        tree = chronosynaptic.ChronosynapticTree(root, iterations=6, forks=3, max_depth=2)
        node = tree.search("what should the agent do next", "selftest")
        result, _ = tree.collapse_and_seal(node, "what next", "selftest", do_seal=False)
        check("chronosynaptic: collapses to a path", bool(result and result["chosen"]))
        explicit_notes = {
            "query": "audit a staking module",
            "context": "selftest explicit perspectives",
            "perspectives": [
                {
                    "name": "Accounting lens",
                    "kind": "audit",
                    "summary": "Bond share accounting remains internally consistent.",
                    "score": 220,
                    "findings": ["total shares match per-operator shares"],
                },
                {
                    "name": "Queue lens",
                    "kind": "audit",
                    "summary": "Queue accounting needs follow-up invariant execution.",
                    "score": 190,
                    "evidence": ["test/helpers/InvariantAsserts.sol"],
                },
            ],
        }
        explicit, explicit_ring = tree.collapse_explicit_notes(explicit_notes, do_seal=True)
        payload = explicit_ring["payload"] if explicit_ring else {}
        check("chronosynaptic: explicit notes seal a synthesis",
              explicit_ring is not None and payload.get("event") == "chronosynaptic_explicit_collapse")
        check("chronosynaptic: explicit notes choose highest score",
              explicit["chosen"]["name"] == "Accounting lens")
        check("chronosynaptic: explicit notes preserve rejected perspectives",
              len(payload.get("rejected_perspectives", [])) == 1 and
              payload["rejected_perspectives"][0]["name"] == "Queue lens")

        # 8. Consensus — quorum attest + verify
        qu = consensus.Quorum(root)
        qu.init(n=3, quorum=2)
        qu.attest()
        check("consensus: quorum valid", qu.verify()[0])

        # 9. Immune — scan a clean chain
        d = immune.Immune(root).detect()
        check("immune: scan runs, chain clean", d.get("compromised") is False)

        # 10. Hippocampus — persistent, rebuildable, sub-linear recall index (derived from the chain)
        hp = hippocampus.Hippocampus(root)
        built = hp.build()
        check("hippocampus: index builds from chain", built["indexed"] >= 1)
        check("hippocampus: not stale after build", hp.status()["stale"] is False)
        cand = hp.search("wallet alpha")              # 'wallet'/'alpha' live in the cartography blocks above
        check("hippocampus: sub-linear search returns candidates", isinstance(cand, list) and len(cand) >= 1)
        check("hippocampus: index loss does not affect chain integrity", tc.verify()[0])

        # 11. Dormancy — manual pause halts sealing; resume restores it; chain stays intact
        dm = dormancy.Dormancy(root)
        dm.pause(reason="selftest")
        check("dormancy: pause sets dormant state", dm.is_paused())
        check("dormancy: chain still verifies while paused", tc.verify()[0])
        try:
            tc.seal("experience", {"summary": "refused while paused"}); refused = False
        except RuntimeError:
            refused = True
        check("dormancy: seal refused while paused", refused)
        dm.resume()
        check("dormancy: resume clears dormant state", not dm.is_paused())
        check("dormancy: sealing works again after resume", tc.seal("experience", {"summary": "after resume"})["index"] >= 1)

        check("timechain: final verify", tc.verify()[0])
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("\nSELFTEST:", "PASS ✅" if _ok else "FAIL ❌")
    sys.exit(0 if _ok else 1)


if __name__ == "__main__":
    main()
