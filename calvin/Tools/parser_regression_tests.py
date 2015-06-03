# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import difflib
import cscompiler
from a4 import Analyzer as A2
from analyzer import Analyzer as A1

crashers = ['test14', 'test15', 'test16']
expected_diff = []
tests = ['args1', 'args2', 'args3', 'args4', 'test1', 'test2', 'test2xin', 'test3', 'test4', 'test5', 'test6', 'test8', 'test8a', 'test9', 'test9a', 'test9b', 'test11', 'test11a', 'test12', 'test13', 'test14', 'test15', 'test16']

res = {}
for test in tests:
    filename = 'tests/scripts/%s.calvin' % test
    print test,

    with open(filename, 'r') as f:
        source = f.read()

    header = source.splitlines()[0].lstrip('/ ')
    print header,
    res[test] = [header]
    if test in crashers:
        res[test].append("CRASHER")
        print "CRASHER"
        continue

    prg, errors, warnings = cscompiler.compile(source, test)
    if error:
        print "{reason} {script} [{line}:{col}]".format(script=filename, **error)
        raise Exception(error['reason'])
    a1 = A1(prg)
    a2 = A2(prg)

    # print "======= DONE ========"

    if a1.app_info == a2.app_info:
        output = "EXPECTED DIFF" if test in expected_diff else "IDENTICAL"
        print output
    else:
        output = "EXPECTED DIFF" if test in expected_diff else "DIFFERENCE"
        print output
        out1 = json.dumps(a1.app_info, indent=4, sort_keys=True)
        out2 = json.dumps(a2.app_info, indent=4, sort_keys=True)
        diff = difflib.unified_diff(out1.splitlines(), out2.splitlines())
        print '\n'.join(list(diff))

    res[test].append(output)


print
print "SUMMARY"
print "---------------------"
for test in tests:
    print test, res[test][1]


