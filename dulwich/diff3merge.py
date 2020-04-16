#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""
Implementation of a diff3 approach to perform a 3-way merge
"""

# Implementation of using a diff3 approach to perform a 3-way merge
# In Python3
#
# Based on the wonderful blog, "The If Works", by James Coglin
# See: https://blog.jcoglan.com/2017/05/08/merging-with-diff3/
#
# Copyright (c) 2020 Kevin B. Hendricks, Stratford Ontario Canada
#
# Available under the MIT License

import sys
# import os

from difflib import diff_bytes, ndiff
from .myersdiff import myers_diff


def do_file_merge_myers(alice, bob, ancestor):
    """Merge alice and bob based on their common ancestor
       Uses Myers diff to perform matching
       Args:
           alice     - bytestring contents of a file to merge
           bob       - bytestring contents of another file to merge
           ancestor  - bytestring contents of ancestor common to alice and bob
           diff_type - 'myers' or 'ndiff' diff implementation to use
                       default is 'myers'
       Returns:
           tuple of bytestring result of merge of alice with bob and
           list of any conflicts
    """
    mrg3 = Merge3Way(ancestor, alice, bob, "myers")
    res = mrg3.merge()
    conflicts = mrg3.get_conflicts()
    return (res, conflicts)

def do_file_merge_ndiff(alice, bob, ancestor):
    """Merge alice and bob based on their common ancestor
       Uses difflib's ndiff (patience diff) to perform matching
       Args:
           alice     - bytestring contents of a file to merge
           bob       - bytestring contents of another file to merge
           ancestor  - bytestring contents of ancestor common to alice and bob
           diff_type - 'myers' or 'ndiff' diff implementation to use
                       default is 'myers'
       Returns:
           bytestring result of merge of alice with bob with conflicts marked
    """
    mrg3 = Merge3Way(ancestor, alice, bob, "ndiff")
    res = mrg3.merge()
    conflicts = mrg3.get_conflicts()
    return (res, cconflicts)


class Merge3Way(object):
    """class to perform a 3 way merge of alice and bob based
       on their common ancestor
    """

    def __init__(self, ancestor, alice, bob, diff_type):
        """ Merge3Way init
           Args:
               ancestor  - btyestring of common ancestor to alice and bob
               alice     - bytestring to be merged with bob
               bob       - bytestring to be merged with alice
               diff_type - type of diff to use "myers" or "ndiff"
           Returns:
               instance of Merge3Way class
        """
        self.o_file = b'ancestor'
        self.a_file = b'alice'
        self.b_file = b'bob'
        self.o_lines = ancestor.splitlines(keepends=True)
        self.a_lines = alice.splitlines(keepends=True)
        self.b_lines = bob.splitlines(keepends=True)
        self.conflicts = []
        if diff_type in ('myers', 'Myers', 'MYERS',
                         b'myers', b'Myers', b'MYERS'):
            self.a_matches = self._myers_matches(self.o_lines, self.a_lines)
            self.b_matches = self._myers_matches(self.o_lines, self.b_lines)
        else:
            self.a_matches = self._ndiff_matches(self.o_lines, self.a_lines)
            self.b_matches = self._ndiff_matches(self.o_lines, self.b_lines)
        self.chunks = []
        self.on, self.an, self.bn = 0, 0, 0

    def get_conflicts(self):
        """ Returns list of conflicts if any from merge
            where each conflict is a tuple of ranges of line numbers
            that conflict in ancestor, alice, and then bob respectively
            ((ancestor begin, end), (alice begin,end) (bob begin, end))
        """
        return self.conflicts

    def _ndiff_matches(self, olines, dlines):
        """ Uses difflib's ndiff to find matching lines
            in ancestor and alice or bob
            Args:
               olines - list of bytestrings of ancestor
               dlines - list of bytestrings of either alice or bob
            Returns:
               dictionary mapping matching line numbers in ancestor to other
        """
        on, dn = 0, 0
        matches = {}

        # See difflib.diff_bytes documentation
        # https://docs.python.org/3/library/difflib.html
        # Use this dfunc to allow ndiff to work on mixed or unknown encoded
        # byte strings
        def do_ndiff(alines, blines, fromfile, tofile, fromfiledate,
                     tofiledate, n, lineterm):
            return ndiff(alines, blines, linejunk=None, charjunk=None)

        for line in diff_bytes(do_ndiff, olines, dlines, b'ancestor', b'other',
                               b' ', b' ', n=-1, lineterm=b'\n'):
            dt = line[0:2]
            if dt == b'  ':
                on += 1
                dn += 1
                matches[on] = dn
            elif dt == b'+ ':
                dn += 1
            elif dt == b'- ':
                on += 1
        return matches

    def _myers_matches(self, olines, dlines):
        """ Uses myers diff implementation to find matching lines
            in ancestor and alice or bob
            Args:
               olines - list of bytestrings of ancestor
               dlines - list of bytestrings of either alice or bob
            Returns:
               dictionary mapping matching line numbers in ancestor to other
        """
        on, dn = 0, 0
        matches = {}
        for line in myers_diff(olines, dlines):
            dt = line[0:2]
            if dt == b'  ':
                on += 1
                dn += 1
                matches[on] = dn
            elif dt == b'+ ':
                dn += 1
            elif dt == b'- ':
                on += 1
        return matches

    def _generate_chunks(self):
        """ generate a list of chunks where each chunk represents
            either of matching region or non-matching region
            across alice, ancestor, and bob
        """
        while(True):
            i = self._find_next_mismatch()
            if i is None:
                self._emit_final_chunk()
                return
            if i == 1:
                o, a, b = self._find_next_match()
                if a and b:
                    self._emit_chunk(o, a, b)
                else:
                    self._emit_final_chunk()
                    return
            elif i:
                self._emit_chunk(self.on + i, self.an + i, self.bn + i)

    def _inbounds(self, i):
        """Determine if current offset i is within any of the 3 files"""
        if (self.on + i) <= len(self.o_lines):
            return True
        if (self.an + i) <= len(self.a_lines):
            return True
        if (self.bn + i) <= len(self.b_lines):
            return True
        return False

    def _ismatch(self, matchdict, offset, i):
        """Using matchdict to determine line in ancestor exists
           in alice/bob at offset """
        if (self.on + i) in matchdict:
            return matchdict[self.on + i] == offset + i
        return False

    def _find_next_mismatch(self):
        """Walk chunks to find next mismatched chunk"""
        i = 1
        while self._inbounds(i) and \
                self._ismatch(self.a_matches, self.an, i) and \
                self._ismatch(self.b_matches, self.bn, i):
            i += 1
        if self._inbounds(i):
            return i
        return None

    def _find_next_match(self):
        """Find next chunk that matches across ancestor, alice, and bob"""
        ov = self.on + 1
        while(True):
            if ov > len(self.o_lines):
                break
            if (ov in self.a_matches and ov in self.b_matches):
                break
            ov += 1
        av = bv = None
        if ov in self.a_matches:
            av = self.a_matches[ov]
        if ov in self.b_matches:
            bv = self.b_matches[ov]
        return (ov, av, bv)

    def _write_chunk(self, o_range, a_range, b_range):
        """Output merged chunk of the given ranges"""
        oc = b''.join(self.o_lines[o_range[0]:o_range[1]])
        ac = b''.join(self.a_lines[a_range[0]:a_range[1]])
        bc = b''.join(self.b_lines[b_range[0]:b_range[1]])
        if oc == ac and oc == bc:
            self.chunks.append(oc)
        elif oc == ac:
            self.chunks.append(bc)
        elif oc == bc:
            self.chunks.append(ac)
        else:
            # conflict
            self.conflicts.append((o_range, a_range, b_range))
            cc = b'<<<<<<< ' + self.a_file + b'\n'
            cc += ac
            cc += b'======= \n'
            cc += bc
            cc += b'>>>>>>> ' + self.b_file + b'\n'
            self.chunks.append(cc)

    def _emit_chunk(self, o, a, b):
        """Emit chunk at offsets o, a, b in ancestor, alice, and bob"""
        self._write_chunk((self.on, o-1),
                          (self.an, a-1),
                          (self.bn, b-1))
        self.on, self.an, self.bn = o - 1, a - 1, b - 1

    def _emit_final_chunk(self):
        """Write out any remaining chunks"""
        self._write_chunk((self.on, len(self.o_lines)+1),
                          (self.an, len(self.a_lines)+1),
                          (self.bn, len(self.b_lines)+1))

    def merge(self):
        """Perform 3 way merge"""
        self._generate_chunks()
        res = b''.join(self.chunks)
        return res


def main():
    """Perform 3-Way Merge of Alice and Bob using a common Ancestor
          Args:
            ancestor_path - path to ancestor file
            alice_path    - path to alice file
            bob_path      - path to bob file
            diff_type     - "myers" or "ndiff"
          Prints output of 3 way merge with any conflicts marked
    """
    argv = sys.argv
    if len(argv) < 5:
        print("diff3merge ancestor_path alice_path bob_path myers|ndiff")
    ofile = argv[1]
    afile = argv[2]
    bfile = argv[3]
    dtype = argv[4]
    with open(ofile, 'rb') as of:
        ancestor = of.read()
    with open(afile, 'rb') as af:
        alice = af.read()
    with open(bfile, 'rb') as bf:
        bob = bf.read()
    res = do_file_merge(alice, bob, ancestor, dtype)
    print(res.decode('utf-8'), end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
