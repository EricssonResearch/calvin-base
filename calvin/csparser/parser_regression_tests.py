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


def testit():
    import json
    import difflib

    # from a4 import Analyzer as A2
    from analyzer import Analyzer as A1
    from analyzer import Analyzer as A2
    import calvin.Tools.cscompiler as cscompiler

    crashers = []
    expected_diff = []
    tests = ['test1']

    res = {}
    for test in tests:
        filename = 'calvin/csparser/testscripts/%s.calvin' % test
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
        print prg
        if errors:
            for error in errors:
                print "{reason} {script} [{line}:{col}]".format(script=filename, **error)
            raise Exception("There were errors....")
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

if __name__ == '__main__':
    import sys
    import os
    os.chdir("/Users/eperspe/Source/calvin-base")
    file = "/Users/eperspe/.virtualenvs/calvin-dev/bin/activate_this.py"
    execfile(file, dict(__file__=file))
    sys.path[:0] = ["/Users/eperspe/Source/calvin-base"]
    for p in sys.path:
        print p
    testit()



