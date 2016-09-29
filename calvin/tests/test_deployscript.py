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

from calvin.csparser.dscodegen import calvin_dscodegen
import unittest
import json
import difflib
import pytest
import pprint

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

    def parse(self, test, source_text=None):
        if not source_text:
            test = self.test_script_dir + test + '.calvin'
            source_text = self._read_file(test)

        requirements, issuetracker = calvin_dscodegen(source_text, test)
        errors = issuetracker.errors(sort_key='reason')
        warnings = issuetracker.warnings(sort_key='reason')

        return requirements, errors, warnings



class DeployScriptCheckerTest(CalvinTestBase):
    """Test the DeployScript checker"""

    def testCheckSimpleScript1(self):
        script = """
        a:std.CountTimer()
        b:io.Print()

        a.integer > b.token
        
        rule simple: node_attr(node_name={"name": "simple_rt"})
        apply a, b: simple 
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertFalse(errors)
        pprint.pprint(result)

    def testCheckSimpleScript2(self):
        script = """
        a:std.CountTimer()
        b:io.Print()

        a.integer > b.token
        
        rule simple: node_attr(node_name={"name": "simple_rt"}) & node_attr(owner={"personOrGroup": "me"})
        apply a, b: simple 
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertFalse(errors)
        pprint.pprint(result)

    def testCheckSimpleScript3(self):
        script = """
        a:std.CountTimer()
        b:io.Print()

        a.integer > b.token
        
        rule simple: node_attr(node_name={"name": "simple_rt1"}) | node_attr(node_name={"name": "simple_rt2"})
        apply a, b: simple 
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertFalse(errors)
        pprint.pprint(result)

    def testCheckHierarchicalScript1(self):
        script = """
        a:std.CountTimer()
        b:io.Print()

        a.integer > b.token
        
        rule union: node_attr(node_name={"name": "simple_rt1"}) | node_attr(node_name={"name": "simple_rt2"})
        rule hierarchical: union & ~current()
        apply a, b: hierarchical 
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertFalse(errors)
        pprint.pprint(result)

    def testCheckOnlyDeployScript(self):
        script = """
        rule union: node_attr(node_name={"name": "simple_rt1"}) | node_attr(node_name={"name": "simple_rt2"})
        rule hierarchical: union & ~current()
        apply a, b: hierarchical 
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertFalse(errors)
        pprint.pprint(result)

    def testCheckOnlyCalvinScript(self):
        script = """
        a:std.CountTimer()
        b:io.Print()

        a.integer > b.token
        """
        result, errors, warnings = self.parse('inline', script)
        self.assertFalse(errors)
        pprint.pprint(result)
