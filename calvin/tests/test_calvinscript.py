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

from calvin.csparser.parser import calvin_parser
from calvin.csparser.analyzer import generate_app_info
from calvin.csparser.checker import check
import unittest
import json
import difflib
import pytest

def absolute_filename(filename):
    import os.path
    return os.path.join(os.path.dirname(__file__), filename)


class CalvinTestBase(unittest.TestCase):

    def setUp(self):
        self.test_script_dir = absolute_filename('scripts/')

    def tearDown(self):
        pass

    def _read_file(self, file):
        try:
            with open(file, 'r') as source:
                text = source.read()
        except Exception as e:
            print "Error: Could not read file: '%s'" % file
            raise e
        return text

    def _format_unexpected_error_message(self, errors):
        msg_list = ["Expected empty error, not {0}".format(err) for err in errors]
        return '\n'.join(msg_list)

    def invoke_parser(self, test, source_text=None):
        if not source_text:
            test = self.test_script_dir + test + '.calvin'
            source_text = self._read_file(test)
        return calvin_parser(source_text, test)

    def invoke_parser_assert_syntax(self, test, source_text=None):
        """Verify that the source is free from syntax errors and return parser output"""
        result, errors, warnings = self.invoke_parser(test, source_text)
        self.assertFalse(errors, self._format_unexpected_error_message(errors))
        return result

    def assert_script(self, test):
        """Check parsing of script against a reference result"""
        result = self.invoke_parser_assert_syntax(test)
        ref_file = self.test_script_dir + test + '.ref'
        reference = self._read_file(ref_file)
        # Canonical form
        sorted_result = json.dumps(result, indent=4, sort_keys=True)
        sorted_result = "\n".join([line for line in sorted_result.splitlines() if "sourcefile" not in line])
        reference = "\n".join([line for line in reference.splitlines() if "sourcefile" not in line])
        diff_lines = difflib.unified_diff(sorted_result.splitlines(), reference.splitlines())
        diff = '\n'.join(diff_lines)
        self.assertFalse(diff, diff)


class CalvinScriptParserTest(CalvinTestBase):
    """Test the CalvinScript parser"""

    def testSimpleStructure(self):
        """Basic sanity check"""
        self.assert_script('test1')

    def testComplexScript(self):
        self.assert_script('test9')

    def testComponentDefinitions(self):
        self.assert_script('test8')

    def testSyntaxError(self):
        """Check syntax error output"""
        test = 'test10'
        result, errors, warnings = self.invoke_parser(test)
        self.assertEqual(errors[0], {'reason': 'Syntax error.', 'line': 6, 'col': 2})


class CalvinScriptAnalyzerTest(CalvinTestBase):
    """Test the CalvinsScript analyzer"""

    def assert_app_info(self, test, app_info):
        """Check app_info against a reference result"""
        ref_file = self.test_script_dir + test + '.app_info'
        reference = self._read_file(ref_file)
        # Canonical form
        sorted_app_info = json.dumps(app_info, indent=4, sort_keys=True)
        diff_lines = difflib.unified_diff(sorted_app_info.splitlines(), reference.splitlines())
        diff = '\n'.join(diff_lines)
        self.assertFalse(diff, diff)

    def testSimpleScript(self):
        test = 'test9'
        # First make sure result below is error-free
        result = self.invoke_parser_assert_syntax(test)
        app_info = generate_app_info(result)
        self.assert_app_info(test, app_info)

    def testMissingActor(self):
        script = """a:std.NotLikely()"""
        result = self.invoke_parser_assert_syntax('inline', script)
        app_info = generate_app_info(result)
        self.assertFalse(app_info['valid'])


