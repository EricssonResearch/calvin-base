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

from calvin.csparser.codegen import calvin_codegen
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

    def parse(self, test, source_text=None, verify=True):
        if not source_text:
            test = self.test_script_dir + test + '.calvin'
            source_text = self._read_file(test)

        deployable, issuetracker = calvin_codegen(source_text, test, verify=verify)
        errors = issuetracker.errors(sort_key='reason')
        warnings = issuetracker.warnings(sort_key='reason')

        return deployable, errors, warnings



class CalvinScriptCheckerTest(CalvinTestBase):
    """Test the CalvinsScript checker"""

    def testCheckSimpleScript(self):
        script = """
        a:std.CountTimer()
        b:io.Print()

        a.integer > b.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertFalse(errors)

    def testCheckSimpleScript2(self):
        script = """
        a:Foo()
        b:Bar()
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertTrue(errors)

    def testCheckLocalComponent(self):
        script = """
        component Foo() -> out {
            f:std.CountTimer()
            f.integer > .out
        }
        a:Foo()
        b:test.Sink()
        a.out > b.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertFalse(errors)

    def testCheckOutportConnections(self):
        script = """
        a:std.CountTimer()
        b:std.CountTimer()
        c:test.Sink()
        a.integer > c.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(errors[0]['reason'], "Actor b (std.CountTimer) is missing connection to outport 'integer'")

    def testCheckInportConnections1(self):
        script = """
        c:test.Sink()
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Actor c (test.Sink) is missing connection to inport 'token'")

    def testCheckInportConnections2(self):
        script = """
        a:std.CountTimer()
        b:std.CountTimer()
        c:test.Sink()
        a.integer > c.token
        b.integer > c.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        # self.assertEqual(errors[0]['reason'], "Input port 'c.token' with multiple connections ('a.integer') must have a routing port property.")
        # self.assertEqual(errors[1]['reason'], "Input port 'c.token' with multiple connections ('b.integer') must have a routing port property.")

    def testBadComponent1(self):
        script = """
        component Foo() -> out {
            a:std.CountTimer()
            b:std.CountTimer()
            a.integer > .out
        }
        a:Foo()
        b:test.Sink()
        a.out > b.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Actor b (std.CountTimer) is missing connection to outport 'integer'")

    def testBadComponent2(self):
        script = """
        component Foo() -> out {
            a:std.CountTimer()
            b:test.Sink()
            a.integer > b.token
        }
        a:Foo()
        b:test.Sink()
        a.out > b.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Component Foo is missing connection to outport 'out'")

    def testBadComponent3(self):
        script = """
        component Foo() -> out {
            a:std.CountTimer()
            a.integer > .out
            a.integer > .out
        }
        a:Foo()
        b:test.Sink()
        a.out > b.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        # self.assertEqual(errors[0]['reason'], "Input port 'b.token' with multiple connections ('a:a.integer') must have a routing port property.")

    def testBadComponent4(self):
        script = """
        component Foo() in -> {
            a:test.Sink()
        }
        b:Foo()
        a:std.CountTimer()
        a.integer > b.in
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['reason'], "Actor a (test.Sink) is missing connection to inport 'token'")
        self.assertEqual(errors[1]['reason'], "Component Foo is missing connection to inport 'in'")

    def testBadComponent5(self):
        script = """
        component Foo() in -> {
            a:test.Sink()
            .foo > a.token
        }
        b:Foo()
        a:std.CountTimer()
        a.integer > b.in
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['reason'], "Component Foo has no inport 'foo'")
        self.assertEqual(errors[1]['reason'], "Component Foo is missing connection to inport 'in'")

    def testBadComponent6(self):
        script = """
        component Foo() -> out {
            a:std.CountTimer()
            a.integer > .foo
        }
        b:Foo()
        a:test.Sink()
        b.out > a.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['reason'], "Component Foo has no outport 'foo'")
        self.assertEqual(errors[1]['reason'], "Component Foo is missing connection to outport 'out'")

    def testBadComponent7(self):
        script = """
        component Foo() in -> out {
            .in > .out
        }
        """
        result, errors, warnings = self.parse('inline', script)
        print errors
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Component inport connected directly to outport.")



    def testUndefinedActors(self):
        script = """
        a.token > b.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['reason'], "Undefined actor: 'a'")
        self.assertEqual(errors[1]['reason'], "Undefined actor: 'b'")


    def testUndefinedArguments(self):
        script = """
        a:std.Constant()
        b:test.Sink()
        a.token > b.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Missing argument: 'data'")

    def testExcessArguments(self):
        script = """
        a:std.Constant(data=1, bar=2)
        b:test.Sink()
        a.token > b.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Excess argument: 'bar'")


    def testComponentUndefinedArgument(self):
        script = """
        component Foo(file) in -> {
            a:test.Sink()
            .in > a.token
        }
        b:Foo()
        a:std.CountTimer()
        a.integer > b.in
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['reason'], "Missing argument: 'file'")
        self.assertEqual(errors[1]['reason'], "Unused argument: 'file'")

    def testComponentUnusedArgument(self):
        script = """
        component Foo(file) in -> {
            a:test.Sink()
            .in > a.token
        }
        b:Foo(file="Foo.txt")
        a:std.CountTimer()
        a.integer > b.in
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Unused argument: 'file'")

    def testComponentExcessArgument(self):
        script = """
        component Foo(file) -> out {
            file > .out
        }
        a:Foo(file="Foo.txt", bar=1)
        b:io.Print()
        a.out > b.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Excess argument: 'bar'")


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
        c:test.Sink()

        a.integer > b.in
        b.out > c.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

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
        c:test.Sink()

        a.integer > b.in
        b.out > c.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testLocalBadComponentCauseCrash1(self):
        script = """
        component Foo() in -> out {
          snk1 : io.Print()
          .in  > snk1.token
        }
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)

    def testLocalBadComponentCauseCrash2(self):
        script = """
        component Foo() in -> out {
          snk1 : io.Print()
          .in  > snk1.token
        }
        foo : Foo()
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 3)
        self.assertEqual(errors[0]['reason'], "Component Foo is missing connection to outport 'out'")
        self.assertEqual(errors[1]['reason'], "Component foo (local.Foo) is missing connection to inport 'in'")
        self.assertEqual(errors[2]['reason'], "Component foo (local.Foo) is missing connection to outport 'out'")

    def testLocalBadComponentCauseCrash3(self):
        script = """
        component Foo() in -> out {
          snk1 : io.Print()
          .in  > snk1.token
        }
        foo : Foo()
        1 > foo.in
        """
        result, errors, warnings = self.parse('inline', script)
        print errors
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['reason'], "Component Foo is missing connection to outport 'out'")
        self.assertEqual(errors[1]['reason'], "Component foo (local.Foo) is missing connection to outport 'out'")


    def testNoSuchPort(self):
        script = """
        i:std.Identity()
        src:std.CountTimer()
        dst:test.Sink()
        src.integer > i.foo
        i.bar > dst.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 4)
        self.assertEqual(errors[0]['reason'], "Actor i (std.Identity) has no inport 'foo'")
        self.assertEqual(errors[1]['reason'], "Actor i (std.Identity) has no outport 'bar'")
        self.assertEqual(errors[2]['reason'], "Actor i (std.Identity) is missing connection to inport 'token'")
        self.assertEqual(errors[3]['reason'], "Actor i (std.Identity) is missing connection to outport 'token'")

    def testRedefineInstance(self):
        script = """
        i:std.Identity()
        src:std.CountTimer()
        dst:test.Sink()
        i:std.ClassicDelay(delay=0.2)
        src.integer > i.token
        i.token > dst.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Instance identifier 'i' redeclared")

    def testUndefinedActorInComponent(self):
        script = """
        component Bug() -> out {
          b.out > .out
        }
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)


    def testUndefinedConstant(self):
        script = """
        src : std.Constant(data=FOO)
        snk : test.Sink()
        src.token > snk.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Undefined identifier: 'FOO'")

    @pytest.mark.xfail()
    def testUnusedConstant(self):
        script = """
        define FOO=2
        sink : flow.Terminator()
        1 > sink.void
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Unused constant: 'FOO'")


    def testDefinedConstant(self):
        script = """
        define FOO = 42
        src : std.Constant(data=FOO)
        snk : test.Sink()
        src.token > snk.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testUndefinedRecursiveConstant(self):
        script = """
        define FOO = BAR
        src : std.Constant(data=FOO)
        snk : test.Sink()
        src.token > snk.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['reason'], "Constant 'BAR' is undefined")
        self.assertEqual(errors[1]['reason'], "Undefined identifier: 'FOO'")


    def testDefinedRecursiveConstant(self):
        script = """
        define FOO = BAR
        define BAR = 42
        src : std.Constant(data=FOO)
        snk : test.Sink()
        src.token > snk.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)


    def testLiteralOnPort(self):
        script = """
        snk : test.Sink()
        42 > snk.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testComponentArgumentOnInternalPort(self):
        script = """
        component Foo(foo) -> out {
            foo > .out
        }
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testLiteralOnInternalPort(self):
        script = """
        component Foo() -> out {
            1 > .out
        }
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)


    def testBadLocalPort(self):
        script = """
        component Foo() in -> {
            snk : test.Sink()
            .in > snk.token
        }
        src : std.Counter()
        src.integer > .in
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Internal port '.in' outside component definition")


    def testVoidOnInPort(self):
        script = """
        iip : flow.Init(data="ping")
        print : io.Print()
        voidport > iip.in
        iip.out > print.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]['reason'], "Using 'void' as input to 'iip.in'")


    def testVoidOnOutPort(self):
        script = """
        src : std.Counter()
        src.integer > voidport
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testVoidInvalidUse1(self):
        script = """
        component Foo() in -> {
            .in > voidport
        }
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Syntax error.")

    def testVoidInvalidUse2(self):
        script = """
        component Bar() -> out {
            voidport > .out
        }
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Syntax error.")

    def testVoidInvalidUse3(self):
        script = """
        1 > voidport
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Syntax error.")

    def testVoidInvalidUse4(self):
        script = """
        define BAR=1
        BAR > voidport
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Syntax error.")

    def testPortlist2(self):
        script = """
        src : std.Counter()
        snk1 : io.Print()
        snk2 : io.Print()
        src.integer > snk1.token, snk2.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testPortlist3(self):
        script = """
        src : std.Counter()
        snk1 : io.Print()
        snk2 : io.Print()
        snk3 : io.Print()
        src.integer > snk1.token, snk2.token, snk3.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testPortlistLiteral(self):
        script = """
        snk1 : io.Print()
        snk2 : io.Print()
        1 > snk1.token, snk2.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)


    def testPortlistInternalOutPort(self):
        script = """
        component Foo() in ->  {
            snk1 : io.Print()
            snk2 : io.Print()
            .in  > snk1.token , snk2.token
        }
        snk : Foo()
        1 > snk.in
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testPortlistInternalInPort(self):
        script = """
        component Foo() -> out {
            snk1 : io.Print()
            snk2 : io.Print()
            1  > snk1.token, snk2.token, .out
        }
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testPortlistInternalInPort2(self):
        script = """
        component Foo() -> out {
            snk1 : io.Print()
            snk2 : io.Print()
            src : std.Counter()
            src.integer  > snk1.token, snk2.token, .out
        }
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)


    def testPortlistInternalOutPortPassthrough(self):
        script = """
        component Foo() in -> out {
            snk1 : io.Print()
            .in  > snk1.token, .out
        }
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['reason'], "Component inport connected directly to outport.")

    def testTokenTransform(self):
        script = """
        snk1 : io.Print()
        1 > /2/ snk1.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testTokenTransformBad(self):
        script = """
        snk1 : io.Print()
        1 /2/ > snk1.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 2)

    def testTokenTransformInternalInport(self):
        script = """
        component Foo() in ->  {
            snk1 : io.Print()
            .in  > /2/ snk1.token
        }
        f : Foo()
        1 > f.in
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testTokenTransformInternalInportBad(self):
        script = """
        component Foo() in ->  {
            snk1 : io.Print()
            .in /2/ > snk1.token
        }
        f : Foo()
        1 > f.in
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 4)

    def testTokenTransformInternalOutport(self):
        script = """
        component Foo()  -> out {

            1 > /2/ .out
        }
        f : Foo()
        f.out > voidport
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testTokenTransformInternalOutportBad(self):
        script = """
        component Foo()  -> out {

            1 /2/ >  .out
        }
        f : Foo()
        f.out > voidport
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 3)

    def testStringLiteral(self):
        # N.B raw string (r"") required to have same behaviour as script file
        script = r"""
        out: io.Print()
        "{\"x\": \"X\n\"}" > out.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testStringLiteralNoLinebreaks(self):
        # N.B raw string (r"") required to have same behaviour as script file
        script = r"""
        define FOO = "abc
                      def"
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)

    def testStringLiteralConcatenation(self):
        # N.B raw string (r"") required to have same behaviour as script file
        script = r"""
        define FOO = "abc\n"
                     "def"
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testLabelConstant(self):
        script = r"""
        print1 : io.Print()
        print2 : io.Print()
        :foo 1 > print1.token
        foo.token > print2.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testLabelConstantify(self):
        script = r"""
        print1 : io.Print()
        print2 : io.Print()
        1 > /:foo 2/ print1.token
        foo.out > print2.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testPortRef(self):
        script = r"""
        print1 : io.Print()
        &print1.token >  print1.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    @pytest.mark.xfail()
    def testPortRefMissingSyntaxCheck(self):
        # FIXME: io.Print has no outport
        script = r"""
        print1 : io.Print()
        &print1.token[out] >  print1.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)

    @pytest.mark.xfail()
    def testPortRefAsKey(self):
        script = r"""
        print1 : io.Print()
        {&print1.token:"Comment"} >  print1.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertTrue(len(errors) > 0)

    def testAmbigousPortProperty1(self):
        script = r"""
        i : std.Identity()
        src : std.CountTimer()
        snk : io.Print()
        src.integer > i.token
        i.token > snk.token
        i.token(routing="round-robin")
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 2)

    def testAmbigousPortProperty2(self):
        script = r"""
        i : std.Identity()
        src : std.CountTimer()
        snk : io.Print()
        src.integer > i.token
        i.token > snk.token
        i.token[in](routing="round-robin")
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 1)

    def testAmbigousPortProperty3(self):
        script = r"""
        i : std.Identity()
        src : std.CountTimer()
        snk : io.Print()
        src.integer > i.token
        i.token > snk.token
        i.token[out](routing="round-robin")
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertEqual(len(errors), 0)

    def testComponentToComponent1(self):
        script = r"""
        component InComp() in -> {
            out : io.Print()
            .in > out.token
        }

        component OutComp() -> out {
            trig : std.Trigger(data="No data", tick=1.0)
            trig.data > .out
        }

        out_comp : OutComp()
        in_comp : InComp()

        out_comp.out > in_comp.in
        """
        result, errors, warnings = self.parse('inline', script)
        for e in errors:
            print e['reason']
        self.assertEqual(len(errors), 0)

    def testCompToCompWithFanoutFromInternalInport(self):
        script = r"""
        component Left() -> out {
            src : std.Trigger(tick=1, data=true)
            src.data > .out
        }
        component Right() in ->  {
            a : io.Print()
            b : io.Print()
            .in > a.token, b.token
        }
        src : Left()
        snk : Right()
        src.out > snk.in
        """
        result, errors, warnings = self.parse('inline', script)
        for e in errors:
            print e['reason']
        self.assertEqual(len(errors), 0)



