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

    # Old setup
    import calvin.csparser.parser_old as parser_old
    import calvin.csparser.checker as checker_old
    import calvin.csparser.analyzer as analyzer_old

    # New setup
    import calvin.csparser.parser as parser
    import calvin.csparser.codegen as codegen

    def old_ir(source_text, filename):
        ir, errors, warnings = parser_old.calvin_parser(source_text, filename)
        if not errors:
            c_errors, c_warnings = checker_old.check(ir)
            errors.extend(c_errors)
            warnings.extend(c_warnings)
        if errors:
            for error in errors:
                print "{reason} {script} [{line}:{col}]".format(script=filename, **error)
            raise Exception("There were errors caught by the old checker...")
        return ir

    def ast(source_text):
        ast, errors, warnings = parser.calvin_parser(source_text)
        if errors:
            for error in errors:
                print "{reason} {script} [{line}:{col}]".format(script=filename, **error)
            raise Exception("There were errors caught by the new parser...")
        return ast


    crashers = []
    expected_diff = []
    tests = ['test1', 'test2', 'test3', 'test4', 'test5']

    res = {}
    for test in tests:
        try:
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

            a1 = analyzer_old.Analyzer(old_ir(source, test))
            a2 = codegen.CodeGen(ast(source), test)

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
        except Exception as e:
            print "Error", e


    print
    print "SUMMARY"
    print "---------------------"
    for test in tests:
        print test, res[test][1]


def run_check():
    # Configure for virtualenv
    cwd = "/Users/eperspe/Source/calvin-base"
    env_activate = "/Users/eperspe/.virtualenvs/calvin/bin/activate_this.py"
    calvin_root = "/Users/eperspe/Source/calvin-base"

    import sys
    import os
    os.chdir(cwd)
    execfile(env_activate, dict(__file__=env_activate))
    sys.path[:0] = [calvin_root]

    # Run regression checks
    testit()

if __name__ == '__main__':
    run_check()



