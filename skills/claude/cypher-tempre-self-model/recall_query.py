#!/usr/bin/env python3
"""recall_query - Layer 3 facade: the question path (v3.14).

The recall ladder for QUESTIONS against an existing chain: grep -> retrieve
-> fan-out -> gather/track. See recall_core for the seal path.

    from recall_query import Recall
    r = Recall(root, None)   # .grep / .retrieve / .gather / .track surfaces
"""
from recall import Recall                                     # noqa: F401
