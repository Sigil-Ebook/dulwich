#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
"""
Implementation of os.fsencode and os.fsdecode for python 2.7
"""

# Copyright (C) 2020 Kevin B. Hendricks, Stratford Ontario Canada
#
# All rights reserved.
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Due to Linux use of arbitrary bytes in paths and the fact that a
# single code base must work on all platforms across python 2.7 and 3.x,
# we need to use the os.fsencode and os.fsdecode routines when coverting
# paths to and from bytes/unicode but os.fsencode and os.fsdecode do
# not exist in python 2.7 so we need to replace them


from __future__ import print_function

import sys
import os
import codecs

_PY3 = sys.version_info[0] >= 3
_ISWINDOWS = sys.platform.startswith('win')


if _PY3:  # only needed to prevent flake8 errors on Python 3.X
    unicode = str
    unichr = chr


# These routines are only used on Python 2.7


def _os_fsencode(apath, fs_encoding=sys.getfilesystemencoding()):
    if isinstance(apath, bytes):
        return apath
    # manually undo what surrogateescape may have done
    res = []
    for c in apath:
        if 0xdc00 <= ord(c) <= 0xdcff:
            res.append(chr(ord(c) - 0xdc00))
        else:
            res.append(c.encode(fs_encoding))
    return b''.join(res)


def _os_fsdecode(apath, fs_encoding=sys.getfilesystemencoding()):
    if isinstance(apath, unicode):
        return apath
    if _ISWINDOWS:
        return apath.decode(fs_encoding, 'strict')
    return apath.decode(fs_encoding, 'surrogateescape')


def _surrogate_escape_for_decode(error):
    c = error.object[error.start:error.end]
    val = ord(c)
    val += 0xdc00
    return unichr(val), error.end


if _PY3:
    os_fsencode = os.fsencode
    os_fsdecode = os.fsdecode
else:
    os_fsencode = _os_fsencode
    os_fsdecode = _os_fsdecode
    codecs.register_error('surrogateescape', _surrogate_escape_for_decode)


# ------------- public functions -----------------


def bytes_path(apath):
    """ convert a file path to bytes using os.fsencode
        or its equivalent on Python 2.7
    Args:
        apath - a file path
    Returns
        the path converted into bytes on Python 3.x and str on Python 2.7
    """
    if apath is None:
        return None
    return os_fsencode(apath)


def unicode_path(apath):
    """ convert a file path to unicode using os.fsdecode
        or its equivalent on Python 2.7
    Args:
        apath - a file path
    Returns
        the path converted into str on Python 3.x and unicode on Python 2.7
    """
    if apath is None:
        return None
    return os_fsdecode(apath)


def printable_path(apath):
    """ convert a path with possible embedded surrogates
        to something that can be printed without errors
    Args:
        apath - a file path
    Returns
        the path converted into a pure unicode with
        replacement chars if needed
    """
    if isinstance(apath, bytes):
        upath = unicode_path(apath)
    else:
        upath = apath
    bpath = upath.encode('utf-8', 'replace')
    return bpath.decode('utf-8', 'strict')


def test():
    # basic round trip test
    bytes_path = b"hello/I/am/a/path.txt"
    text_path = u"hello/I/am/a/path.txt"
    a = bytes_path(text_path)
    b = unicode_path(bytes_path)
    print(a, type(a))
    print(b, type(b))

    # test with arbitrary bytes path from linux
    linux_bytes_path = b'/non/ascii\xffgh'
    print(linux_bytes_path == bytes_path(linux_bytes_path))
    c = unicode_path(linux_bytes_path)
    # note: c can still not be printed on Python 3
    # since surrogates are embedded, it will throw utf-8 encode exception
    print(printable_path(c), type(c))
    d = bytes_path(c)
    print(d == linux_bytes_path)


if __name__ == '__main__':
    sys.exit(test())
