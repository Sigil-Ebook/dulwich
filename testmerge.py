#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

import sys
import os
from dulwich import porcelain
from dulwich.diff3merge import do_file_merge_myers
from dulwich.diff3merge import do_file_merge_ndiff

def main():
    acwd = os.getcwd()
    os.chdir("test1")
    print(porcelain.branch_list("."))
    mb = porcelain.merge_base(".",["br1", "br2"])
    print(mb)
    print(porcelain.merge_base_is_ancestor(".", mb, "br1"))
    print(porcelain.merge_base_is_ancestor(".", mb, "br2"))
    porcelain.branch_merge(".",["br1", "br2"], do_file_merge_myers)

if __name__ == '__main__':
    sys.exit(main())
