#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Testcases for confsort module.
"""
import confsort


def test_setup():
    """
    Setup arguments for testcase.
    """
    config = """
             [testing]
             abc=$cde/hej
             ijk=$abc/aj
             sdf=$ijk/ojoj
             blu=$ijk/ojsan
             cde=gfh/da
             """
    fp = open("test.ini", 'w')
    fp.write(config)
    fp.close()


def test():
    """
    A testcase for this module.
    """
    fp = open("test.ini", 'r')
    original = fp.readlines()
    fp.close()

    confsort.reorder("test.ini")

    fp = open("test.ini", 'r')
    sort = fp.readlines()
    fp.close()

    print "Origin \t{}".format(original)
    print "Sorted \t{}".format(sort)

test_setup()
test()
