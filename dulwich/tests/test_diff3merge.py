# -*- coding: utf-8 -*-
# test_diff3merge.py -- Tests for diff3 merge
# encoding: utf-8
# Copyright (c) 2020 Kevin B. Hendricks, Stratford Ontario Canada

"""Tests for diff3merge."""

from dulwich.diff3merge import do_file_merge_myers, do_file_merge_ndiff
from dulwich.tests import TestCase


class FindDiff3MergeTests(TestCase):

    @staticmethod
    def run_test(alice, bob, base, dtype):
        if (dtype == "myers"):
            return do_file_merge_myers(alice, bob, base)
        return do_file_merge_ndiff(alice, bob, base)

    def test_grocery_list_myers(self):
        # standard grocery list example of original paper
        # which diff method is used matters as there are many
        # ways to determine identical chunks across all 3 versions
        dtype = "myers"
        alice = b"""celery
salmon
tomatoes
garlic
onions
wine
"""
        bob = b"""celery
salmon
garlic
onions
tomatoes
wine
"""
        base = b"""celery
garlic
onions
salmon
tomatoes
wine
"""
        res, conflicts = self.run_test(alice, bob, base, dtype)
        expected_conflicts = [((1, 4), (1, 2), (1, 4))]
        expected_results = b"""celery
<<<<<<< alice
salmon
======= 
salmon
garlic
onions
>>>>>>> bob
tomatoes
garlic
onions
wine
"""  # noqa:W291
        self.assertEqual(res, expected_results)
        self.assertEqual(conflicts, expected_conflicts)

    def test_grocery_list_ndiff(self):
        # standard grocery list example of original paper
        # which diff method is used matters as there are many
        # ways to determine identical chunks across all 3 versions
        dtype = "ndiff"
        alice = b"""celery
salmon
tomatoes
garlic
onions
wine
"""
        bob = b"""celery
salmon
garlic
onions
tomatoes
wine
"""
        base = b"""celery
garlic
onions
salmon
tomatoes
wine
"""
        res, conflicts = self.run_test(alice, bob, base, dtype)
        expected_conflicts = [((1, 1), (1, 3), (1, 2)),
                              ((3, 5), (5, 5), (4, 5))]
        expected_results = b"""celery
<<<<<<< alice
salmon
tomatoes
======= 
salmon
>>>>>>> bob
garlic
onions
<<<<<<< alice
======= 
tomatoes
>>>>>>> bob
wine
"""  # noqa:W291
        self.assertEqual(res, expected_results)
        self.assertEqual(conflicts, expected_conflicts)

    def test_text_block_myers(self):
        dtype = "ndiff"
        alice = b"""Add a line here
This is a more complete test
and a few typ0s to fix
also I plan to add few lines
    and to remove
"""
        bob = b"""This is a more complete test
and a few typos to fix
also I plan to add few lines
    and to remove
other lines
"""
        base = b"""This is a more complete test
and a few typ0s to fix
also I plan to add few lines
    and to remove
other lines
"""
        res, conflicts = self.run_test(alice, bob, base, dtype)
        expected_conflicts = []
        expected_results = b"""Add a line here
This is a more complete test
and a few typos to fix
also I plan to add few lines
    and to remove
"""
        self.assertEqual(res, expected_results)
        self.assertEqual(conflicts, expected_conflicts)

    def test_text_block_ndiff(self):
        dtype = "ndiff"
        alice = b"""Add a line here
This is a more complete test
and a few typ0s to fix
also I plan to add few lines
    and to remove
"""
        bob = b"""This is a more complete test
and a few typos to fix
also I plan to add few lines
    and to remove
other lines
"""
        base = b"""This is a more complete test
and a few typ0s to fix
also I plan to add few lines
    and to remove
other lines
"""
        res, conflicts = self.run_test(alice, bob, base, dtype)
        expected_conflicts = []
        expected_results = b"""Add a line here
This is a more complete test
and a few typos to fix
also I plan to add few lines
    and to remove
"""
        self.assertEqual(res, expected_results)
        self.assertEqual(conflicts, expected_conflicts)
