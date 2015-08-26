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

import unittest
import tempfile
import os
import pytest

from calvin.utilities.calvinconfig import CalvinConfig


class TestBase(unittest.TestCase):

    def setUp(self):
        self.filepath = None
        f, self.filepath = tempfile.mkstemp()
        os.unlink(self.filepath)
        self._env = os.environ
        print "hej"

    def tearDown(self):
        if self.filepath and os.path.exists(self.filepath):
            os.unlink(self.filepath)
        print "da"
        os.environ = self._env


class CalvinConfigTests(TestBase):

    @unittest.skip("Currently, file is not created automatically")
    def test_create_default_config(self):

        self.assertEqual(os.path.exists(self.filepath), False)

        os.environ['CALVIN_CONFIG_PATH'] = self.filepath

        CalvinConfig()

        self.assertEqual(os.path.exists(self.filepath), True)

        with open(self.filepath, "rb") as f:
            content = f.readlines()

        self.assertGreater(len(content), 1)

    def test_set_get(self):
        self.assertEqual(os.path.exists(self.filepath), False)
        os.environ['CALVIN_CONFIG_PATH'] = self.filepath

        _conf = CalvinConfig()
        _conf.add_section("test")

        for a in range(10):
            _conf.set("test", "BANAN%d" % a, str(a))
            self.assertEqual(_conf.get("test", "BANAN%d" % a), str(a))

        for a in range(10):
            _conf.set("test", "BANAN%d" % a, a)
            self.assertEqual(_conf.get("test", "BANAN%d" % a), a)

        for a in range(10):
            _conf.set("test", "BANAN%d" % a, range(10))
            self.assertEqual(_conf.get("test", "BANAN%d" % a), range(10))

        # Should this two become the same ? No.
        for a in range(10):
            _conf.set("test", "BANAN%d" % a, dict(zip(range(10), range(10))))
            self.assertNotEqual(_conf.get("test", "BANAN%d" % a), dict(zip([str(x) for x in range(10)], range(10))))

        for a in range(10):
            _conf.set("test", "BANAN%d" % a, dict(zip([str(x) for x in range(10)], range(10))))
            self.assertEqual(_conf.get("test", "BANAN%d" % a), dict(zip([str(x) for x in range(10)], range(10))))

        for a in range(10):
            _conf.set("test", "BANAN%d" % a, dict(zip([str(x) for x in range(10)], [range(10)])))
            self.assertEqual(_conf.get("test", "BANAN%d" % a), dict(zip([str(x) for x in range(10)], [range(10)])))

    def test_env_override(self):
        # Env override is only allowed for known sections: GLOBAL, TESTING, DEVELOPER
        # Also, environment is read upon config creation
        self.assertEqual(os.path.exists(self.filepath), False)
        os.environ['CALVIN_CONFIG_PATH'] = self.filepath

        for a in range(10):
            os.environ['CALVIN_TESTING_APA%d' % a] = "100"
        _conf = CalvinConfig()

        for a in range(10):
            self.assertEqual(_conf.get("testing", "APA%d" % a), 100)

    def test_lists(self):
        self.assertEqual(os.path.exists(self.filepath), False)
        os.environ['CALVIN_CONFIG_PATH'] = self.filepath

        _conf = CalvinConfig()
        _conf.add_section("test")

        test_item = [str(x) for x in range(10)]
        _conf.set("test", "BANAN2", test_item)
        self.assertEqual(_conf.get("test", "BANAN2"), test_item)

    @pytest.mark.xfail()
    def test_env_override_list_append(self):
        self.assertEqual(os.path.exists(self.filepath), False)
        os.environ['CALVIN_CONFIG_PATH'] = self.filepath

        _conf = CalvinConfig()
        _conf.add_section("test")

        test_item = [str(x) for x in range(10)]
        _conf.set("test", "KAKA", test_item)
        os.environ['CALVIN_KAKA'] = "HEJ"
        self.assertEqual(_conf.get("test", "KAKA"), "HEJ")

        test_item = range(10)
        test_item2 = ["HEJ", "hej", "HEJ"]
        _conf.set("test", "KAKA", test_item)
        os.environ['CALVIN_KAKA'] = os.pathsep.join(test_item2)
        self.assertEqual(_conf.get("test", "KAKA"), test_item2 + test_item)

        test_item = [str(x) for x in range(10)]
        _conf.set("test", "KAKA", test_item)
        os.environ['CALVIN_KAKA'] = '["HEJ", "hej", "HEJ"]'
        self.assertEqual(_conf.get("test", "KAKA"), test_item2 + test_item)
