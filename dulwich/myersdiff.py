#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""
Implementation of a Myers Optimal Diff In Python3
"""

# Implementation of a Myers Optimal Diff In Python3
# Copyright (c) 2020 Kevin B. Hendricks, Stratford Ontario Canada
#
# Available under the MIT License

# Based on the the original work of Eugene W. Myers
#    "An O(ND) Difference Algorithm and Its Variations"
#    http://www.xmailserver.org/diff2.pdf

# Adopts the backtrace approach to help shrink the memory footprint of
#
#    Daniel Hernandez (DHDaniel)
#    "The Myers Difference Algorithm for Version Control Systems"
#    https://github.com/DHDaniel/git-diff-clone/
#
# which has the following license:
#
# MIT License
# 
# Copyright (c) 2020 Daniel Hernandez H.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
from collections import deque

# Uses as closely as possible the exact notation of Myers's
# "An O(ND) Difference Algorithm and Its Variations" and
# includes direct quotes to help explain how it works

# Let A represent the initial list of values to be edited with length N
# ie. A = abcabba

# Let B represent the final list of values of the target with length M
# ie. B = cbabac

# An edit script for A and B is a set of insertion and deletion commands
# that transform A into B.  The length of a script is the number of symbols
# inserted and deleted.

# An Edit Graph for A and B has a vertex at each point in the grid (x,y)
# where: 0 <= x <= N, and 0 <= y <= M

# Horizontal edges connect each vertex to its right neighbor:
#     (x-1, y) -> (x, y)
# Vertical edges connect each vertex to the neighbor below:
#     (x, y-1) -> (x, y)
# Diagonal edges connect each vertex to the neighbor right and below:
#     (x-1,y-1) -> (x,y)
# The points (x,y) for which Ax == By are called match points

# The total number of match points between A and B is the number of
# diagonal edges in the edit graph as diagonal edges are in
# one-to-one correspondence with match points.

# A trace of length L is a sequence of L match points,
# (x1 ,y1 )(x2 ,y2 ) . . . (xL ,yL ), such that xi < xi+1 and
# yi < yi + 1 for successive points (xi,yi) and (xi + 1,yi + 1), i∈[1,L−1].

# Every trace is in exact correspondence with the diagonal edges of a path
# in the edit graph from (0,0) to (N,M).

# Each diagonal edge ending at (x,y) corresponds to a keep (match).
# Each horizontal edge to point (x,y) corresponds to a delete;
# Each vertical edge from (x,y) corresponds to an insert.

# The Algorithm - The problem of finding a shortest edit script (SES)
# then reduces to finding a path from (0,0) to (N,M) with the fewest
# number of horizontal and vertical edges.

# Let a D-path be a path starting at (0,0) that has exactly D
# non-diagonal edges.
# A 0-path must consist solely of diagonal edges.
# By simple induction, it follows that a D-path must consist of
# a (D − 1)-path followed by a non-diagonal edge and then a
# possibly empty sequence of diagonal edges called a *snake*.

# Number the diagonals in the grid of edit graph vertices so that
# diagonal k consists of the points (x,y) for which x − y = k.
# With this definition the diagonals are numbered from −M to N.

# Note that a vertical (horizontal) edge with start point on diagonal k
# has end point on diagonal k − 1 (k + 1) and a snake remains on the
# diagonal in which it starts.

# Let V: array [-Max .. Max ] of Integer
#    where V[k] contains the row index of the endpoint of a furthest
#    reaching path in diagonal k of the EditGraph

# Note: Even and odd diagonals end points are disjoint so the values
# from the even numbered diagonals can be used to calc odd numbered
# diagonals

# The pseudo code for the algorithm directly from the paper
# Constant MAX ∈ [0,M+N]
# Var V: Array [− MAX .. MAX] of Integer
# V[1]←0
# For D ← 0 to MAX Do
#     For k ← −D to D in steps of 2 Do
#            If k=−D or k≠D and V[k−1]<V[k+1] The
#                x ← V[k+1]
#            Else
#                x ← V[k−1]+1
#            y←x−k
#            While x<N and y<M and ax+1 = by+1 Do (x,y)←(x+1,y+1)
#            V[k]←x
#            If x≥N and y≥M Then
#                Length of an SES is D
#                Stop
# Length of an SES is greater than MAX


def _myers_ses(a_lines, b_lines):
    """ Myers algorithm to determine the shortest edit script
        Args:
          a_lines - list of byte strings representing lines of 'from' file
          b_lines - list of byte strings representing lines of 'to' file
        Returns:
          a list of V arrays representing the history of vertices
          used to generate the shortest edit script
    """
    m, n = len(a_lines), len(b_lines)
    MAX = m + n
    trace = []
    v = [-1 for i in range(2 * MAX + 1)]
    v[1] = 0
    for d in range(MAX+1):
        for k in range(-d, d+1, 2):
            if k == -d or (k != d and v[k - 1] < v[k + 1]):
                x = v[k + 1]
            else:
                x = v[k - 1] + 1
            y = x - k
            # Snake of diagonals
            while x < m and y < n and a_lines[x] == b_lines[y]:
                x, y = x + 1, y + 1
            v[k] = x
            if x >= n and y >= m:
                return trace
        # Need to store away the history of vertice traces to later
        # extract the edit script
        trace.append(v[:])


# Used to extract the SES (shortest edit script) by walking the trace
# vertices history backwards by D-path length along the frontier.
# Using the backtrace approach means the edit script itself does
# NOT have to be stored as it is built, only the V needs be kept across
# iterations and thereby reduces the total memory footprint
def _myers_backtrace(trace, a_lines, b_lines):
    """Yields in reverse order the (prev x, prevy, x, y) for each interation
        that represents the SES from (N,M) to (0,0)
        Args:
          trace - a list of V arrays representing the history of vertices
                  used when generating the shortest edit script
          a_lines - list of byte strings representing lines of 'from' file
          b_lines - list of byte strings representing lines of 'to' file
        Yields/Returns:
          a tuple of prev_x, prev_y, x, y of the vertices of the SES
    """
    x, y = len(a_lines), len(b_lines)
    # Each trace represents a D-path length value 1, ..., up to N+M
    # Reverse the trace history list to get the longest D-Path trace first
    trace_enum = list(enumerate(trace))
    trace_enum.reverse()
    # Determine the diagonal number from V (initial since reversed is (N,M))
    # Extract prev k diagonal number from movement direction
    # Then use prev k and V to get prev x and prev y
    # Climb up any snakes if needed
    # Rinse and repeat until D = 0 case has been processed
    for d, v in trace_enum:
        k = x - y
        if k == -d or (k != d and v[k - 1] < v[k + 1]):
            prev_k = k + 1
        else:
            prev_k = k - 1
        prev_x = v[prev_k]
        prev_y = prev_x - prev_k
        while x > prev_x and y > prev_y:
            yield (x - 1, y - 1, x, y)
            x, y = x - 1, y - 1
        if d >= 0:
            yield (prev_x, prev_y, x, y)
        x, y = prev_x, prev_y
    # Handle any initial snake (ie. not reached origin yet)
    while x > 0 and y > 0:
        yield (x - 1, y - 1, x, y)
        x, y = x - 1, y - 1


def myers_diff(a_lines, b_lines):
    """ Uses the Myers's algorithm to create a diff from a to b
        Args:
          a_lines - list of byte strings representing lines of 'from' file
          b_lines - list of byte strings representing lines of 'to' file
        Returns:
          list of edit lines to convert the 'from' file contents to the 'to'
          All lines returned are preceded by a two character string
          indicating the required change:
          b'+ ' - insert, b'- ' - delete, b'  ' - keep
    """
    m, n = len(a_lines), len(b_lines)
    res = deque()
    trace = _myers_ses(a_lines, b_lines)
    backtrack = _myers_backtrace(trace, a_lines, b_lines)
    # determine edit that moves from (prev_x, prev_y) to (x,y)
    # ie. what was done: '+ ','- ','  '
    for prev_x, prev_y, x, y in backtrack:
        a_line = a_lines[prev_x] if prev_x < m else None
        b_line = b_lines[prev_y] if prev_y < n else None
        if a_line is not None and b_line is not None:
            if x == prev_x:
                res.appendleft(b'+ ' + b_line)
            elif y == prev_y:
                res.appendleft(b'- ' + a_line)
            else:
                res.appendleft(b'  ' + a_line)
    return list(res)


def main():
    """ Uses the Myers's algorithm to produce the diff from file a to file b
        Args:
          from_path to file a
          to_path to file b
        Returns 0:
          prints the diff of from_file to to_file
          All lines returned are preceded by a two character string
          indicating the required change:
          b'+ ' - insert, b'- ' - delete, b'  ' - keep
    """
    argv = sys.argv
    if len(argv) < 2:
        print("myersdiff.py from_path to_path")
    fromfile = argv[1]
    tofile = argv[2]
    # Can be used on text with any encoding (even mixed) so treat
    # all as bytestrings
    try:
        with open(fromfile, 'rb') as ff:
            a = ff.read()
        with open(tofile, 'rb') as tf:
            b = tf.read()
    except:  # noqa:E722
        a, b = b'', b''
    res = myers_diff(a.splitlines(keepends=True), b.splitlines(keepends=True))
    print(b''.join(res).decode('utf-8'), end="")
    return 0


if __name__ == '__main__':
    sys.exit(main())
