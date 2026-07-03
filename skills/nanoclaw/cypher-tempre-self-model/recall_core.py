#!/usr/bin/env python3
"""recall_core - Layer 3 facade: the seal path (v3.14).

First step of the recall.py decomposition (self-audit: 2,540 lines mixing
four modules). The facades give each concern a stable import surface NOW so
callers migrate first and the physical split can land without breaking
anyone: recall_core (label/seal/loop), recall_query (grep/retrieve/gather),
recall_evidence (evidence assembly). recall.py remains the implementation
home until the physical split completes.

    from recall_core import Recall, loop_seal
"""
from recall import Recall, _loop_seal as loop_seal            # noqa: F401
