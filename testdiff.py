#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

import sys
import os
from dulwich import porcelain

def main():
    acwd = os.getcwd()
    os.chdir("test1")
    # print(porcelain.branch_list("."))

    print("Testing diff of tree against tree")
    porcelain.diff(".", committish1=b"br1", committish2=b"br2")

    print("\nTesting diff of tree against working dir")
    porcelain.diff(".", committish1=b"HEAD")

    print("\nTesting diff of tree against index")
    porcelain.diff(".", committish1=b"HEAD", cached=True)

    print("\nTesting diff of index against working dir")
    porcelain.diff(".")


if __name__ == '__main__':
    sys.exit(main())
