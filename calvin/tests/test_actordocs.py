import pytest
import unittest
import json
from calvin.actorstore.store import DocumentationStore

class TestBase(unittest.TestCase):

    def setUp(self):
        self.ds = DocumentationStore()

    def tearDown(self):
        pass

class SanityCheck(TestBase):

    def test_sanity(self):
        self.assertTrue(self.ds)
        self.assertTrue(self.ds.docs)

class ModuleDocs(TestBase):

    def test_help_root_no_args(self):
        actual = self.ds.help(compact=True)
        self.assertEqual("Calvin", actual[:6])

    def test_help_root_arg_none(self):
        actual = self.ds.help(what=None, compact=True)
        self.assertEqual("Calvin", actual[:6])

    def test_help_root_arg_empty_string(self):
        actual = self.ds.help(what="", compact=True)
        self.assertEqual("Calvin", actual[:6])

    def test_help_raw_root_no_args(self):
        actual = json.loads(self.ds.help_raw())
        self.assertTrue(actual['modules'])
        self.assertTrue('std' in actual['modules'])
        self.assertFalse(actual['actors'])

    def test_help_raw_root_arg_none(self):
        actual = json.loads(self.ds.help_raw(what=None))
        self.assertTrue(actual['modules'])
        self.assertTrue('std' in actual['modules'])
        self.assertFalse(actual['actors'])

    def test_help_raw_root_arg_empty_string(self):
        actual = json.loads(self.ds.help_raw(what=""))
        self.assertEqual(actual['short_desc'], 'A systematic approach to handling impedance mismatch in IoT.')

    def test_help_raw_flow(self):
        actual = json.loads(self.ds.help_raw(what='flow'))
        self.assertEqual(set(['is_known', 'long_desc', 'short_desc', 'modules', 'actors']), set(actual.keys()))
        self.assertTrue(actual['actors'])
        self.assertTrue('Init' in actual['actors'])

    def test_help_raw_flow_init(self):
        actual = json.loads(self.ds.help_raw('flow.Init'))
        self.assertTrue(actual['is_known'])
        self.assertEqual(set(['inputs', 'name', 'outputs', 'args', 'is_known', 'ns', 'type', 'long_desc', 'short_desc', 'output_properties', 'input_properties', 'requires', 'input_docs', 'output_docs']), set(actual.keys()))

    def test_help_raw_unknown(self):
        actual = json.loads(self.ds.help_raw(what='no_such_thing'))
        self.assertEqual(actual['short_desc'], 'No such entity')

    def test_help_raw_qualified_unknown(self):
        actual = json.loads(self.ds.help_raw(what='no.such.thing'))
        self.assertEqual(actual['short_desc'], 'No such entity')

    def test_metadata_std(self):
        # For actors only
        actual = self.ds.metadata('std')
        self.assertFalse(actual['is_known'])

    def test_metadata_flow_init(self):
        actual = self.ds.metadata('flow.Init')
        self.assertTrue(actual['is_known'])
        self.assertEqual(set(['inputs', 'name', 'outputs', 'args', 'is_known', 'ns', 'type', 'output_properties', 'input_properties', 'requires']), set(actual.keys()))