class CalvinScriptCheckerTest(CalvinTestBase):
    """Test the CalvinsScript checker"""

    def testCheckSimpleScript(self):
        script = """
        a:Foo()
        b:Bar()
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertTrue(errors)

    def testCheckLocalComponent(self):
        script = """
        component Foo() -> out {
            f:std.CountTimer()
            f.integer > .out
        }
        a:Foo()
        b:io.StandardOut()
        a.out > b.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertFalse(errors, '\n'.join([str(error) for error in errors]))
        self.assertFalse(warnings, '\n'.join([str(warning) for warning in warnings]))

    def testCheckOutportConnections(self):
        script = """
        a:std.CountTimer()
        b:std.CountTimer()
        c:io.StandardOut()
        a.integer > c.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(errors[0]['reason'], "Actor b (std.CountTimer) is missing connection to outport 'integer'")
        self.assertFalse(warnings)

    def testCheckInportConnections(self):
        script = """
        c:io.StandardOut()
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(errors[0]['reason'], "Missing connection to inport 'c.token'")
        self.assertFalse(warnings)

    def testCheckInportConnections(self):
        script = """
        a:std.CountTimer()
        b:std.CountTimer()
        c:io.StandardOut()
        a.integer > c.token
        b.integer > c.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['reason'], "Actor c (io.StandardOut) has multiple connections to inport 'token'")
        self.assertFalse(warnings)

    def testBadComponent1(self):
        script = """
        component Foo() -> out {
            a:std.CountTimer()
            b:std.CountTimer()
            a.integer > .out
        }
        a:Foo()
        b:io.StandardOut()
        a.out > b.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Actor b (std.CountTimer) is missing connection to outport 'integer'")
        self.assertFalse(warnings)

    def testBadComponent2(self):
        script = """
        component Foo() -> out {
            a:std.CountTimer()
            b:io.StandardOut()
            a.integer > b.token
        }
        a:Foo()
        b:io.StandardOut()
        a.out > b.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Component Foo is missing connection to outport 'out'")
        self.assertFalse(warnings)

    def testBadComponent3(self):
        script = """
        component Foo() -> out {
            a:std.CountTimer()
            a.integer > .out
            a.integer > .out
        }
        a:Foo()
        b:io.StandardOut()
        a.out > b.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['reason'], "Component Foo has multiple connections to outport 'out'")
        self.assertEqual(errors[1]['reason'], "Component Foo has multiple connections to outport 'out'")
        self.assertFalse(warnings)

    def testBadComponent4(self):
        script = """
        component Foo() in -> {
            a:io.StandardOut()
        }
        b:Foo()
        a:std.CountTimer()
        a.integer > b.in
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['reason'], "Component Foo is missing connection to inport 'in'")
        self.assertEqual(errors[1]['reason'], "Actor a (io.StandardOut) is missing connection to inport 'token'")
        self.assertFalse(warnings)

    def testBadComponent5(self):
        script = """
        component Foo() in -> {
            a:io.StandardOut()
            .foo > a.token
        }
        b:Foo()
        a:std.CountTimer()
        a.integer > b.in
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['reason'], "Component Foo has no inport 'foo'")
        self.assertEqual(errors[1]['reason'], "Component Foo is missing connection to inport 'in'")
        self.assertEqual(len(warnings), 0)

    def testBadComponent6(self):
        script = """
        component Foo() -> out {
            a:std.CountTimer()
            a.integer > .foo
        }
        b:Foo()
        a:io.StandardOut()
        b.out > a.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['reason'], "Component Foo has no outport 'foo'")
        self.assertEqual(errors[1]['reason'], "Component Foo is missing connection to outport 'out'")
        self.assertEqual(len(warnings), 0)

    def testBadComponent7(self):
        script = """
        component Foo() in -> out {
            .in > .out
        }
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Component Foo passes port 'in' directly to port 'out'")
        self.assertEqual(len(warnings), 0)

    def testUndefinedActors(self):
        script = """
        a.token > b.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['reason'], "Undefined actor: 'a'")
        self.assertEqual(errors[1]['reason'], "Undefined actor: 'b'")


    def testUndefinedArguments(self):
        script = """
        a:std.Constant()
        b:io.StandardOut()
        a.token > b.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Missing argument: 'data'")

    def testComponentUndefinedArgument(self):
        script = """
        component Foo(file) in -> {
            a:io.StandardOut()
            .in > a.token
        }
        b:Foo()
        a:std.CountTimer()
        a.integer > b.in
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['reason'], "Unused argument: 'file'")
        self.assertEqual(errors[1]['reason'], "Missing argument: 'file'")

    def testComponentUnusedArgument(self):
        script = """
        component Foo(file) in -> {
            a:io.StandardOut()
            .in > a.token
        }
        b:Foo(file="Foo.txt")
        a:std.CountTimer()
        a.integer > b.in
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 1)
        self.assertEqual(len(warnings), 0)
        self.assertEqual(errors[0]['reason'], "Unused argument: 'file'")

    def testLocalComponentRecurse(self):
        script = """
          component E() in -> out {
          f:std.Identity()

          .in > f.token
          f.token > .out
        }
        component B() in -> out {
          e:E()

          .in > e.in
          e.out > .out
        }

        a:std.Counter()
        b:B()
        c:io.StandardOut()

        a.integer > b.in
        b.out > c.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(warnings), 0)

    @pytest.mark.xfail(reason="Since component def is now a dict, order is not preserved. Needs fix.")
    def testLocalComponentBad(self):
        script = """
        component B() in -> out {
          e:E()

          .in > e.in
          e.out > .out
        }
        component E() in -> out {
          f:std.Identity()

          .in > f.token
          f.token > .out
        }

        a:std.Counter()
        b:B()
        c:io.StandardOut()

        a.integer > b.in
        b.out > c.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Unknown actor type: 'E'")
        self.assertEqual(len(warnings), 0)

    def testNoSuchPort(self):
        script = """
        i:std.Identity()
        src:std.CountTimer()
        dst:io.StandardOut()
        src.integer > i.foo
        i.bar > dst.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        self.assertEqual(len(errors), 4)
        self.assertEqual(errors[0]['reason'], "Actor i (std.Identity) has no inport 'foo'")
        self.assertEqual(errors[1]['reason'], "Actor i (std.Identity) has no outport 'bar'")
        self.assertEqual(errors[2]['reason'], "Actor i (std.Identity) is missing connection to inport 'token'")
        self.assertEqual(errors[3]['reason'], "Actor i (std.Identity) is missing connection to outport 'token'")
        self.assertEqual(len(warnings), 0)

    @pytest.mark.xfail()
    def testRedfineInstance(self):
        script = """
        i:std.Identity()
        src:std.CountTimer()
        dst:io.StandardOut()
        i:std.RecTimer()
        src.integer > i.token
        i.token > dst.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        print errors
        self.assertEqual(len(errors), 1)
        self.assertEqual(len(warnings), 0)

    def testUndefinedActorInComponent(self):
        script = """
        component Bug() -> out {
          b.out > .out
        }
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        print errors
        self.assertEqual(len(errors), 1)
        self.assertEqual(len(warnings), 0)


class CalvinScriptDefinesTest(CalvinTestBase):
    """Test CalvinsScript defines"""

    def testUndefinedConstant(self):
        script = """
        src : std.Constant(data=FOO)
        snk : io.StandardOut()
        src.token > snk.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        print errors
        self.assertEqual(len(errors), 1)
        self.assertEqual(len(warnings), 0)
        self.assertEqual(errors[0]['reason'], "Undefined identifier: 'FOO'")

    def testDefinedConstant(self):
        script = """
        define FOO = 42
        src : std.Constant(data=FOO)
        snk : io.StandardOut()
        src.token > snk.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        print errors
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(warnings), 0)

    @pytest.mark.xfail()
    def testUndefinedRecursiveConstant(self):
        script = """
        define FOO = BAR
        src : std.Constant(data=FOO)
        snk : io.StandardOut()
        src.token > snk.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        print errors
        self.assertEqual(len(errors), 1)
        self.assertEqual(len(warnings), 0)
        self.assertEqual(errors[0]['reason'], "Undefined identifier: 'FOO'")


    def testDefinedRecursiveConstant(self):
        script = """
        define FOO = BAR
        define BAR = 42
        src : std.Constant(data=FOO)
        snk : io.StandardOut()
        src.token > snk.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        print errors
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(warnings), 0)


    def testLiteralOnPort(self):
        script = """
        snk : io.StandardOut()
        42 > snk.token
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        print errors
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(warnings), 0)

    @pytest.mark.xfail()
    def testComponentArgumentOnPort(self):
        script = """
        component Foo(foo) -> out {
            foo > .out
        }
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        print errors
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(warnings), 0)

    @pytest.mark.xfail()
    def testBadLocalPort(self):
        script = """
        component Foo() in -> {
            snk : io.StandardOut()
            .in > snk.token
        }
        src : std.Counter()
        src.integer > .in
        """
        result = self.invoke_parser_assert_syntax('inline', script)
        errors, warnings = check(result)
        print errors
        self.assertNotEqual(len(errors), 0)
        self.assertEqual(len(warnings), 0)




