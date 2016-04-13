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


def testit(testlist, print_diff, print_script):
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
    tests = testlist or [
        'empty_script',
        'define_constants',
        'two_actors',
        'three_actors',
        'implicit_port',
        'actor_one_arg',
        'actor_two_args',
        'define_component',
        'local_component'
    ]

    res = {}
    for test in tests:
        try:
            filename = 'calvin/csparser/testscripts/regression-tests/%s.calvin' % test
            print test,

            with open(filename, 'r') as f:
                source = f.read()

            #header = source.splitlines()[0].lstrip('/ ')
            # print header,
            res[test] = [test]
            if test in crashers:
                res[test].append("CRASHER")
                print "CRASHER"
                continue

            a1 = analyzer_old.Analyzer(old_ir(source, test))
            a2 = codegen.CodeGen(ast(source), test)

            # print "======= DONE ========"

            if a1.app_info == a2.app_info:
                output = "IDENTICAL {}".format("(SURPRISE)" if test in expected_diff else "")
                print output
            else:
                if print_script:
                    print source
                    print

                output = "DIFFERENCE {}".format("(EXPECTED)" if test in expected_diff else "")
                print output
                if print_diff:
                    out1 = json.dumps(a1.app_info, indent=4, sort_keys=True)
                    out2 = json.dumps(a2.app_info, indent=4, sort_keys=True)
                    diff = difflib.unified_diff(out1.splitlines(), out2.splitlines())
                    print '\n'.join(list(diff))

            res[test].append(output)
        except Exception as e:
            import sys
            exc_type, exc_obj, tb = sys.exc_info()
            f = tb.tb_frame
            lineno = tb.tb_lineno
            filename = f.f_code.co_filename
            print 'EXCEPTION IN ({}, "{}"): {}'.format(filename, lineno, exc_obj)



    print
    print "SUMMARY"
    print "---------------------"
    for test in tests:
        print test, res[test][1] if len(res[test])>1 else "--- CRASH ---"


def run_check(tests=None, print_diff=True, print_script=False):
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
    testit(tests, print_diff, print_script)

if __name__ == '__main__':
    run_check()



