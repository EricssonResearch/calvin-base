import pytest
import unittest
import types
import inspect
from calvin.csparser.complete import Completion

class TestBase(unittest.TestCase):

    source_text = """
    component Foo() a -> b {
        flt : std.Identity()
        .a > flt.in
        flt.out > .b
    }
    src:std.Counter()
    snk:io.Print()
    log:io.Print()

    src.integer > snk.token, log.token
    """

    def setUp(self):
        completion = Completion()
        completion.set_source(inspect.cleandoc(self.source_text))
        self.completion = completion

    def tearDown(self):
        pass

class SanityCheck(TestBase):

    def test_sanity(self):
        completion = self.completion
        self.assertTrue(completion.metadata)
        self.assertTrue(completion.source)
        self.assertEqual(completion.source_lines[6], 'snk:io.Print()')
        self.assertEqual(completion.source_line(7), 'snk:io.Print()')
        completion._first_line_is_zero = True
        self.assertEqual(completion.source_lines[6], 'snk:io.Print()')
        self.assertEqual(completion.source_line(6), 'snk:io.Print()')


class ActorCompletionTests(TestBase):

    def test_completion_module(self):
        d = self.completion.complete(7, 4)
        self.assertEqual(set(d['suggestions']), set(self.completion.metadata.keys()))
        self.assertEqual('module', d['type'])

    def test_completion_module_partial(self):
        d = self.completion.complete(7, 5)
        self.assertEqual(set(d['suggestions']), set(['io']))
        self.assertEqual(set(d['completions']), set(['o']))

    def test_completion_module_partial2(self):
        d = self.completion.complete(6, 5)
        self.assertEqual(set(d['suggestions']), set(['std', 'sensor']))
        self.assertEqual(set(d['completions']), set(['td', 'ensor']))

    def test_completion_actor(self):
        d = self.completion.complete(6, 8)
        expected = self.completion.metadata['std'].keys()
        self.assertEqual(set(d['suggestions']), set(expected))
        self.assertEqual(set(d['completions']), set(expected))
        self.assertEqual('actor', d['type'])
        self.assertEqual(len(d['completions']), len(d['arg_dicts']))

    def test_completion_actor_partial(self):
        d = self.completion.complete(6, 10)
        expected = [x for x in self.completion.metadata['std'].keys() if x.startswith('Co')]
        self.assertEqual(set(d['suggestions']), set(expected))
        self.assertEqual(set(d['completions']), set([x[2:] for x in expected]))
        self.assertEqual(len(d['completions']), len(d['arg_dicts']))

class PortCompletionTests(TestBase):

    def test_outport(self):
        d = self.completion.complete(10, 4)
        self.assertEqual(set(d['suggestions']), set(['integer']))
        self.assertEqual(set(d['completions']), set(['integer']))
        self.assertEqual('outport', d['type'])

    def test_outport_partial(self):
        d = self.completion.complete(10, 6)
        self.assertEqual(set(d['suggestions']), set(['integer']))
        self.assertEqual(set(d['completions']), set(['teger']))

    def test_inport(self):
        d = self.completion.complete(10, 18)
        self.assertEqual(set(d['suggestions']), set(['token']))
        self.assertEqual(set(d['completions']), set(['token']))
        self.assertEqual('inport', d['type'])

    def test_inport_list(self):
        d = self.completion.complete(10, 29)
        self.assertEqual(set(d['suggestions']), set(['token']))
        self.assertEqual(set(d['completions']), set(['token']))
        self.assertEqual('inport', d['type'])

    def test_inport_partial(self):
        d = self.completion.complete(10, 20)
        self.assertEqual(set(d['suggestions']), set(['token']))
        self.assertEqual(set(d['completions']), set(['ken']))

    def test_outport_comp(self):
        d = self.completion.complete(4, 8)
        self.assertEqual(set(d['suggestions']), set(['token']))
        self.assertEqual(set(d['completions']), set(['token']))

class PortCompletionIncompleteSourceTests(PortCompletionTests):

    def setUp(self):
        super(PortCompletionIncompleteSourceTests, self).setUp()
        # Patch complete to truncate the source code
        cmpl = self.completion.complete
        def complete_trunc(self, lineno, col):
            if not self._first_line_is_zero:
                lineno = lineno - 1
            src_lines = self.source_lines[:lineno - 1] + [self.source_lines[lineno][:col]]
            src = "\n".join(src_lines)
            self.set_source(src)
            return cmpl(lineno, col)

        self.completion.complete = types.MethodType(complete_trunc, self.completion, Completion)



class PortPropertyCompletionTests(TestBase):

    @unittest.expectedFailure
    def test_outport(self):
        self.assertTrue(False)

class NoCompletions(TestBase):

    def test_completion_module(self):
        d = self.completion.complete(1, 3)
        self.assertEqual(set(d['suggestions']), set({}))