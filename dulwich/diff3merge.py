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

from difflib import ndiff

# from collections import namedtuple
# from mdiff import myers_diff, Keep, Insert, Remove

    
class Merge3Way(object):

    def __init__(self, ancestor_path, alice_path, bob_path, use_myers):
        self.o_file = ancestor_path
        self.a_file = alice_path
        self.b_file = bob_path
        self.o_lines = []
        self.a_lines = []
        self.b_lines = []
        # Note: keep lineends if passed text by using splitlines(keepends=True)
        try:
            with open(self.o_file) as of:
                self.o_lines = of.readlines()
            with open(self.a_file) as af:
                self.a_lines = af.readlines()
            with open(self.b_file) as bf:
                self.b_lines = bf.readlines()
        except:
            self.o_lines, self.a_lines, self.b_lines = [''], [''], ['']

        if use_myers:
            self.a_matches = self.myers_matches(self.o_lines, self.a_lines)
            self.b_matches = self.myers_matches(self.o_lines, self.b_lines)
        else:
            self.a_matches = self.ndiff_matches(self.o_lines, self.a_lines)
            self.b_matches = self.ndiff_matches(self.o_lines, self.b_lines)

        self.chunks = []
        self.on, self.an, self.bn = 0, 0, 0

    def ndiff_matches(self, olines, dlines):
        # ancestor line number to alice/bob line numbers for matching lines
        on, dn = 0, 0
        matches = {}
        for line in ndiff(olines, dlines, linejunk=None, charjunk=None):
            dt = line[0:2]
            if dt == '  ':
                on += 1
                dn += 1
                matches[on] = dn
            elif dt == '+ ':
                dn += 1
            elif dt == '- ':
                on += 1
        return matches

    def myers_matches(self, olines, dlines):
        # ancestor line number to alice/bob line numbers for matching lines
        on, dn = 0, 0
        matches = {}
        for elem in myers_diff(olines, dlines):
            if isinstance(elem, Keep):
                on += 1
                dn += 1
                matches[on] = dn
            elif isinstance(elem, Insert):
                dn += 1
            else:
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
        oc = ''.join(self.o_lines[o_range[0]:o_range[1]])
        ac = ''.join(self.a_lines[a_range[0]:a_range[1]])
        bc = ''.join(self.b_lines[b_range[0]:b_range[1]])
        if oc == ac and oc == bc:
            self.chunks.append(oc)
        elif oc == ac:
            self.chunks.append(bc)
        elif oc == bc:
            self.chunks.append(ac)
        else:
            # conflict
            cc = '<<<<<<< ' + self.a_file + '\n'
            cc += ac
            cc += '======= \n'
            cc += bc
            cc += '>>>>>>> ' + self.b_file + '\n'
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
        res = ''.join(self.chunks)
        print(res, end="")

def main():
    argv = sys.argv
    if len(argv) < 4:
        print("diff3merge ancestor_path alice_path bob_path")
    ofile = argv[1]
    afile = argv[2]
    bfile = argv[3]
    use_myers = False
    mrg3 = Merge3Way(ofile, afile, bfile, use_myers)
    mrg3.merge()
    return 0


if __name__ == '__main__':
    sys.exit(main())
