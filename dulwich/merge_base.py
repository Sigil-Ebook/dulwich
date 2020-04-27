#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""
Implementation of merge-base following the approach of git
"""
# Copyright (c) 2020 Kevin B. Hendricks, Stratford Ontario Canada
#
# Available under the MIT License

import sys
from collections import deque

from dulwich.objects import Commit
from dulwich.repo import (BaseRepo, Repo)

def _find_lcas(r, c1, c2s):
    cands = []
    cstates = {}

    # Flags to Record State
    _ANC_OF_1 = 1  # ancestor of commit 1
    _ANC_OF_2 = 2  # ancestor of commit 2
    _DNC = 4       # Do Not Consider
    _LCA = 8       # potential LCA

    def _has_candidates(wlst, cstates):
        for cmt in wlst:
            if cmt.id in cstates:
                if not (cstates[cmt.id] & _DNC):
                    return True
        return False

    # initialize the working list
    wlst = deque()
    cstates[c1.id] = _ANC_OF_1
    wlst.append(c1)
    for c2 in c2s:
        cstates[c2.id] = _ANC_OF_2       
        wlst.append(c2)

    # loop until no other LCA candidates are viable in working list
    # adding any parents to the list in a breadth first manner
    while _has_candidates(wlst, cstates):
        cmt = wlst.popleft()
        flags = cstates[cmt.id]
        if flags == (_ANC_OF_1 | _ANC_OF_2):
            # potential common ancestor
            if not (flags & _LCA):
                flags = flags | _LCA
                cstates[cmt.id] = flags
                cands.append(cmt)
                # mark any parents of this node _DNC as all parents
                # would be one level further removed common ancestors
                flags = flags | _DNC
        if cmt.parents:
            for parent in cmt.parents:
                pcmt = r[parent]
                if pcmt.id in cstates:
                    cstates[pcmt.id] = cstates[pcmt.id] | flags
                else:
                    cstates[pcmt.id] = flags
                wlst.append(pcmt)

    # walk final candidates removing any superceded by _DNC by later lower LCAs
    results = []
    for cmt in cands:
        if not (cstates[cmt.id] & _DNC):
            results.append(cmt.id)
    return results

def find_merge_base(r, commits):
    """ find lowest common ancestors of commit[0] and any of commits[1:]
       ARGS
          r - Repo object
          commits - list of Commit objects
       Returns
          list of LCA commit ids
    """
    c1 = commits[0]
    c2s = commits[1:]
    if not c2s or len(c2s) == 0:
        return [c1.id]
    if c1 in c2s:
        return [c1.id]
    return _find_lcas(r, c1, c2s)
