import pytest
import unittest
import types
import inspect
from calvin.csparser.parser import calvin_parse

class TestBase(unittest.TestCase):

    source_text = r'''
        define NODE1={"organization": "org.testexample", "name": "testNode1"}
        define NODE2={"organization": "org.testexample", "name": "testNode2"}


        define ARG=-1

        component Foo(arg) in -> out {
          """
          Foo(arg)
          Documentation please
          """

          init : flow.Init(data=arg)

          .in > init.in
          init.out > .out
        }

        src : Foo(arg=ARG)
        delay : std.ClassicDelay(delay=0.1)
        print : io.Print()

        src.out > print.token
        src.out > delay.token
        delay.token > src.in

        src.out(routing="round-robin")
        delay.token[in](routing="round-robin")

        # define rules
        rule src_rule: node_attr(node_name=NODE1)

        rule dst_rule: node_attr(node_name=NODE1) & node_attr(node_name={"name": "testNode2"})
        rule src_rule: node_attr(node_name=NODE1) | node_attr(node_name=NODE2) & ~current()
        rule combined_rule: dst_rule & src_rule | current()
        rule long: node_attr(node_name={"name": "testNode2"}) & node_attr(owner={"personOrGroup": "me"}) & node_attr(adress={"locality": "Lund"})
        rule not_rule: ~node_attr(node_name={"name": "testNode2"})

        # define a group
        group group_name: actor, some_group

        # apply rules, '*' indicates optional rule
        apply src: combined_rule
        apply delay, print: long
        apply src, print: dst_rule | node_attr(node_spec=NODE1) & ~current()
    '''

    def setUp(self):
        self.ir, self.it = calvin_parse(inspect.cleandoc(self.source_text))

    def tearDown(self):
        pass

class SanityCheck(TestBase):

    def test_sanity(self):
        from calvin.csparser import astprint
        # bp = astprint.BracePrinter()
        # bp.process(self.ir)

        self.assertTrue(self.ir)
        self.assertTrue(self.it)
        self.assertEqual(len(self.ir.children), 5)
        self.assertEqual(len(self.ir.children[4].children), 18)

        self.assertEqual(self.it.issue_count, 0)

