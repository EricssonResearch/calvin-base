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
import os
import json
import difflib

# Old setup
import calvin.csparser.parser_old as parser_old
import calvin.csparser.checker as checker_old
import calvin.csparser.analyzer as analyzer_old

# New setup
import calvin.csparser.parser as parser
import calvin.csparser.codegen as codegen


def old_codegen(source, test):
    ir, errors, warnings = old_ir(source, test)
    if errors:
        for error in errors:
            print "{reason} {script} [{line}:{col}]".format(script=filename, **error)
        raise Exception("There were errors caught by the old checker...")
    return analyzer_old.Analyzer(ir)


def new_codegen(source, test):
    ast, errors, warnings = new_ast(source)
    if errors:
        for error in errors:
            print "{reason} {script} [{line}:{col}]".format(script=filename, **error)
        raise Exception("There were errors caught by the new parser...")
    cg = codegen.CodeGen(ast, test)
    cg.run()
    return cg


def old_issue_report(source, test):
    ir, errors, warnings = old_ir(source, test)
    return errors, warnings


def new_issue_report(source, test):
    ast, errors, warnings = new_ast(source)
    cg = codegen.CodeGen(ast, test)
    cg.run()
    for issue in cg.issues:
        if issue['type'] is 'error':
            errors.append(issue)
        else:
            warnings.append(issue)
    return errors, warnings


def old_ir(source_text, filename):
    ir, errors, warnings = parser_old.calvin_parser(source_text, filename)
    if not errors:
        c_errors, c_warnings = checker_old.check(ir)
        errors.extend(c_errors)
        warnings.extend(c_warnings)
    return ir, errors, warnings


def new_ast(source_text):
    ast, issues, dummy = parser.calvin_parser(source_text)
    errors = [issue for issue in issues if issue['type'] is 'error']
    warnings = [issue for issue in issues if issue['type'] is 'warning']
    return ast, errors, warnings


def test_generator(testdir, testlist):

    def collect_all_tests(testdir):
        tests = [os.path.splitext(file)[0] for file in os.listdir(testdir) if file.endswith(".calvin")]
        return tests

    testdir = os.path.abspath(os.path.expandvars(testdir))
    tests = testlist or collect_all_tests(testdir)

    for test in tests:
        filename = '{}/{}.calvin'.format(testdir, test)
        with open(filename, 'r') as f:
            source = f.read()

        yield(source, test)


def codegen_test(testlist, testdir):

    results = {}
    for source, test in test_generator(testdir, testlist):
        results[test] = {}
        try:
            a1 = old_codegen(source, test)
        except:
            results[test]['output'] = "EXCEPTION IN OLD"
            continue
        try:
            a2 = new_codegen(source, test)
        except:
            results[test]['output'] = "EXCEPTION IN NEW"
            continue

        if a1.app_info == a2.app_info:
            results[test]['output'] = "IDENTICAL"
        else:
            results[test]['output'] = "DIFFERENCE"
            out1 = json.dumps(a1.app_info, indent=4, sort_keys=True)
            out2 = json.dumps(a2.app_info, indent=4, sort_keys=True)
            diff = difflib.unified_diff(out1.splitlines(), out2.splitlines())
            results[test]['diff'] = '\n'.join(list(diff))
            results[test]['source'] = source

    return results

def old_issues_covered(old_issues, new_issues):
    # for each old issue, check if it is reported in new issues
    passed = True
    if len(old_issues) > len(new_issues):
        return False

    for t in old_issues:
        skip_line_check = (t['line'] == 0)
        issue = (t['line'], t['reason'])
        cover = [x for x in new_issues if x['reason'] == t['reason'] and (x['line'] == t['line'] or skip_line_check)]
        if not cover:
            passed = False
            break;
    return passed


def issue_test(testlist, testdir):

    results = {}
    for source, test in test_generator(testdir, testlist):
        results[test] = {}
        old_errors, old_warnings = old_issue_report(source, test)
        new_errors, new_warnings = new_issue_report(source, test)

        error_cover = old_issues_covered(old_errors, new_errors)
        warning_cover = old_issues_covered(old_warnings, new_warnings)

        if error_cover and warning_cover:
            results[test]['output'] = "PASSED"
        else:
            status = "FAILED"
            if not error_cover:
                results[test]['old_errors'] = old_errors
                results[test]['new_errors'] = new_errors
                status = status + " ERRORS"
            if not warning_cover:
                results[test]['old_warnings'] = old_warnings
                results[test]['new_warnings'] = new_warnings
                status = status + " WARNINGS"
            results[test]['output'] = status

    return results


def setup_venv():
    cwd = "/Users/eperspe/Source/calvin-base"
    env_activate = "/Users/eperspe/.virtualenvs/calvin/bin/activate_this.py"
    calvin_root = "/Users/eperspe/Source/calvin-base"

    import sys
    import os
    os.chdir(cwd)
    execfile(env_activate, dict(__file__=env_activate))
    sys.path[:0] = [calvin_root]


def run_check(tests=None, testdir='calvin/csparser/testscripts/regression-tests'):
    # Configure for virtualenv
    setup_venv()
    # Run regression checks
    print "Checking code generation..."
    results = codegen_test(tests, testdir)
    print "SUMMARY"
    print "---------------------"
    for test, result in results.iteritems():
        print test, result['output']
        if result['output'] is not "IDENTICAL":
            print result.get('diff', "-- No diff available")


def run_issue_check(tests=None, testdir='calvin/csparser/testscripts/issue-reporting-tests'):
    # Configure for virtualenv
    setup_venv()
    # Run regression checks
    print "Checking issue reporting..."
    results = issue_test(tests, testdir)
    print "SUMMARY"
    print "---------------------"
    for test, result in results.iteritems():
        print test, result['output']
        if result['output'] is not "PASSED":
            if 'old_errors' in result:
                print "    Expected:", result['old_errors']
                print "    Got     :", result['new_errors']
            if 'old_warnings' in result:
                print "    Expected:", result['old_warnings']
                print "    Got     :", result['new_warnings']


def run_all():
    run_check()
    print
    run_issue_check()


if __name__ == '__main__':
    run_all()








