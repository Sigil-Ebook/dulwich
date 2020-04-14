#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

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
import os

from difflib import diff_bytes, ndiff


def do_file_merge(alice, bob, ancestor):
    mrg3 = Merge3Way(ancestor, alice, bob)
    res = mrg3.merge()
    conflicts = mrg3.get_conflicts()
    return res


class Merge3Way(object):

    def __init__(self, ancestor, alice, bob):
        self.o_file = b'ancestor'
        self.a_file = b'alice'
        self.b_file = b'bob'
        self.o_lines = ancestor.splitlines(keepends=True)
        self.a_lines = alice.splitlines(keepends=True)
        self.b_lines = bob.splitlines(keepends=True)
        self.conflicts = []
        self.a_matches = self.ndiff_matches(self.o_lines, self.a_lines)
        self.b_matches = self.ndiff_matches(self.o_lines, self.b_lines)

        self.chunks = []
        self.on, self.an, self.bn = 0, 0, 0


    def get_conflicts(self):
        return self.conflicts


    # ancestor line number to alice/bob line numbers for matching lines
    def ndiff_matches(self, olines, dlines):
        on, dn = 0, 0
        matches = {}

        # See difflib.diff_bytes documentation
        # https://docs.python.org/3/library/difflib.html
        # Use this to allow ndiff to work on mixed or unknown encoded
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


    def generate_chunks(self):
        while(True):
            i = self.find_next_mismatch()
            if i is None:
                self.emit_final_chunk()
                return
            if i == 1:
                o, a, b = self.find_next_match()
                if a and b:
                    self.emit_chunk(o, a, b)
                else:
                    self.emit_final_chunk()
                    return
            elif i:
                self.emit_chunk(self.on + i, self.an + i, self.bn + i)


    def inbounds(self, i):
        if (self.on + i) <= len(self.o_lines): return True
        if (self.an + i) <= len(self.a_lines): return True
        if (self.bn + i) <= len(self.b_lines): return True
        return False


    def ismatch(self, matchdict, offset, i):
        if (self.on + i) in matchdict:
            return matchdict[self.on + i] == offset + i
        return False


    def find_next_mismatch(self):
        i = 1
        while self.inbounds(i) and \
                self.ismatch(self.a_matches, self.an, i) and \
                self.ismatch(self.b_matches, self.bn, i):
            i += 1
        if self.inbounds(i): return i
        return None


    def find_next_match(self):
        ov = self.on + 1
        while(True):
            if ov > len(self.o_lines): break
            if (ov in self.a_matches and ov in self.b_matches): break
            ov += 1
        av = bv = None
        if ov in self.a_matches:
            av = self.a_matches[ov]
        if ov in self.b_matches:
            bv = self.b_matches[ov]
        return (ov, av, bv)


    def write_chunk(self, o_range, a_range, b_range):
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


    def emit_chunk(self, o, a, b):
        self.write_chunk((self.on, o-1), 
                         (self.an, a-1), 
                         (self.bn, b-1))
        self.on, self.an, self.bn = o - 1, a - 1, b - 1


    def emit_final_chunk(self):
        self.write_chunk((self.on, len(self.o_lines)+1), 
                         (self.an, len(self.a_lines)+1), 
                         (self.bn, len(self.b_lines)+1))


    def merge(self):
        self.generate_chunks()
        res = b''.join(self.chunks)
        return res


def main():
    argv = sys.argv
    if len(argv) < 4:
        print("diff3merge ancestor_path alice_path bob_path")
    ofile = argv[1]
    afile = argv[2]
    bfile = argv[3]
    with open(ofile, 'rb') as of:
        ancestor = of.read()
    with open(afile, 'rb') as af:
        alice = af.read()
    with open(bfile, 'rb') as bf:
        bob = bf.read()
    res = do_file_merge(alice, bob, ancestor)
    print(res.decode('utf-8'),end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
