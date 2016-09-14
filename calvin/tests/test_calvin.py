# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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
import time
import pytest

from calvin.csparser import cscompile as compiler
from calvin.Tools import cscompiler as compile_tool
from calvin.Tools import deployer
from calvin.utilities import calvinlogger
from calvin.requests.request_handler import RequestHandler
from . import helpers

_log = calvinlogger.get_logger(__name__)


def absolute_filename(filename):
    import os.path
    return os.path.join(os.path.dirname(__file__), filename)


rt1 = None
rt2 = None
rt3 = None
test_type = None
request_handler = None


def deploy_app(deployer, runtimes=None):
    runtimes = runtimes if runtimes else [ deployer.runtime ]
    return helpers.deploy_app(request_handler, deployer, runtimes)
    
def expected_tokens(rt, actor_id, t_type='seq'):
    return helpers.expected_tokens(request_handler, rt, actor_id, t_type)

def wait_for_tokens(rt, actor_id, size=5, retries=20):
    return helpers.wait_for_tokens(request_handler, rt, actor_id, size, retries)
    
def actual_tokens(rt, actor_id, size=5, retries=20):
    return helpers.actual_tokens(request_handler, rt, actor_id, size, retries)

def get_runtime(n=1):
    import random
    runtimes = [rt1, rt2, rt3]
    random.shuffle(runtimes)
    return runtimes[:n]
  
def setup_module(module):
    global rt1, rt2, rt3
    global request_handler
    global test_type

    request_handler = RequestHandler()
    test_type, [rt1, rt2, rt3] = helpers.setup_test_type(request_handler)


def teardown_module(module):
    global rt1
    global rt2
    global rt3
    global test_type
    global request_handler

    helpers.teardown_test_type(request_handler, [rt1, rt2, rt3], test_type)


class CalvinTestBase(unittest.TestCase):

    def setUp(self):
        self.rt1 = rt1
        self.rt2 = rt2
        self.rt3 = rt3

    def assert_lists_equal(self, expected, actual, min_length=5):
        self.assertTrue(len(actual) >= min_length, "Received data too short (%d), need at least %d" % (len(actual), min_length))
        self._assert_lists_equal(expected, actual)

    def _assert_lists_equal(self, expected, actual):
        assert actual
        assert reduce(lambda a, b: a and b[0] == b[1], zip(expected, actual), True) 
        
    def compile_script(self, script, name):
        # Instead of rewriting tests after compiler.compile_script changed
        # from returning app_info, errors, warnings to app_info, issuetracker
        # use this stub in tests to keep old behaviour
        app_info, issuetracker = compiler.compile_script(script, name)
        return app_info, issuetracker.errors(), issuetracker.warnings()

    def wait_for_migration(self, runtime, actors, retries=20):
        retry = 0
        if not isinstance(actors, list):
            actors = [ actors ]
        while retry < retries:
            try:
                for actor in actors:
                    request_handler.get_actor(runtime, actor)
                break
            except Exception:
                _log.info("Migration not finished, retrying in %d" % (retry,))
                retry += 1
                time.sleep(retry)

    def migrate(self, source, dest, actor):
        request_handler.migrate(source, actor, dest.id)
        self.wait_for_migration(dest, [actor])

@pytest.mark.slow
@pytest.mark.essential
class TestNodeSetup(CalvinTestBase):

    """Testing starting a node"""

    def testStartNode(self):
        """Testing starting node"""

        assert request_handler.get_node(self.rt1, self.rt1.id)['uri'] == self.rt1.uri


@pytest.mark.essential
@pytest.mark.slow
class TestLocalConnectDisconnect(CalvinTestBase):

    """Testing local connect/disconnect/re-connect"""

    def testLocalSourceSink(self):
        """Testing local source and sink"""

        rt = self.rt1

        # Setup
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        request_handler.connect(rt, snk, 'token', rt.id, src, 'integer')

        # Wait for some tokens to arrive
        wait_for_tokens(rt, snk)

        # Check what was sent
        expected = expected_tokens(rt, src, 'seq')
        # Wait for it to arrive
        actual = actual_tokens(rt, snk, len(expected))

        request_handler.disconnect(rt, src)
        
        # Assert the sent and arrived are identical
        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, snk)

    def testLocalConnectDisconnectSink(self):
        """Testing local connect/disconnect/re-connect on sink"""

        rt = self.rt1

        src = request_handler.new_actor(rt, "std.CountTimer", "src")
        snk = request_handler.new_actor_wargs(rt, "io.StandardOut", "snk", store_tokens=1, quiet=1)

        request_handler.connect(rt, snk, 'token', rt.id, src, 'integer')

        # Wait for some tokens
        actual = wait_for_tokens(rt, snk)

        # Disconnect/reconnect
        request_handler.disconnect(rt, snk)
        request_handler.connect(rt, snk, 'token', rt.id, src, 'integer')
        
        # Wait for at least one more token
        wait_for_tokens(rt, snk, len(actual)+1)

        # Fetch what was sent/received
        expected = expected_tokens(rt, src, 'seq')
        actual = actual_tokens(rt, snk, len(expected))

        request_handler.disconnect(rt, snk)

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, snk)

    def testLocalConnectDisconnectSource(self):
        """Testing local connect/disconnect/re-connect on source"""

        rt = self.rt1

        src = request_handler.new_actor(rt, "std.CountTimer", "src")
        snk = request_handler.new_actor_wargs(rt, "io.StandardOut", "snk", store_tokens=1, quiet=1)
        request_handler.connect(rt, snk, "token", rt.id, src, "integer")
        
        # Wait for some tokens
        actual = wait_for_tokens(rt, snk)
        
        # disconnect/reconnect
        request_handler.disconnect(rt, src)
        request_handler.connect(rt, snk, "token", rt.id, src, "integer")
        
        # Wait for one more token
        wait_for_tokens(rt, snk, len(actual)+1)

        # Fetch what was sent/received
        expected = expected_tokens(rt, src, 'seq')
        actual = actual_tokens(rt, snk, len(expected))

        request_handler.disconnect(rt, src)

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, snk)

    def testLocalConnectDisconnectFilter(self):
        """Testing local connect/disconnect/re-connect on filter"""

        rt = self.rt1

        src = request_handler.new_actor(rt, "std.CountTimer", "src")
        csum = request_handler.new_actor(rt, "std.Sum", "sum")
        snk = request_handler.new_actor_wargs(rt, "io.StandardOut", "snk", store_tokens=1, quiet=1)

        request_handler.connect(rt, snk, "token", rt.id, csum, "integer")
        request_handler.connect(rt, csum, "integer", rt.id, src, "integer")
        
        # Wait for some tokens
        actual = wait_for_tokens(rt, snk)

        # disconnect/reconnect
        request_handler.disconnect(rt, csum)
        request_handler.connect(rt, snk, "token", rt.id, csum, "integer")
        request_handler.connect(rt, csum, "integer", rt.id, src, "integer")
      
        # Wait for one more token
        wait_for_tokens(rt, snk, len(actual)+1)
        
        # Fetch sent/received
        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))

        request_handler.disconnect(rt, src)

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, csum)
        request_handler.delete_actor(rt, snk)

    def testTimerLocalSourceSink(self):
        """Testing timer based local source and sink"""

        rt = self.rt1

        src = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src', sleep=0.1, steps=10)
        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        request_handler.connect(rt, snk, 'token', rt.id, src, 'integer')

        # Wait for some tokens
        wait_for_tokens(rt, snk)

        # Check what was sent/received
        expected = expected_tokens(rt, src, 'seq')
        actual = actual_tokens(rt, snk, len(expected))

        request_handler.disconnect(rt, src)

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, snk)


@pytest.mark.essential
@pytest.mark.slow
class TestRemoteConnection(CalvinTestBase):

    """Testing remote connections"""

    def testRemoteOneActor(self):
        """Testing remote port"""

        rt = self.rt1
        peer = self.rt2

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer.id, csum, 'integer')
        request_handler.connect(peer, csum, 'integer', rt.id, src, 'integer')
        
        # Wait for some tokens
        actual = wait_for_tokens(rt, snk, 10)

        request_handler.disconnect(rt, src)

        # Fetch sent
        expected = expected_tokens(rt, src, 'sum')
        
        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, csum)
        request_handler.delete_actor(rt, src)

    def testRemoteSlowPort(self):
        """Testing remote slow port and that token flow control works"""

        rt = self.rt1
        peer = self.rt2

        snk1 = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk1', store_tokens=1, quiet=1)
        alt = request_handler.new_actor(peer, 'std.Alternate', 'alt')
        src1 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src1', sleep=0.1, steps=100)
        src2 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src2', sleep=1.0, steps=10)

        request_handler.connect(rt, snk1, 'token', peer.id, alt, 'token')
        request_handler.connect(peer, alt, 'token_1', rt.id, src1, 'integer')
        request_handler.connect(peer, alt, 'token_2', rt.id, src2, 'integer')
        
        actual = wait_for_tokens(rt, snk1, 10)

        request_handler.disconnect(rt, src1)
        request_handler.disconnect(rt, src2)

        expected_1 = expected_tokens(rt, src1, 'seq')
        expected_2 = expected_tokens(rt, src2, 'seq')
        expected = helpers.flatten_zip(zip(expected_1, expected_2))

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, snk1)
        request_handler.delete_actor(peer, alt)
        request_handler.delete_actor(rt, src1)
        request_handler.delete_actor(rt, src2)

    def testRemoteSlowFanoutPort(self):
        """Testing remote slow port with fan out and that token flow control works"""

        rt = self.rt1
        peer = self.rt2

        snk1 = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(peer, 'io.StandardOut', 'snk2', store_tokens=1, quiet=1)
        alt = request_handler.new_actor(peer, 'std.Alternate', 'alt')
        src1 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src1', sleep=0.1, steps=100)
        src2 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src2', sleep=1.0, steps=10)

        request_handler.connect(rt, snk1, 'token', peer.id, alt, 'token')
        request_handler.connect(peer, snk2, 'token', rt.id, src1, 'integer')
        request_handler.connect(peer, alt, 'token_1', rt.id, src1, 'integer')
        request_handler.connect(peer, alt, 'token_2', rt.id, src2, 'integer')
        
        # Wait for some tokens
        actual_1 = wait_for_tokens(rt, snk1, 10)
        actual_2 = wait_for_tokens(peer, snk2, 10)
        
        request_handler.disconnect(rt, src1)
        request_handler.disconnect(rt, src2)
        
        expected_1 = expected_tokens(rt, src1, 'seq')
        expected_2 = expected_tokens(rt, src2, 'seq')
        expected = helpers.flatten_zip(zip(expected_1, expected_2))

        self.assert_lists_equal(expected, actual_1)
        self.assert_lists_equal(expected_1, actual_2)

        request_handler.delete_actor(rt, snk1)
        request_handler.delete_actor(peer, snk2)
        request_handler.delete_actor(peer, alt)
        request_handler.delete_actor(rt, src1)
        request_handler.delete_actor(rt, src2)

@pytest.mark.essential
@pytest.mark.slow
class TestActorMigration(CalvinTestBase):

    def testOutPortRemoteToLocalMigration(self):
        """Testing outport remote to local migration"""

        rt = self.rt1
        peer = self.rt2
        
        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer.id, csum, 'integer')
        request_handler.connect(peer, csum, 'integer', rt.id, src, 'integer')
        
        actual_1 = wait_for_tokens(rt, snk)
        
        self.migrate(rt, peer, src)
        
        # Wait for at least queue + 1 tokens
        wait_for_tokens(rt, snk, len(actual_1)+5)
        expected = expected_tokens(peer, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        
        self.assert_lists_equal(expected, actual)
        
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, csum)
        request_handler.delete_actor(peer, src)

    def testFanOutPortLocalToRemoteMigration(self):
        """Testing outport with fan-out local to remote migration"""

        rt = self.rt1
        peer = self.rt2

        src = request_handler.new_actor_wargs(rt, "std.CountTimer", "src", sleep=0.1, steps=100)
        snk_1 = request_handler.new_actor_wargs(rt, "io.StandardOut", "snk-1", store_tokens=1, quiet=1)
        snk_2 = request_handler.new_actor_wargs(rt, "io.StandardOut", "snk-2", store_tokens=1, quiet=1)

        request_handler.set_port_property(rt, src, 'out', 'integer',
                                            port_properties={'routing': 'fanout', 'nbr_peers': 2})

        request_handler.connect(rt, snk_1, 'token', rt.id, src, 'integer')
        request_handler.connect(rt, snk_2, 'token', rt.id, src, 'integer')
        wait_for_tokens(rt, snk_1)
        wait_for_tokens(rt, snk_2)

        expected = expected_tokens(rt, src, 'seq')
        actual_1 = actual_tokens(rt, snk_1, len(expected))
        self.assert_lists_equal(expected, actual_1)

        expected = expected_tokens(rt, src, 'seq')
        actual_2 = actual_tokens(rt, snk_2, len(expected))

        self.assert_lists_equal(expected, actual_2)

        self.migrate(rt, peer, src)

        # Make sure that we got at least 5 more tokens since we could have transfered but unprocessed in queue
        wait_for_tokens(rt, snk_1, len(actual_1)+5)
        
        expected = expected_tokens(peer, src, 'seq')
        actual = actual_tokens(rt, snk_1, len(expected))
        self.assert_lists_equal(expected, actual)

        # Make sure that we got at least 5 more tokens since we could have transfered but unprocessed in queue
        wait_for_tokens(rt, snk_2, len(actual_2)+5)
        expected = expected_tokens(peer, src, 'seq')
        actual = actual_tokens(rt, snk_2, len(expected))
        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(peer, src)
        request_handler.delete_actor(rt, snk_1)
        request_handler.delete_actor(rt, snk_2)

    def testFanOutPortRemoteToLocalMigration(self):
        """Testing outport with fan-out remote to local migration"""

        rt = self.rt1
        peer = self.rt2

        snk1 = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(peer, 'io.StandardOut', 'snk2', store_tokens=1, quiet=1)
        alt = request_handler.new_actor(peer, 'std.Alternate', 'alt')
        src1 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src1', sleep=0.1, steps=100)
        src2 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src2', sleep=0.1, steps=100)

        request_handler.set_port_property(peer, alt, 'out', 'token',
                                            port_properties={'routing': 'fanout', 'nbr_peers': 2})

        request_handler.connect(rt, snk1, 'token', peer.id, alt, 'token')
        request_handler.connect(peer, snk2, 'token', peer.id, alt, 'token')
        request_handler.connect(peer, alt, 'token_1', rt.id, src1, 'integer')
        request_handler.connect(peer, alt, 'token_2', rt.id, src2, 'integer')
        wait_for_tokens(rt, snk1)
        wait_for_tokens(peer, snk2)

        expected_1 = expected_tokens(rt, src1, 'seq')
        expected_2 = expected_tokens(rt, src2, 'seq')
        expected = helpers.flatten_zip(zip(expected_1, expected_2))

        actual = actual_tokens(rt, snk1, len(expected))
        snk1_0 = len(actual)
        self.assert_lists_equal(expected, actual)

        actual = actual_tokens(peer, snk2, len(expected))
        snk2_0 = len(actual)
        self.assert_lists_equal(expected, actual)

        self.migrate(rt, peer, snk1)

        # Make sure that we got at least 5 more tokens since we could have transfered but unprocessed in queue
        wait_for_tokens(peer, snk1, snk1_0+5)
        wait_for_tokens(peer, snk2, snk2_0+5)
        
        expected_1 = expected_tokens(rt, src1, 'seq')
        expected_2 = expected_tokens(rt, src2, 'seq')
        expected = helpers.flatten_zip(zip(expected_1, expected_2))


        actual = actual_tokens(peer, snk1, len(expected))
        self.assert_lists_equal(expected, actual)

        actual = actual_tokens(peer, snk2, len(expected))
        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(peer, snk1)
        request_handler.delete_actor(peer, snk2)
        request_handler.delete_actor(peer, alt)
        request_handler.delete_actor(rt, src1)
        request_handler.delete_actor(rt, src2)

    def testOutPortLocalToRemoteMigration(self):
        """Testing outport local to remote migration"""

        rt = self.rt1
        peer = self.rt2

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(peer, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer.id, csum, 'integer')
        request_handler.connect(peer, csum, 'integer', peer.id, src, 'integer')
        wait_for_tokens(rt, snk)

        actual_1 = actual_tokens(rt, snk)
        self.migrate(peer, rt, src)
        
        # Make sure that we got at least 5 more tokens since we could have transfered but unprocessed in queue
        wait_for_tokens(rt, snk, len(actual_1)+5)
        
        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        self.assert_lists_equal(expected, actual)
        
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, csum)
        request_handler.delete_actor(rt, src)

    def testOutPortLocalRemoteRepeatedMigration(self):
        """Testing outport local to remote migration and back repeatedly"""

        rt = self.rt1
        peer = self.rt2

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(peer, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer.id, csum, 'integer')
        request_handler.connect(peer, csum, 'integer', peer.id, src, 'integer')
        
        wait_for_tokens(rt, snk)

        actual_x = actual_tokens(rt, snk)
        for i in range(5):
            if i % 2 == 0:
                self.migrate(peer, rt, src)
            else:
                self.migrate(rt, peer, src)
            actual_x = actual_tokens(rt, snk, len(actual_x)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        self.assert_lists_equal(expected, actual)
        
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, csum)
        request_handler.delete_actor(rt, src)

    def testInOutPortRemoteToLocalMigration(self):
        """Testing out- and inport remote to local migration"""

        rt = self.rt1
        peer = self.rt2

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer.id, csum, 'integer')
        request_handler.connect(peer, csum, 'integer', rt.id, src, 'integer')

        actual_1 = wait_for_tokens(rt, snk)

        self.migrate(peer, rt, csum)

        wait_for_tokens(rt, snk, len(actual_1)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        self.assert_lists_equal(expected, actual)
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(rt, csum)
        request_handler.delete_actor(rt, src)

    def testInOutPortLocalRemoteRepeatedMigration(self):
        """Testing outport local to remote migration and revers repeatedly"""

        rt = self.rt1
        peer = self.rt2

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(rt, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', rt.id, csum, 'integer')
        request_handler.connect(rt, csum, 'integer', rt.id, src, 'integer')
        wait_for_tokens(rt, snk)

        actual_x = actual_tokens(rt, snk)
        for i in range(5):
            if i % 2 == 0:
                self.migrate(rt, peer, csum)
            else:
                self.migrate(peer, rt, csum)
            actual_x = actual_tokens(rt, snk, len(actual_x)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        
        self.assert_lists_equal(expected, actual)
        
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, csum)
        request_handler.delete_actor(rt, src)

    def testInOutPortLocalToRemoteMigration(self):
        """Testing out- and inport local to remote migration"""

        rt = self.rt1
        peer = self.rt2

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(rt, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', rt.id, csum, 'integer')
        request_handler.connect(rt, csum, 'integer', rt.id, src, 'integer')
        wait_for_tokens(rt, snk)

        actual_1 = wait_for_tokens(rt, snk)
        self.migrate(rt, peer, csum)
        wait_for_tokens(rt, snk, len(actual_1)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        self.assert_lists_equal(expected, actual)
        
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, csum)
        request_handler.delete_actor(rt, src)


    def testInOutPortRemoteToRemoteMigration(self):
        """Testing out- and inport remote to remote migration"""

        rt = self.rt1
        peer0 = self.rt2
        peer1 = self.rt3

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        csum = request_handler.new_actor(peer0, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer0.id, csum, 'integer')
        request_handler.connect(peer0, csum, 'integer', rt.id, src, 'integer')
        wait_for_tokens(rt, snk)

        actual_1 = actual_tokens(rt, snk)
        self.migrate(peer0, peer1, csum)
        wait_for_tokens(rt, snk, len(actual_1)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        
        self.assert_lists_equal(expected, actual)
        
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer1, csum)
        request_handler.delete_actor(rt, src)

    def testExplicitStateMigration(self):
        """Testing migration of explicit state handling"""

        rt = self.rt1
        peer0 = self.rt2

        snk = request_handler.new_actor_wargs(peer0, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        wrapper = request_handler.new_actor(rt, 'misc.ExplicitStateExample', 'wrapper')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(peer0, snk, 'token', rt.id, wrapper, 'token')
        request_handler.connect(rt, wrapper, 'token', rt.id, src, 'integer')

        actual_1 = wait_for_tokens(peer0, snk)

        self.migrate(rt, peer0, wrapper)
        wait_for_tokens(peer0, snk, len(actual_1)+5)

        expected = [u'((( 1 )))', u'((( 2 )))', u'((( 3 )))', u'((( 4 )))', u'((( 5 )))', u'((( 6 )))', u'((( 7 )))', u'((( 8 )))']
        actual = actual_tokens(peer0, snk, len(expected))
        self.assert_lists_equal(expected, actual)
        request_handler.delete_actor(peer0, snk)
        request_handler.delete_actor(peer0, wrapper)
        request_handler.delete_actor(rt, src)


@pytest.mark.essential
@pytest.mark.slow
class TestCalvinScript(CalvinTestBase):

    def testCompileSimple(self):
        script = """
      src : std.CountTimer()
      snk : io.StandardOut(store_tokens=1, quiet=1)
      src.integer > snk.token
    """

        rt = self.rt1
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt, app_info)
        deploy_app(d)

        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        wait_for_tokens(rt, snk)
        expected = expected_tokens(rt, src, 'seq')
        actual = actual_tokens(rt, snk, len(expected))
        request_handler.disconnect(rt, src)

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)

    def testDestroyAppWithLocalActors(self):
        script = """
      src : std.CountTimer()
      snk : io.StandardOut(store_tokens=1, quiet=1)
      src.integer > snk.token
    """

        rt = self.rt1
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt, app_info)

        deploy_app(d)
        app_id = d.app_id

        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        applications = request_handler.get_applications(rt)
        assert app_id in applications

        helpers.destroy_app(d)

        applications = request_handler.get_applications(rt)
        assert app_id not in applications

        actors = request_handler.get_actors(rt)
        assert src not in actors
        assert snk not in actors

    def testDestroyAppWithMigratedActors(self):
        rt, rt1, rt2 = get_runtime(3)

        script = """
      src : std.CountTimer()
      snk : io.StandardOut(store_tokens=1, quiet=1)
      src.integer > snk.token"""
      
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt, app_info)
        deploy_app(d)
        app_id = d.app_id

        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        self.migrate(rt, rt1, snk)
        self.migrate(rt, rt2, src)
                
        applications = request_handler.get_applications(rt)
        assert app_id in applications

        helpers.destroy_app(d)
        
        applications = request_handler.get_applications(rt)
        assert app_id not in applications

        for retry in range(1, 5):
            actors = []
            actors.extend(request_handler.get_actors(rt))
            actors.extend(request_handler.get_actors(rt1))
            actors.extend(request_handler.get_actors(rt2))
            intersection = [a for a in actors if a in d.actor_map.values()]
            if len(intersection) > 0:
                print("Not all actors removed, checking in %s" % (retry, ))
                time.sleep(retry)
            else:
                break

        for actor in d.actor_map.values():
            assert actor not in actors

@pytest.mark.essential
class TestConnections(CalvinTestBase):

    @pytest.mark.slow
    def testLocalSourceSink(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        actual = wait_for_tokens(self.rt1, snk)
        expected = expected_tokens(self.rt1, src, 'seq')
        
        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt1, snk)

    def testMigrateSink(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        pre_migrate = wait_for_tokens(self.rt1, snk)

        self.migrate(self.rt1, self.rt2, snk)
        
        actual = wait_for_tokens(self.rt2, snk, len(pre_migrate)+5)
        expected = expected_tokens(self.rt1, src)
        
        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt2, snk)

    def testMigrateSource(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        actual = wait_for_tokens(self.rt1, snk)

        self.migrate(self.rt1, self.rt2, src)

        actual = actual_tokens(self.rt1, snk, len(actual)+5 )
        expected = expected_tokens(self.rt2, src)

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(self.rt2, src)
        request_handler.delete_actor(self.rt1, snk)

    def testTwoStepMigrateSinkSource(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        pre_migrate = wait_for_tokens(self.rt1, snk)
        self.migrate(self.rt1, self.rt2, snk)
        mid_migrate = wait_for_tokens(self.rt2, snk, len(pre_migrate)+5)
        self.migrate(self.rt1, self.rt2, src)
        post_migrate = wait_for_tokens(self.rt2, snk, len(mid_migrate)+5)
        
        expected = expected_tokens(self.rt2, src)
        
        self.assert_lists_equal(expected, post_migrate, min_length=10)

        request_handler.delete_actor(self.rt2, src)
        request_handler.delete_actor(self.rt2, snk)

    def testTwoStepMigrateSourceSink(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        pre_migrate = wait_for_tokens(self.rt1, snk)
        self.migrate(self.rt1, self.rt2, src)
        mid_migrate = wait_for_tokens(self.rt1, snk, len(pre_migrate)+5)
        self.migrate(self.rt1, self.rt2, snk)
        post_migrate = wait_for_tokens(self.rt2, snk, len(mid_migrate)+5)

        expected = expected_tokens(self.rt2, src)
        self.assert_lists_equal(expected, post_migrate, min_length=15)

        request_handler.delete_actor(self.rt2, src)
        request_handler.delete_actor(self.rt2, snk)


@pytest.mark.essential
class TestScripts(CalvinTestBase):

    @pytest.mark.slow
    def testInlineScript(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > snk.token
          """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['simple:snk']
        src = d.actor_map['simple:src']

        actual = wait_for_tokens(self.rt1, snk)
        expected = expected_tokens(self.rt1, src)

        self.assert_lists_equal(expected, actual)

        helpers.destroy_app(d)

    @pytest.mark.slow
    def testFileScript(self):
        _log.analyze("TESTRUN", "+", {})
        scriptname = 'test1'
        scriptfile = absolute_filename("scripts/%s.calvin" % (scriptname, ))
        app_info, issuetracker = compile_tool.compile_file(scriptfile)
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        src = d.actor_map['%s:src' % scriptname]
        snk = d.actor_map['%s:snk' % scriptname]

        actual = wait_for_tokens(self.rt1, snk)        
        expected = expected_tokens(self.rt1, src)

        self.assert_lists_equal(expected, actual)

        helpers.destroy_app(d)


@pytest.mark.essential
class TestMetering(CalvinTestBase):

    @pytest.mark.slow
    def testMetering(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > snk.token
          """

        r = request_handler.register_metering(self.rt1)
        user_id = r['user_id']
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)
        
        snk = d.actor_map["simple:snk"]
        src = d.actor_map["simple:src"]
        tokens = len(wait_for_tokens(self.rt1, snk, 10))
        
        metainfo = request_handler.get_actorinfo_metering(self.rt1, user_id)
        data1 = request_handler.get_timed_metering(self.rt1, user_id)

        actual = wait_for_tokens(self.rt1, snk, tokens+10)
        data2 = request_handler.get_timed_metering(self.rt1, user_id)

        assert snk in metainfo
        assert data1[snk][0][1] in metainfo[snk]

        expected = expected_tokens(self.rt1, src)
        self.assert_lists_equal(expected, actual)
        
        # Verify only new data
        assert max([data[0] for data in data1[snk]]) < min([data[0] for data in data2[snk]])
        # Verify about same number of tokens (time diff makes exact match not possible)
        diff = len(data1[snk]) + len(data2[snk]) - len(actual)
        assert diff > -3 and diff < 3
        
        request_handler.unregister_metering(self.rt1, user_id)
        helpers.destroy_app(d)


    @pytest.mark.slow
    def testMigratingMetering(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > snk.token
          """

        r1 = request_handler.register_metering(self.rt1)
        user_id = r1['user_id']
        # Register as same user to keep it simple
        r2 = request_handler.register_metering(self.rt2, user_id)
        # deploy app
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['simple:snk']
        src = d.actor_map['simple:src']
        tokens = len(wait_for_tokens(self.rt1, snk))
        
        # migrate sink back and forth
        self.migrate(self.rt1, self.rt2, snk)
        tokens = len(wait_for_tokens(self.rt2, snk, tokens+5))
        self.migrate(self.rt2, self.rt1, snk)
        tokens = len(wait_for_tokens(self.rt1, snk, tokens+5))

        # Get metering
        metainfo1 = request_handler.get_actorinfo_metering(self.rt1, user_id)
        metainfo2 = request_handler.get_actorinfo_metering(self.rt2, user_id)
        data1 = request_handler.get_timed_metering(self.rt1, user_id)
        data2 = request_handler.get_timed_metering(self.rt2, user_id)

        # Check metainfo
        assert snk in metainfo1
        assert snk in metainfo2
        assert data1[snk][0][1] in metainfo1[snk]
        assert data2[snk][0][1] in metainfo2[snk]

        # Check that the sink produced something
        expected = expected_tokens(self.rt1, src)
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual)
        # Verify action times of data2 is in middle of data1

        limits = (min([data[0] for data in data2[snk]]), max([data[0] for data in data2[snk]]))
        v = [data[0] for data in data1[snk]]
        assert len(filter(lambda x: x > limits[0] and x < limits[1], v)) == 0
        assert len(filter(lambda x: x < limits[0], v)) > 0
        assert len(filter(lambda x: x > limits[1], v)) > 0
        # Verify about same number of tokens (time diff makes exact match not possible)
        diff = len(data1[snk]) + len(data2[snk]) - len(actual)
        assert diff > -3 and diff < 3
        request_handler.unregister_metering(self.rt1, user_id)
        request_handler.unregister_metering(self.rt2, user_id)
        helpers.destroy_app(d)


    @pytest.mark.slow
    def testAggregatedMigratingMetering(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > snk.token
          """

        r1 = request_handler.register_metering(self.rt1)
        user_id = r1['user_id']
        # Register as same user to keep it simple
        r2 = request_handler.register_metering(self.rt2, user_id)
        # deploy app
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)
        
        snk = d.actor_map['simple:snk']
        src = d.actor_map['simple:src']
        # migrate sink back and forth
        tokens = len(wait_for_tokens(self.rt1, snk))

        self.migrate(self.rt1, self.rt2, snk)
        tokens = len(wait_for_tokens(self.rt2, snk, tokens+5))
        self.migrate(self.rt2, self.rt1, snk)
        tokens = len(wait_for_tokens(self.rt1, snk, tokens+5))
        
        # Get metering
        metainfo1 = request_handler.get_actorinfo_metering(self.rt1, user_id)
        data1 = request_handler.get_timed_metering(self.rt1, user_id)
        agg2 = request_handler.get_aggregated_metering(self.rt2, user_id)
        data2 = request_handler.get_timed_metering(self.rt2, user_id)
        agg1 = request_handler.get_aggregated_metering(self.rt1, user_id)
        metainfo2 = request_handler.get_actorinfo_metering(self.rt2, user_id)
        
        # Check metainfo
        assert snk in metainfo1
        assert snk in metainfo2
        assert data1[snk][0][1] in metainfo1[snk]
        assert data2[snk][0][1] in metainfo2[snk]
        
        # Check that the sink produced something
        expected = expected_tokens(self.rt1, src)
        actual = actual_tokens(self.rt1, snk, len(expected))
        self.assert_lists_equal(expected, actual)
        
        # Verify about same number of tokens (time diff makes exact match not possible)
        total_timed = len(data1[snk]) + len(data2[snk])
        diff = total_timed - len(actual)
        assert diff > -3 and diff < 3
        total_agg = sum(agg1['activity'][snk].values()) + sum(agg2['activity'][snk].values())
        diff = total_agg - len(actual)
        assert diff > -3 and diff < 3
        assert sum(agg1['activity'][snk].values()) >= len(data1[snk])
        assert sum(agg2['activity'][snk].values()) <= len(data2[snk])
        request_handler.unregister_metering(self.rt1, user_id)
        request_handler.unregister_metering(self.rt2, user_id)
        helpers.destroy_app(d)


    @pytest.mark.slow
    def testLateAggregatedMigratingMetering(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > snk.token
          """

        # deploy app
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)
        
        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']
        
        # migrate sink back and forth
        tokens = len(wait_for_tokens(self.rt1, snk))
        self.migrate(self.rt1, self.rt2, snk)
        tokens = len(wait_for_tokens(self.rt2, snk, tokens+5))
        self.migrate(self.rt2, self.rt1, snk)
        tokens = len(wait_for_tokens(self.rt1, snk, tokens+5))

        # Metering
        r1 = request_handler.register_metering(self.rt1)
        user_id = r1['user_id']

        # Register as same user to keep it simple
        r2 = request_handler.register_metering(self.rt2, user_id)
        metainfo1 = request_handler.get_actorinfo_metering(self.rt1, user_id)
        agg2 = request_handler.get_aggregated_metering(self.rt2, user_id)
        agg1 = request_handler.get_aggregated_metering(self.rt1, user_id)
        metainfo2 = request_handler.get_actorinfo_metering(self.rt2, user_id)

        # Check metainfo
        assert snk in metainfo1
        assert snk in metainfo2

        # Check that the sink produced something
        expected = expected_tokens(self.rt1, src)
        actual = actual_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual)
        
        total_agg = sum(agg1['activity'][snk].values()) + sum(agg2['activity'][snk].values())
        diff = total_agg - len(actual)
        assert diff > -3 and diff < 3
        request_handler.unregister_metering(self.rt1, user_id)
        request_handler.unregister_metering(self.rt2, user_id)
        
        helpers.destroy_app(d)


class TestStateMigration(CalvinTestBase):

    def testSimpleState(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          sum : std.Sum()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > sum.integer
          sum.integer > snk.token
          """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)
        
        src = d.actor_map['simple:src']
        csum = d.actor_map['simple:sum']
        snk = d.actor_map['simple:snk']

        tokens = len(wait_for_tokens(self.rt1, snk))
        self.migrate(self.rt1, self.rt2, csum)
    
        actual = request_handler.report(self.rt1, snk, tokens+5)
        expected = expected_tokens(self.rt1, src, 'sum')

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)


@pytest.mark.slow
@pytest.mark.essential
class TestAppLifeCycle(CalvinTestBase):

    def testAppDestructionOneRemote(self):
        from functools import partial
        
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          sum : std.Sum()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > sum.integer
          sum.integer > snk.token
          """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        src = d.actor_map['simple:src']
        csum = d.actor_map['simple:sum']
        snk = d.actor_map['simple:snk']

        tokens = len(wait_for_tokens(self.rt1, snk))
        self.migrate(self.rt1, self.rt2, csum)
        
        actual = actual_tokens(self.rt1, snk, tokens+5)
        expected = expected_tokens(self.rt1, src, 'sum')

        self.assert_lists_equal(expected, actual)
        
        helpers.delete_app(request_handler, self.rt1, d.app_id)
        
        def check_actors_gone(runtime):
            for actor in src, csum, snk:
                a = request_handler.get_actor(runtime, actor)
                if a is not None:
                    _log.info("Actor '%r' still present on runtime '%r" % (actor, runtime.id, ))
                    return False
            return True

        for rt in [ self.rt1, self.rt2, self.rt3 ]:
            check_rt = partial(check_actors_gone, rt)
            all_gone = helpers.retry(20, check_rt, lambda x: x, "Not all actors gone on rt '%r'" % (rt.id, ))
            assert all_gone

        def check_application_gone(runtime):
            try :
                app = request_handler.get_application(runtime, d.app_id)
            except Exception as e:
                msg = str(e.message)
                if msg.startswith(404):
                    return True
            return app is None
            
        for rt in [ self.rt1, self.rt2, self.rt3 ]:
            check_rt = partial(check_application_gone, rt)
            all_gone = helpers.retry(20, check_rt, lambda x: x, "Application still present on rt '%r'" % (rt.id, ))
            assert all_gone
            
        self.assertTrue(request_handler.get_application(self.rt1, d.app_id) is None)
        self.assertTrue(request_handler.get_application(self.rt2, d.app_id) is None)
        self.assertTrue(request_handler.get_application(self.rt3, d.app_id) is None)

    def testAppDestructionAllRemote(self):
        from functools import partial
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          sum : std.Sum()
          snk : io.StandardOut(store_tokens=1, quiet=1)
          src.integer > sum.integer
          sum.integer > snk.token
          """
        #? import sys
        #? from twisted.python import log
        #? log.startLogging(sys.stdout)

        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        src = d.actor_map['simple:src']
        csum = d.actor_map['simple:sum']
        snk = d.actor_map['simple:snk']

        tokens = len(wait_for_tokens(self.rt1, snk))
        
        self.migrate(self.rt1, self.rt2, src)
        self.migrate(self.rt1, self.rt2, csum)
        self.migrate(self.rt1, self.rt2, snk)
        
        actual = actual_tokens(self.rt2, snk, tokens+5)
        expected = expected_tokens(self.rt2, src, 'sum')

        self.assert_lists_equal(expected, actual)
        
        helpers.delete_app(request_handler, self.rt1, d.app_id)

        def check_actors_gone(runtime):
            for actor in src, csum, snk:
                a = request_handler.get_actor(runtime, actor)
                if a is not None:
                    _log.info("Actor '%r' still present on runtime '%r" % (actor, runtime.id, ))
                    return False
            return True

        for rt in [ self.rt1, self.rt2, self.rt3 ]:
            check_rt = partial(check_actors_gone, rt)
            all_gone = helpers.retry(20, check_rt, lambda x: x, "Not all actors gone on rt '%r'" % (rt.id, ))
            assert all_gone

        def check_application_gone(runtime):
            try :
                app = request_handler.get_application(runtime, d.app_id)
            except Exception as e:
                msg = str(e.message)
                if msg.startswith(404):
                    return True
            return app is None
            
        for rt in [ self.rt1, self.rt2, self.rt3 ]:
            check_rt = partial(check_application_gone, rt)
            all_gone = helpers.retry(20, check_rt, lambda x: x, "Application still present on rt '%r'" % (rt.id, ))
            assert all_gone

        self.assertTrue(request_handler.get_application(self.rt1, d.app_id) is None)
        self.assertTrue(request_handler.get_application(self.rt2, d.app_id) is None)
        self.assertTrue(request_handler.get_application(self.rt3, d.app_id) is None)


@pytest.mark.essential
class TestEnabledToEnabledBug(CalvinTestBase):

    def test10(self):
        _log.analyze("TESTRUN", "+", {})
        # Two actors, doesn't seem to trigger the bug
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, src, 'integer')

        actual = actual_tokens(self.rt1, snk, 10)

        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt1, snk)

    def test11(self):
        _log.analyze("TESTRUN", "+", {})
        # Same as test10, but scripted
        script = """
            src : std.Counter()
            snk : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['simple:snk']

        actual = actual_tokens(self.rt1, snk, 10)
        self.assert_lists_equal(range(1, 10), actual)

        helpers.destroy_app(d)

    def test20(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        ity = request_handler.new_actor(self.rt1, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, ity, 'token')
        request_handler.connect(self.rt1, ity, 'token', self.rt1.id, src, 'integer')

        actual = actual_tokens(self.rt1, snk, 10)

        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt1, ity)
        request_handler.delete_actor(self.rt1, snk)

    def test21(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        ity = request_handler.new_actor(self.rt2, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(self.rt3, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt3, snk, 'token', self.rt2.id, ity, 'token')
        request_handler.connect(self.rt2, ity, 'token', self.rt1.id, src, 'integer')

        actual = actual_tokens(self.rt3, snk, 10)
        self.assert_lists_equal(range(1,10), actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt2, ity)
        request_handler.delete_actor(self.rt3, snk)

    def test22(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        ity = request_handler.new_actor(self.rt2, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(self.rt3, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt2, ity, 'token', self.rt1.id, src, 'integer')
        request_handler.connect(self.rt3, snk, 'token', self.rt2.id, ity, 'token')

        actual = actual_tokens(self.rt3, snk, 10)
        self.assert_lists_equal(range(1,10), actual)

        actual = actual_tokens(self.rt3, snk, len(actual)+1)
        self.assert_lists_equal(range(1,len(actual)), actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt2, ity)
        request_handler.delete_actor(self.rt3, snk)

    def test25(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        ity = request_handler.new_actor(self.rt1, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt1, ity, 'token', self.rt1.id, src, 'integer')
        request_handler.connect(self.rt1, snk, 'token', self.rt1.id, ity, 'token')

        actual = actual_tokens(self.rt1, snk, 10)

        self.assert_lists_equal(range(1, 10), actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt1, ity)
        request_handler.delete_actor(self.rt1, snk)

    def test26(self):
        _log.analyze("TESTRUN", "+", {})
        # Same as test20
        script = """
            src : std.Counter()
            ity : std.Identity()
            snk : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > ity.token
            ity.token > snk.token
          """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)
        snk = d.actor_map['simple:snk']
        
        actual = actual_tokens(self.rt1, snk, 10)        
        self.assert_lists_equal(range(1,10), actual)

        helpers.destroy_app(d)


    def test30(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        snk1 = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk2', store_tokens=1, quiet=1)

        request_handler.set_port_property(self.rt1, src, 'out', 'integer',
                                            port_properties={'routing': 'fanout', 'nbr_peers': 2})

        request_handler.connect(self.rt1, snk1, 'token', self.rt1.id, src, 'integer')
        request_handler.connect(self.rt1, snk2, 'token', self.rt1.id, src, 'integer')

        actual1 = actual_tokens(self.rt1, snk1, 10)
        actual2 = actual_tokens(self.rt1, snk2, 10)

        self.assert_lists_equal(list(range(1, 10)), actual1)
        self.assert_lists_equal(list(range(1, 10)), actual2)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt1, snk1)
        request_handler.delete_actor(self.rt1, snk2)

    def test31(self):
        # Verify that fanout defined implicitly in scripts is handled correctly
        _log.analyze("TESTRUN", "+", {})
        script = """
            src : std.Counter()
            snk1 : io.StandardOut(store_tokens=1, quiet=1)
            snk2 : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > snk1.token
            src.integer > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "test31")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)
        
        snk1 = d.actor_map['test31:snk1']
        snk2 = d.actor_map['test31:snk2']
        actual1 = actual_tokens(self.rt1, snk1, 10)
        actual2 = actual_tokens(self.rt1, snk2, 10)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual1)
        self.assert_lists_equal(expected, actual2)

        d.destroy()

    def test32(self):
        # Verify that fanout from component inports is handled correctly
        _log.analyze("TESTRUN", "+", {})
        script = """
            component Foo() in -> a, b{
              a : std.Identity()
              b : std.Identity()
              .in >  a.token
              .in > b.token
              a.token > .a
              b.token > .b
            }

            snk2 : io.StandardOut(store_tokens=1, quiet=1)
            snk1 : io.StandardOut(store_tokens=1, quiet=1)
            foo : Foo()
            req : std.Counter()
            req.integer > foo.in
            foo.a > snk1.token
            foo.b > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "test32")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk1 = d.actor_map['test32:snk1']
        snk2 = d.actor_map['test32:snk2']
        actual1 = actual_tokens(self.rt1, snk1, 10)
        actual2 = actual_tokens(self.rt1, snk2, 10)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual1)
        self.assert_lists_equal(expected, actual2)

        d.destroy()

    def test40(self):
        # Verify round robin port
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        snk1 = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(self.rt1, 'io.StandardOut', 'snk2', store_tokens=1, quiet=1)

        request_handler.set_port_property(self.rt1, src, 'out', 'integer',
                                            port_properties={'routing': 'round-robin', 'nbr_peers': 2})

        request_handler.connect(self.rt1, snk1, 'token', self.rt1.id, src, 'integer')
        request_handler.connect(self.rt1, snk2, 'token', self.rt1.id, src, 'integer')

        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        actual1 = actual_tokens(self.rt1, snk1, 10)
        actual2 = actual_tokens(self.rt1, snk2, 10)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt1, snk1)
        request_handler.delete_actor(self.rt1, snk2)



@pytest.mark.essential
class TestNullPorts(CalvinTestBase):

    def testVoidActor(self):
        # Verify that the null port of a std.Void actor behaves as expected
        _log.analyze("TESTRUN", "+", {})
        script = """
            src1 : std.Counter()
            src2 : std.Void()
            join : std.Join()
            snk  : io.StandardOut(store_tokens=1, quiet=1)

            src1.integer > join.token_1
            src2.void > join.token_2
            join.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testVoidActor")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testVoidActor:snk']        
        actual = wait_for_tokens(self.rt1, snk, 10)
        expected = list(range(1, 10))
        self.assert_lists_equal(expected, actual)

        helpers.destroy_app(d)

    def testTerminatorActor(self):
        # Verify that the null port of a std.Terminator actor behaves as expected
        _log.analyze("TESTRUN", "+", {})
        script = """
            src  : std.Counter()
            term : std.Terminator()
            snk  : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > term.void
            src.integer > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testTerminatorActor")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)
        
        snk = d.actor_map['testTerminatorActor:snk']
        actual = wait_for_tokens(self.rt1, snk)        
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)


@pytest.mark.essential
class TestCompare(CalvinTestBase):

    def testBadOp(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=5, n=-1)
            pred  : std.Compare(op="<>")
            snk   : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testBadOp")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testBadOp:snk']
        actual = wait_for_tokens(self.rt1, snk, 10)
        expected = [0] * 10

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)

    def testEqual(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=5, n=-1)
            pred  : std.Compare(op="=")
            snk   : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testEqual")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testEqual:snk']

        expected = [x == 5 for x in range(1, 10)]
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)


    def testGreaterThanOrEqual(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=5, n=-1)
            pred  : std.Compare(op=">=")
            snk   : io.StandardOut(store_tokens=1, quiet=1)

            src.integer > pred.a
            const.token > pred.b
            pred.result > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testGreaterThanOrEqual")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testGreaterThanOrEqual:snk']
        expected = [x >= 5 for x in range(1, 10)]
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)



@pytest.mark.essential
class TestSelect(CalvinTestBase):

    def testTrue(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=true, n=-1)
            route : std.Select()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.integer > route.data
            const.token > route.select
            route.case_true  > snk.token
            route.case_false > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testTrue")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testTrue:snk']
        actual = wait_for_tokens(self.rt1, snk, 10)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)

    def testFalse(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=0, n=-1)
            route : std.Select()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.integer > route.data
            const.token > route.select
            route.case_true  > term.void
            route.case_false > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testFalse")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testFalse:snk']
      
        actual = wait_for_tokens(self.rt1, snk, 10)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)


    def testBadSelect(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Counter()
            const : std.Constant(data=2, n=-1)
            route : std.Select()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.integer > route.data
            const.token > route.select
            route.case_true  > term.void
            route.case_false > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testBadSelect")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testBadSelect:snk']
        actual = wait_for_tokens(self.rt1, snk, 10)
        expected = list(range(1, 10))

        self.assert_lists_equal(expected, actual)
        
        helpers.destroy_app(d)


@pytest.mark.essential
class TestDeselect(CalvinTestBase):

    def testDeselectTrue(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0, n=-1)
            const_1 : std.Constant(data=1, n=-1)
            comp    : std.Compare(op="<=")
            ds      : std.Deselect()
            snk     : io.StandardOut(store_tokens=1, quiet=1)

            const_0.token > ds.case_false
            const_1.token > ds.case_true
            src.integer > comp.a
            src.integer > const_5.in
            const_5.out > comp.b
            comp.result > ds.select
            ds.data > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testDeselectTrue")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testDeselectTrue:snk']

        expected = [1] * 5 + [0] * 5
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)
        helpers.destroy_app(d)

    def testDeselectFalse(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0, n=-1)
            const_1 : std.Constant(data=1, n=-1)
            comp    : std.Compare(op="<=")
            ds      : std.Deselect()
            snk     : io.StandardOut(store_tokens=1, quiet=1)

            const_0.token > ds.case_true
            const_1.token > ds.case_false
            src.integer > comp.a
            src.integer > const_5.in
            const_5.out > comp.b
            comp.result > ds.select
            ds.data > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testDeselectFalse")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testDeselectFalse:snk']

        expected = [0] * 5 + [1] * 5
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)
        
        helpers.destroy_app(d)


    def testDeselectBadSelect(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src     : std.Counter()
            const_5 : std.Constantify(constant=5)
            const_0 : std.Constant(data=0, n=11)
            ds      : std.Deselect()
            snk     : io.StandardOut(store_tokens=1, quiet=1)

            const_0.token > ds.case_false
            src.integer > ds.case_true
            const_0.token > const_5.in
            const_5.out > ds.select
            ds.data > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testDeselectBadSelect")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testDeselectBadSelect:snk']

        expected = [0] * 10
        actual = wait_for_tokens(self.rt1, snk, len(expected))
        
        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)


@pytest.mark.essential
class TestLineJoin(CalvinTestBase):

    def testBasicJoin(self):
        _log.analyze("TESTRUN", "+", {})
        datafile = absolute_filename('data.txt')
        script = """
            fname : std.Constant(data="%s")
            src   : io.FileReader()
            join  : text.LineJoin()
            snk   : io.StandardOut(store_tokens=1, quiet=1)

            fname.token > src.filename
            src.out   > join.line
            join.text > snk.token
        """ % (datafile, )
        
        app_info, errors, warnings = self.compile_script(script, "testBasicJoin")
        print errors
       
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        with open(datafile, "r") as fp:
            expected = ["\n".join([l.rstrip() for l in fp.readlines()])]

        snk = d.actor_map['testBasicJoin:snk']

        actual = wait_for_tokens(self.rt1, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


@pytest.mark.essential
class TestRegex(CalvinTestBase):

    def testRegexMatch(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="24.1632", n=1)
            regex : text.RegexMatch(regex=!"\d+\.\d+")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexMatch")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testRegexMatch:snk']

        expected = ["24.1632"]
        actual = wait_for_tokens(self.rt1, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)



    def testRegexNoMatch(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="x24.1632", n=1)
            regex : text.RegexMatch(regex=!"\d+\.\d+")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.no_match > snk.token
            regex.match    > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexNoMatch")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testRegexNoMatch:snk']
        expected = ["x24.1632"]
        actual = wait_for_tokens(self.rt1, snk, 1)
        
        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


    def testRegexCapture(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="24.1632", n=1)
            regex : text.RegexMatch(regex=!"(\d+)\.\d+")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexCapture")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testRegexCapture:snk']

        expected = ["24"]
        actual = wait_for_tokens(self.rt1, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


    def testRegexMultiCapture(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="24.1632", n=1)
            regex : text.RegexMatch(regex=!"(\d+)\.(\d+)")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.match    > snk.token
            regex.no_match > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexMultiCapture")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testRegexMultiCapture:snk']

        expected = ["24"]
        actual = wait_for_tokens(self.rt1, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


    def testRegexCaptureNoMatch(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src   : std.Constant(data="x24.1632", n=1)
            regex : text.RegexMatch(regex=!"(\d+)\.\d+")
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            term  : std.Terminator()

            src.token      > regex.text
            regex.no_match > snk.token
            regex.match    > term.void
        """
        app_info, errors, warnings = self.compile_script(script, "testRegexCaptureNoMatch")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testRegexCaptureNoMatch:snk']
        expected = ["x24.1632"]
        actual = wait_for_tokens(self.rt1, snk, 1)

        self.assert_lists_equal(expected, actual, min_length=1)

        helpers.destroy_app(d)


@pytest.mark.essential
class TestConstantAsArguments(CalvinTestBase):

    def testConstant(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = 42
            src   : std.Constant(data=FOO, n=10)
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstant")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testConstant:snk']

        expected = [42]*10
        actual = wait_for_tokens(self.rt1, snk, len(expected))
        
        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testConstantRecursive(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = BAR
            define BAR = 42
            src   : std.Constant(data=FOO, n=10)
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.token > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantRecursive")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testConstantRecursive:snk']

        expected = [42]*10
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)


@pytest.mark.essential
class TestConstantOnPort(CalvinTestBase):

    def testLiteralOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            42 > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)
        time.sleep(.1)

        snk = d.actor_map['testLiteralOnPort:snk']

        expected = [42]*10
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testConstantOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = "Hello"
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            FOO > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantOnPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testConstantOnPort:snk']

        expected = ["Hello"]*10
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testConstantRecursiveOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = BAR
            define BAR = "yay"
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            FOO > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantRecursiveOnPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testConstantRecursiveOnPort:snk']

        expected = ["yay"]*10
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)


@pytest.mark.essential
class TestConstantAndComponents(CalvinTestBase):

    def testLiteralOnCompPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component Foo() -> out {
                i:std.Stringify()
                42 > i.in
                i.out > .out
            }
            src   : Foo()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.out > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnCompPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testLiteralOnCompPort:snk']

        expected = ["42"]*10
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testConstantOnCompPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define MEANING = 42
            component Foo() -> out {
                i:std.Stringify()
                MEANING > i.in
                i.out > .out
            }
            src   : Foo()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.out > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantOnCompPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testConstantOnCompPort:snk']

        expected = ["42"]*10
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testStringConstantOnCompPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define MEANING = "42"
            component Foo() -> out {
                i:std.Identity()
                MEANING > i.token
                i.token > .out
            }
            src   : Foo()
            snk   : io.StandardOut(store_tokens=1, quiet=1)
            src.out > snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testStringConstantOnCompPort")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testStringConstantOnCompPort:snk']

        expected = ["42"]*10
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)


@pytest.mark.essential
class TestConstantAndComponentsArguments(CalvinTestBase):

    def testComponentArgument(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Count(len) -> seq {
            src : std.Constant(data="hup", n=len)
            src.token > .seq
        }
        src : Count(len=5)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentArgument")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testComponentArgument:snk']

        expected = ["hup"]*5
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=5)

        helpers.destroy_app(d)

    def testComponentConstantArgument(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        define FOO = 5
        component Count(len) -> seq {
            src : std.Constant(data="hup", n=len)
            src.token > .seq
        }
        src : Count(len=FOO)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentConstantArgument")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testComponentConstantArgument:snk']

        expected = ["hup"]*5
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=5)
        
        helpers.destroy_app(d)


    def testComponentConstantArgumentDirect(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        define FOO = 10
        component Count() -> seq {
         src : std.Constant(data="hup", n=FOO)
         src.token > .seq
        }
        src : Count()
        snk : io.StandardOut(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentConstantArgumentDirect")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testComponentConstantArgumentDirect:snk']

        expected = ["hup"]*10
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testComponentArgumentAsImplicitActor(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Count(data) -> seq {
            i : std.Identity()
            data > i.token
            i.token > .seq
        }
        src : Count(data="hup")
        snk : io.StandardOut(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentArgumentAsImplicitActor")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testComponentArgumentAsImplicitActor:snk']

        expected = ["hup"]*10
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)

        helpers.destroy_app(d)

    def testComponentConstantArgumentAsImplicitActor(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        define FOO = "hup"
        component Count(data) -> seq {
            i : std.Identity()
            data > i.token
            i.token > .seq
        }
        src : Count(data=FOO)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        src.seq > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testComponentConstantArgumentAsImplicitActor")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk = d.actor_map['testComponentConstantArgumentAsImplicitActor:snk']

        expected = ["hup"]*10
        actual = wait_for_tokens(self.rt1, snk, len(expected))

        self.assert_lists_equal(expected, actual, min_length=10)
        d.destroy()

@pytest.mark.essential
class TestConstantifyOnPort(CalvinTestBase):

    def testLiteralOnPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src : std.Counter()
            snk : io.StandardOut(store_tokens=1, quiet=1)
            src.integer > /"X"/ snk.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnPort")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)
        
        snk = d.actor_map['testLiteralOnPort:snk']

        actual = wait_for_tokens(self.rt1, snk, 10)
        expected = ['X']*len(actual)

        self.assert_lists_equal(expected, actual, min_length=10)

        d.destroy()

    def testLiteralOnPortlist(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src : std.Counter()
            snk1 : io.StandardOut(store_tokens=1, quiet=1)
            snk2 : io.StandardOut(store_tokens=1, quiet=1)
            src.integer > /"X"/ snk1.token, snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralOnPortlist")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk1 = d.actor_map['testLiteralOnPortlist:snk1']
        snk2 = d.actor_map['testLiteralOnPortlist:snk2']
        
        actual1 = wait_for_tokens(self.rt1, snk1, 10)
        actual2 = wait_for_tokens(self.rt1, snk2, 10)
        
        expected1 = ['X']*len(actual1)
        expected2 = range(1, len(actual2))

        self.assert_lists_equal(expected1, actual1, min_length=10)
        self.assert_lists_equal(expected2, actual2, min_length=10)

        d.destroy()

    def testLiteralsOnPortlist(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src : std.Counter()
            snk1 : io.StandardOut(store_tokens=1, quiet=1)
            snk2 : io.StandardOut(store_tokens=1, quiet=1)
            src.integer > /"X"/ snk1.token, /"Y"/ snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testLiteralsOnPortlist")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk1 = d.actor_map['testLiteralsOnPortlist:snk1']
        snk2 = d.actor_map['testLiteralsOnPortlist:snk2']
        actual1 = wait_for_tokens(self.rt1, snk1, 10)
        actual2 = wait_for_tokens(self.rt1, snk2, 10)
        
        expected1 = ['X']*len(actual1)
        expected2 = ['Y']*len(actual2)

        self.assert_lists_equal(expected1, actual1, min_length=10)
        self.assert_lists_equal(expected2, actual2, min_length=10)

        d.destroy()

    def testConstantsOnPortlist(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            define FOO = "X"
            define BAR = "Y"
            src : std.Counter()
            snk1 : io.StandardOut(store_tokens=1, quiet=1)
            snk2 : io.StandardOut(store_tokens=1, quiet=1)
            src.integer > /FOO/ snk1.token, /BAR/ snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testConstantsOnPortlist")
        d = deployer.Deployer(self.rt1, app_info)
        deploy_app(d)

        snk1 = d.actor_map['testConstantsOnPortlist:snk1']
        snk2 = d.actor_map['testConstantsOnPortlist:snk2']

        actual1 = wait_for_tokens(self.rt1, snk1, 10)
        actual2 = wait_for_tokens(self.rt1, snk2, 10)
        expected1 = ['X']*len(actual1)
        expected2 = ['Y']*len(actual2)

        self.assert_lists_equal(expected1, actual1, min_length=10)
        self.assert_lists_equal(expected2, actual2, min_length=10)

        d.destroy()


@pytest.mark.essential
class TestPortProperties(CalvinTestBase):

    def testRoundRobin(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.Counter()
            snk1   : io.StandardOut(store_tokens=1, quiet=1)
            snk2   : io.StandardOut(store_tokens=1, quiet=1)
            src.integer(routing="round-robin")
            src.integer > snk1.token
            src.integer > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        d.destroy()

    def testPortPropertyOutsideComponentOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
            }
            
            src    : CompCounter()
            snk1   : io.StandardOut(store_tokens=1, quiet=1)
            snk2   : io.StandardOut(store_tokens=1, quiet=1)
            src.seq(routing="round-robin")
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (app_info['port_properties']['testScript:src:compsrc'][0]
                    ['properties']['routing'] == 'round-robin')
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        d.destroy()

    def testPortPropertyOutsideComponentInPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompSink() seq -> {
                compsnk    : io.StandardOut(store_tokens=1, quiet=1)
                .seq > compsnk.token
            }

            src    : std.Counter()
            snk1   : CompSink()
            snk2   : CompSink()
            src.integer(routing="round-robin")
            snk1.seq(test1="dummy1")
            snk2.seq(test1="dummy2")
            src.integer > snk1.seq
            src.integer > snk2.seq
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src'][0]
        assert (app_info['port_properties']['testScript:src'][0]['port'] ==
                'integer')
        assert (app_info['port_properties']['testScript:src'][0]
                    ['properties']['routing'] == 'round-robin')

        assert 'port' in app_info['port_properties']['testScript:snk1:compsnk'][0]
        assert (app_info['port_properties']['testScript:snk1:compsnk'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testScript:snk1:compsnk'][0]
                    ['properties']['test1'] == 'dummy1')
        assert 'port' in app_info['port_properties']['testScript:snk2:compsnk'][0]
        assert (app_info['port_properties']['testScript:snk2:compsnk'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testScript:snk2:compsnk'][0]
                    ['properties']['test1'] == 'dummy2')

        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk1 = d.actor_map['testScript:snk1:compsnk']
        snk2 = d.actor_map['testScript:snk2:compsnk']
        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        d.destroy()

    def testPortPropertyInsideComponentOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                compsrc.integer(routing="round-robin")
            }
            
            src    : CompCounter()
            snk1   : io.StandardOut(store_tokens=1, quiet=1)
            snk2   : io.StandardOut(store_tokens=1, quiet=1)
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (app_info['port_properties']['testScript:src:compsrc'][0]
                    ['properties']['routing'] == 'round-robin')
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        d.destroy()

    def testPortPropertyInsideComponentInPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompSink() seq -> {
                compsnk    : io.StandardOut(store_tokens=1, quiet=1)
                .seq > compsnk.token
                compsnk.token(test1="dummyx")
            }

            src    : std.Counter()
            snk1   : CompSink()
            snk2   : CompSink()
            src.integer(routing="round-robin")
            src.integer > snk1.seq
            src.integer > snk2.seq
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src'][0]
        assert (app_info['port_properties']['testScript:src'][0]['port'] ==
                'integer')
        assert (app_info['port_properties']['testScript:src'][0]
                    ['properties']['routing'] == 'round-robin')

        assert 'port' in app_info['port_properties']['testScript:snk1:compsnk'][0]
        assert (app_info['port_properties']['testScript:snk1:compsnk'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testScript:snk1:compsnk'][0]
                    ['properties']['test1'] == 'dummyx')
        assert 'port' in app_info['port_properties']['testScript:snk2:compsnk'][0]
        assert (app_info['port_properties']['testScript:snk2:compsnk'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testScript:snk2:compsnk'][0]
                    ['properties']['test1'] == 'dummyx')

        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk1 = d.actor_map['testScript:snk1:compsnk']
        snk2 = d.actor_map['testScript:snk2:compsnk']
        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        d.destroy()

    def testPortPropertyInsideComponentInternalInPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                .seq(test1="dummyx")
                compsrc.integer(routing="round-robin")
            }
            
            src    : CompCounter()
            snk1   : io.StandardOut(store_tokens=1, quiet=1)
            snk2   : io.StandardOut(store_tokens=1, quiet=1)
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (app_info['port_properties']['testScript:src:compsrc'][0]
                    ['properties']['routing'] == 'round-robin')

        assert 'port' in app_info['port_properties']['testScript:snk1'][0]
        assert (app_info['port_properties']['testScript:snk1'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testScript:snk1'][0]
                    ['properties']['test1'] == 'dummyx')
        assert 'port' in app_info['port_properties']['testScript:snk2'][0]
        assert (app_info['port_properties']['testScript:snk2'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testScript:snk2'][0]
                    ['properties']['test1'] == 'dummyx')

        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        d.destroy()

    def testPortPropertyInsideComponentInternalOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompSink() seq -> {
                compsnk    : io.StandardOut(store_tokens=1, quiet=1)
                .seq > compsnk.token
                .seq(routing="round-robin")
            }

            src    : std.Counter()
            snk1   : CompSink()
            snk2   : CompSink()
            src.integer > snk1.seq
            src.integer > snk2.seq
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src'][0]
        assert (app_info['port_properties']['testScript:src'][0]['port'] ==
                'integer')
        assert (app_info['port_properties']['testScript:src'][0]
                    ['properties']['routing'] == 'round-robin')

        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk1 = d.actor_map['testScript:snk1:compsnk']
        snk2 = d.actor_map['testScript:snk2:compsnk']
        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        d.destroy()

    def testPortPropertyTupleOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                compsrc.integer(routing=["round-robin", "random"])
            }
            
            src    : CompCounter()
            snk1   : io.StandardOut(store_tokens=1, quiet=1)
            snk2   : io.StandardOut(store_tokens=1, quiet=1)
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (app_info['port_properties']['testScript:src:compsrc'][0]
                    ['properties']['routing'][0] == 'round-robin')
        assert (app_info['port_properties']['testScript:src:compsrc'][0]
                    ['properties']['routing'][1] == 'random')

        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        d.destroy()

    def testPortPropertyConsolidateOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                compsrc.integer(routing=["round-robin", "random"])
            }
            
            src    : CompCounter()
            snk1   : io.StandardOut(store_tokens=1, quiet=1)
            snk2   : io.StandardOut(store_tokens=1, quiet=1)
            src.seq(routing=["dummy", "round-robin"])
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert len(errors) == 0
        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert len(app_info['port_properties']['testScript:src:compsrc'][0]
                    ['properties']['routing']) == 1
        assert (app_info['port_properties']['testScript:src:compsrc'][0]
                    ['properties']['routing'][0] == 'round-robin')

        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']
        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        d.destroy()

    def testPortPropertyConsolidateRejectOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                compsrc.integer(routing=["round-robin", "random"])
            }
            
            src    : CompCounter()
            snk1   : io.StandardOut(store_tokens=1, quiet=1)
            snk2   : io.StandardOut(store_tokens=1, quiet=1)
            src.seq(routing="fanout")
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert len(errors) == 2
        assert all([e['reason'] == "Can't handle conflicting properties without common alternatives" for e in errors])
        assert all([e['line'] in [5, 11] for e in errors])

    def testPortPropertyConsolidateInsideComponentInternalOutPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompSink() seq -> {
                compsnk    : io.StandardOut(store_tokens=1, quiet=1)
                .seq > compsnk.token
                .seq(routing=["random", "round-robin", "fanout"])
            }

            src    : std.Counter()
            snk1   : CompSink()
            snk2   : CompSink()
            src.integer(routing=["round-robin", "random"])
            src.integer > snk1.seq
            src.integer > snk2.seq
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info
        assert 'testScript:src' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src'][0]
        assert (app_info['port_properties']['testScript:src'][0]['port'] ==
                'integer')
        assert len(app_info['port_properties']['testScript:src'][0]
                    ['properties']['routing']) == 2
        assert (app_info['port_properties']['testScript:src'][0]
                    ['properties']['routing'][0] == 'round-robin')

        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk1 = d.actor_map['testScript:snk1:compsnk']
        snk2 = d.actor_map['testScript:snk2:compsnk']
        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

@pytest.mark.essential
class TestCollectPort(CalvinTestBase):

    def testCollectPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.01, start=1, steps=5)
        src2 : std.CountTimer(sleep=0.01, start=1001, steps=5)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        snk.token(routing="collect-unordered")
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        assert 'testCollectPort:snk' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testCollectPort:snk'][0]
        assert (app_info['port_properties']['testCollectPort:snk'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testCollectPort:snk'][0]
                    ['properties']['nbr_peers'] == 2)

        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk = d.actor_map['testCollectPort:snk']
        actual = request_handler.report(self.rt1, snk)

        high = [x for x in actual if x > 999]
        low = [x for x in actual if x < 999]
        self.assert_lists_equal(range(1001,1006), high, min_length=4)
        self.assert_lists_equal(range(1,6), low, min_length=4)

        d.destroy()

    def testCollectPortComponentIn(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Dual() seqin -> seqout1, seqout2 {
            id1    : std.Identity()
            id2    : std.Identity()
            .seqin(routing="round-robin")
            .seqin > id1.token
            .seqin > id2.token
            id1.token > .seqout1
            id2.token > .seqout2
        }
        src1 : std.CountTimer(sleep=0.01, start=1, steps=5)
        src2 : std.CountTimer(sleep=0.01, start=1001, steps=5)
        duo: Dual()
        duo.seqin(routing="collect-unordered")
        snk1 : io.StandardOut(store_tokens=1, quiet=1)
        snk2 : io.StandardOut(store_tokens=1, quiet=1)
        src1.integer > duo.seqin
        src2.integer > duo.seqin
        duo.seqout1 > snk1.token
        duo.seqout2 > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        assert (app_info['port_properties']['testCollectPort:duo:id1'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testCollectPort:duo:id2'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testCollectPort:duo:id1'][0]
                    ['properties']['nbr_peers'] == 2)
        assert (app_info['port_properties']['testCollectPort:duo:id2'][0]
                    ['properties']['nbr_peers'] == 2)
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk1 = d.actor_map['testCollectPort:snk1']
        snk2 = d.actor_map['testCollectPort:snk2']
        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)
        assert len(actual1) > 3
        assert len(actual2) > 3
        high = sorted([x for x in actual1 + actual2 if x > 999])
        low = sorted([x for x in actual1 + actual2 if x < 999])
        self.assert_lists_equal(range(1001,1006), high, min_length=4)
        self.assert_lists_equal(range(1,6), low, min_length=4)

        d.destroy()

    def testCollectPortComponentOut(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Dual() seqin1, seqin2 -> seqout {
            id1    : std.Identity()
            id2    : std.Identity()
            .seqout(routing="collect-unordered")
            .seqin1 > id1.token
            .seqin2 > id2.token
            id1.token > .seqout
            id2.token > .seqout
        }
        src1 : std.CountTimer(sleep=0.01, start=1, steps=5)
        src2 : std.CountTimer(sleep=0.01, start=1001, steps=5)
        duo: Dual()
        duo.seqout(routing="round-robin")
        snk1 : io.StandardOut(store_tokens=1, quiet=1)
        snk2 : io.StandardOut(store_tokens=1, quiet=1)
        src1.integer > duo.seqin1
        src2.integer > duo.seqin2
        duo.seqout > snk1.token
        duo.seqout > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        assert (app_info['port_properties']['testCollectPort:snk1'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testCollectPort:snk2'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testCollectPort:snk1'][0]
                    ['properties']['nbr_peers'] == 2)
        assert (app_info['port_properties']['testCollectPort:snk2'][0]
                    ['properties']['nbr_peers'] == 2)
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(0.5)

        snk1 = d.actor_map['testCollectPort:snk1']
        snk2 = d.actor_map['testCollectPort:snk2']
        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)
        assert len(actual1) > 3
        assert len(actual2) > 3
        high = sorted([x for x in actual1 + actual2 if x > 999])
        low = sorted([x for x in actual1 + actual2 if x < 999])
        self.assert_lists_equal(range(1001,1006), high, min_length=4)
        self.assert_lists_equal(range(1,6), low, min_length=4)

        d.destroy()

    def testCollectPortRemote(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.01, start=1, steps=5)
        src2 : std.CountTimer(sleep=0.01, start=1001, steps=5)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        snk.token(routing="collect-unordered", nbr_peers=2)
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        assert (app_info['port_properties']['testCollectPort:snk'][0]['port'] ==
                'token')
        assert (app_info['port_properties']['testCollectPort:snk'][0]
                    ['properties']['nbr_peers'] == 2)
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        request_handler.migrate(self.rt1, snk, self.rt2.id)
        time.sleep(1)
        actual = request_handler.report(self.rt2, snk)

        high = [x for x in actual if x > 999]
        low = [x for x in actual if x < 999]
        self.assert_lists_equal(range(1001,1006), high, min_length=4)
        self.assert_lists_equal(range(1,6), low, min_length=4)
        d.destroy()

    def testPortPropertyConsolidateInsideComponentInternalInPort(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            component CompCounter() -> seq {
                compsrc    : std.Counter()
                compsrc.integer > .seq
                .seq(test1=["dummyx", "dummyy", "dummyz"], test2="dummyi")
                compsrc.integer(routing="round-robin")
            }
            
            src    : CompCounter()
            snk1   : io.StandardOut(store_tokens=1, quiet=1)
            snk2   : io.StandardOut(store_tokens=1, quiet=1)
            snk1.token(test1=["dummyz", "dummyy"])
            snk2.token(test1="dummyy")
            src.seq > snk1.token
            src.seq > snk2.token
        """
        app_info, errors, warnings = self.compile_script(script, "testScript")
        print errors
        print app_info

        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        time.sleep(.1)

        snk1 = d.actor_map['testScript:snk1']
        snk2 = d.actor_map['testScript:snk2']

        assert 'testScript:src:compsrc' in app_info['port_properties']
        assert 'port' in app_info['port_properties']['testScript:src:compsrc'][0]
        assert (app_info['port_properties']['testScript:src:compsrc'][0]['port'] ==
                'integer')
        assert (app_info['port_properties']['testScript:src:compsrc'][0]
                    ['properties']['routing'] == 'round-robin')

        assert 'port' in app_info['port_properties']['testScript:snk1'][0]
        assert (app_info['port_properties']['testScript:snk1'][0]['port'] ==
                'token')
        assert len(app_info['port_properties']['testScript:snk1'][0]
                    ['properties']['test1']) == 2
        assert (app_info['port_properties']['testScript:snk1'][0]
                    ['properties']['test1'][0] == 'dummyz')
        assert (app_info['port_properties']['testScript:snk1'][0]
                    ['properties']['test1'][1] == 'dummyy')
        assert (app_info['port_properties']['testScript:snk1'][0]
                    ['properties']['test2'] == 'dummyi')
        assert 'port' in app_info['port_properties']['testScript:snk2'][0]
        assert (app_info['port_properties']['testScript:snk2'][0]['port'] ==
                'token')
        assert len(app_info['port_properties']['testScript:snk2'][0]
                    ['properties']['test1']) == 1
        assert (app_info['port_properties']['testScript:snk2'][0]
                    ['properties']['test1'][0] == 'dummyy')
        assert (app_info['port_properties']['testScript:snk2'][0]
                    ['properties']['test2'] == 'dummyi')


@pytest.mark.essential
class TestPortRouting(CalvinTestBase):

    def testCollectPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        snk.token(routing="collect-unordered", nbr_peers=2)
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        actuals = [[]]
        ids = [self.rt1.id, self.rt2.id]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            time.sleep(0.2)
            to = rts[(i+1)%2]
            to_id = ids[(i+1)%2]
            fr = rts[i%2]
            actuals.append(request_handler.report(fr, snk))
            assert len(actuals[i]) < len(actuals[i+1])
            request_handler.migrate(fr, snk, to_id)

        print actuals

        high = [x for x in actuals[-1] if x > 999]
        low = [x for x in actuals[-1] if x < 999]
        self.assert_lists_equal(range(1001,1200), high, min_length=30)
        self.assert_lists_equal(range(1,200), low, min_length=30)
        d.destroy()

    def testCollectPortRemoteMoveMany2(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        snk.token(routing="collect-unordered", nbr_peers=2)
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        src2 = d.actor_map['testCollectPort:src2']
        request_handler.migrate(self.rt1, src2, self.rt2.id)
        actuals = [[]]
        ids = [self.rt1.id, self.rt2.id]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            time.sleep(0.2)
            to = rts[(i+1)%2]
            to_id = ids[(i+1)%2]
            fr = rts[i%2]
            actuals.append(request_handler.report(fr, snk))
            assert len(actuals[i]) < len(actuals[i+1])
            request_handler.migrate(fr, snk, to_id)

        print actuals

        high = [x for x in actuals[-1] if x > 999]
        low = [x for x in actuals[-1] if x < 999]
        self.assert_lists_equal(range(1001,1200), high, min_length=30)
        self.assert_lists_equal(range(1,200), low, min_length=30)
        d.destroy()

    def testCollectPortRemoteMoveMany3(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        snk.token(routing="collect-unordered", nbr_peers=2)
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        src1 = d.actor_map['testCollectPort:src1']
        src2 = d.actor_map['testCollectPort:src2']
        request_handler.migrate(self.rt1, src1, self.rt2.id)
        request_handler.migrate(self.rt1, src2, self.rt3.id)
        actuals = [[]]
        ids = [self.rt1.id, self.rt2.id]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            time.sleep(0.2)
            to = rts[(i+1)%2]
            to_id = ids[(i+1)%2]
            fr = rts[i%2]
            actuals.append(request_handler.report(fr, snk))
            assert len(actuals[i]) < len(actuals[i+1])
            request_handler.migrate(fr, snk, to_id)

        print actuals

        high = [x for x in actuals[-1] if x > 999]
        low = [x for x in actuals[-1] if x < 999]
        self.assert_lists_equal(range(1001,1200), high, min_length=30)
        self.assert_lists_equal(range(1,200), low, min_length=30)
        d.destroy()

    def testCollectTagPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        snk.token(routing="collect-tagged", nbr_peers=2)
        src1.integer(tag="src_one")
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        actuals = [[]]
        ids = [self.rt1.id, self.rt2.id]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            time.sleep(0.2)
            to = rts[(i+1)%2]
            to_id = ids[(i+1)%2]
            fr = rts[i%2]
            actuals.append(request_handler.report(fr, snk))
            assert len(actuals[i]) < len(actuals[i+1])
            request_handler.migrate(fr, snk, to_id)

        print actuals

        assert all([len(t)==1 for t in actuals[-1]])
        # Check that src_one tag is there also after last migration
        assert "src_one" in set([t.keys()[0] for t in actuals[-1][len(actuals[-2])+1:]])
        # Check that src_one tag is there before migration
        assert "src_one" in set([t.keys()[0] for t in actuals[1]])

        nbrs = [t.values()[0] for t in actuals[-1]]
        high = [x for x in nbrs if x > 999]
        low = [x for x in nbrs if x < 999]
        self.assert_lists_equal(range(1001,1200), high, min_length=30)
        self.assert_lists_equal(range(1,200), low, min_length=30)
        d.destroy()

    def testCollectTagPortRemoteMoveMany2(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        snk.token(routing="collect-tagged", nbr_peers=2)
        src1.integer(tag="src_one")
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        src2 = d.actor_map['testCollectPort:src2']
        request_handler.migrate(self.rt1, src2, self.rt2.id)
        actuals = [[]]
        ids = [self.rt1.id, self.rt2.id]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            time.sleep(0.2)
            to = rts[(i+1)%2]
            to_id = ids[(i+1)%2]
            fr = rts[i%2]
            actuals.append(request_handler.report(fr, snk))
            assert len(actuals[i]) < len(actuals[i+1])
            request_handler.migrate(fr, snk, to_id)

        print actuals

        assert all([len(t)==1 for t in actuals[-1]])
        # Check that src_one tag is there also after last migration
        assert "src_one" in set([t.keys()[0] for t in actuals[-1][len(actuals[-2])+1:]])
        # Check that src_one tag is there before migration
        assert "src_one" in set([t.keys()[0] for t in actuals[1]])

        nbrs = [t.values()[0] for t in actuals[-1]]
        high = [x for x in nbrs if x > 999]
        low = [x for x in nbrs if x < 999]
        self.assert_lists_equal(range(1001,1200), high, min_length=30)
        self.assert_lists_equal(range(1,200), low, min_length=30)
        d.destroy()

    def testCollectTagPortRemoteMoveMany3(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        snk.token(routing="collect-tagged", nbr_peers=2)
        src1.integer(tag="src_one")
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        src1 = d.actor_map['testCollectPort:src1']
        src2 = d.actor_map['testCollectPort:src2']
        request_handler.migrate(self.rt1, src1, self.rt2.id)
        request_handler.migrate(self.rt1, src2, self.rt3.id)
        actuals = [[]]
        ids = [self.rt1.id, self.rt2.id]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            time.sleep(0.2)
            to = rts[(i+1)%2]
            to_id = ids[(i+1)%2]
            fr = rts[i%2]
            actuals.append(request_handler.report(fr, snk))
            assert len(actuals[i]) < len(actuals[i+1])
            request_handler.migrate(fr, snk, to_id)

        print actuals

        assert all([len(t)==1 for t in actuals[-1]])
        # Check that src_one tag is there also after last migration
        assert "src_one" in set([t.keys()[0] for t in actuals[-1][len(actuals[-2])+1:]])
        # Check that src_one tag is there before migration
        assert "src_one" in set([t.keys()[0] for t in actuals[1]])

        nbrs = [t.values()[0] for t in actuals[-1]]
        high = [x for x in nbrs if x > 999]
        low = [x for x in nbrs if x < 999]
        self.assert_lists_equal(range(1001,1200), high, min_length=30)
        self.assert_lists_equal(range(1,200), low, min_length=30)
        d.destroy()

    def testCollectAllTagPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : io.StandardOut(store_tokens=1, quiet=1)
        snk.token(routing="collect-all-tagged", nbr_peers=2)
        src1.integer(tag="src_one")
        src2.integer(tag="src_two")
        src1.integer > snk.token
        src2.integer > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testCollectPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        actuals = [[]]
        ids = [self.rt1.id, self.rt2.id]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            time.sleep(0.2)
            to = rts[(i+1)%2]
            to_id = ids[(i+1)%2]
            fr = rts[i%2]
            actuals.append(request_handler.report(fr, snk))
            assert len(actuals[i]) < len(actuals[i+1])
            request_handler.migrate(fr, snk, to_id)

        print actuals

        assert all([len(t)==2 for t in actuals[-1]])
        # Check that src_one tag is there also after last migration
        assert "src_one" in set([k for k in t.keys() for t in actuals[-1][len(actuals[-2])+1:]])
        # Check that src_one tag is there before migration
        assert "src_one" in set([k for k in t.keys() for t in actuals[1]])

        high = [x['src_two'] for x in actuals[-1]]
        low = [x['src_one'] for x in actuals[-1]]
        self.assert_lists_equal(range(1001,1200), high, min_length=30)
        self.assert_lists_equal(range(1,200), low, min_length=30)
        d.destroy()

    def testRoundRobinPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : io.StandardOut(store_tokens=1, quiet=1)
            snk2   : io.StandardOut(store_tokens=1, quiet=1)
            src.integer(routing="round-robin")
            src.integer > snk1.token
            src.integer > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testRRPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk1 = d.actor_map['testRRPort:snk1']
        snk2 = d.actor_map['testRRPort:snk2']
        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']
        actuals1 = [[]]
        actuals2 = [[]]
        ids = [self.rt1.id, self.rt2.id]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            time.sleep(0.2)
            to = rts[(i+1)%2]
            to_id = ids[(i+1)%2]
            fr = rts[i%2]
            actuals1.append(request_handler.report(fr, snk1))
            actuals2.append(request_handler.report(fr, snk2))
            assert len(actuals1[i]) < len(actuals1[i+1])
            assert len(actuals2[i]) < len(actuals2[i+1])
            request_handler.migrate(fr, snk1, to_id)
            request_handler.migrate(fr, snk2, to_id)

        print actuals1, actuals2

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals1[-1], min_length=30)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals2[-1], min_length=30)

        d.destroy()

    def testRoundRobinPortRemoteMoveMany2(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : io.StandardOut(store_tokens=1, quiet=1)
            snk2   : io.StandardOut(store_tokens=1, quiet=1)
            src.integer(routing="round-robin")
            src.integer > snk1.token
            src.integer > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testRRPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk1 = d.actor_map['testRRPort:snk1']
        snk2 = d.actor_map['testRRPort:snk2']
        request_handler.migrate(self.rt1, snk2, self.rt2.id)
        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']
        actuals1 = [[]]
        actuals2 = [[]]
        ids = [self.rt1.id, self.rt2.id]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            time.sleep(0.2)
            to = rts[(i+1)%2]
            to_id = ids[(i+1)%2]
            fr = rts[i%2]
            fr_id = ids[i%2]
            actuals1.append(request_handler.report(fr, snk1))
            actuals2.append(request_handler.report(to, snk2))
            assert len(actuals1[i]) < len(actuals1[i+1])
            assert len(actuals2[i]) < len(actuals2[i+1])
            request_handler.migrate(fr, snk1, to_id)
            request_handler.migrate(to, snk2, fr_id)

        print actuals1, actuals2

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals1[-1], min_length=30)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals2[-1], min_length=30)

        d.destroy()

    def testRoundRobinPortRemoteMoveMany3(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : io.StandardOut(store_tokens=1, quiet=1)
            snk2   : io.StandardOut(store_tokens=1, quiet=1)
            src.integer(routing="round-robin")
            src.integer > snk1.token
            src.integer > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testRRPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk1 = d.actor_map['testRRPort:snk1']
        snk2 = d.actor_map['testRRPort:snk2']
        request_handler.migrate(self.rt1, snk1, self.rt2.id)
        request_handler.migrate(self.rt1, snk2, self.rt3.id)

        snk1_meta = request_handler.get_actor(self.rt1, snk1)
        snk2_meta = request_handler.get_actor(self.rt1, snk2)
        snk1_token_id = snk1_meta['inports'][0]['id']
        snk2_token_id = snk2_meta['inports'][0]['id']

        actual1 = request_handler.report(self.rt1, snk1)
        actual2 = request_handler.report(self.rt1, snk2)

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual1)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 20, 2)), actual2)

        actuals1 = [[]]
        actuals2 = [[]]
        ids = [self.rt2.id, self.rt3.id]
        rts = [self.rt2, self.rt3]
        for i in range(5):
            time.sleep(0.2)
            to = rts[(i+1)%2]
            to_id = ids[(i+1)%2]
            fr = rts[i%2]
            fr_id = ids[i%2]
            actuals1.append(request_handler.report(fr, snk1))
            actuals2.append(request_handler.report(to, snk2))
            assert len(actuals1[i]) < len(actuals1[i+1])
            assert len(actuals2[i]) < len(actuals2[i+1])
            request_handler.migrate(fr, snk1, to_id)
            request_handler.migrate(to, snk2, fr_id)

        print actuals1, actuals2

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals1[-1], min_length=30)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals2[-1], min_length=30)

        d.destroy()

    def testRandomPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : io.StandardOut(store_tokens=1, quiet=1)
            snk2   : io.StandardOut(store_tokens=1, quiet=1)
            src.integer(routing="random")
            src.integer > snk1.token
            src.integer > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testRRPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk1 = d.actor_map['testRRPort:snk1']
        snk2 = d.actor_map['testRRPort:snk2']
        actuals1 = [[]]
        actuals2 = [[]]
        ids = [self.rt1.id, self.rt2.id]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            time.sleep(0.2)
            to = rts[(i+1)%2]
            to_id = ids[(i+1)%2]
            fr = rts[i%2]
            actuals1.append(request_handler.report(fr, snk1))
            actuals2.append(request_handler.report(fr, snk2))
            assert len(actuals1[i]) < len(actuals1[i+1])
            assert len(actuals2[i]) < len(actuals2[i+1])
            request_handler.migrate(fr, snk1, to_id)
            request_handler.migrate(fr, snk2, to_id)

        print actuals1, actuals2

        self.assert_lists_equal(list(range(1, 200)), sorted(actuals1[-1] + actuals2[-1]), min_length=60)

        d.destroy()

    def testRandomPortRemoteMoveMany2(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : io.StandardOut(store_tokens=1, quiet=1)
            snk2   : io.StandardOut(store_tokens=1, quiet=1)
            src.integer(routing="random")
            src.integer > snk1.token
            src.integer > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testRRPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk1 = d.actor_map['testRRPort:snk1']
        snk2 = d.actor_map['testRRPort:snk2']
        request_handler.migrate(self.rt1, snk2, self.rt2.id)
        actuals1 = [[]]
        actuals2 = [[]]
        ids = [self.rt1.id, self.rt2.id]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            time.sleep(0.2)
            to = rts[(i+1)%2]
            to_id = ids[(i+1)%2]
            fr = rts[i%2]
            fr_id = ids[i%2]
            actuals1.append(request_handler.report(fr, snk1))
            actuals2.append(request_handler.report(to, snk2))
            assert len(actuals1[i]) < len(actuals1[i+1])
            assert len(actuals2[i]) < len(actuals2[i+1])
            request_handler.migrate(fr, snk1, to_id)
            request_handler.migrate(to, snk2, fr_id)

        print actuals1, actuals2

        self.assert_lists_equal(list(range(1, 200)), sorted(actuals1[-1] + actuals2[-1]), min_length=60)

        d.destroy()

    def testRandomPortRemoteMoveMany3(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : io.StandardOut(store_tokens=1, quiet=1)
            snk2   : io.StandardOut(store_tokens=1, quiet=1)
            src.integer(routing="random")
            src.integer > snk1.token
            src.integer > snk2.token
        """

        app_info, errors, warnings = self.compile_script(script, "testRRPort")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk1 = d.actor_map['testRRPort:snk1']
        snk2 = d.actor_map['testRRPort:snk2']
        request_handler.migrate(self.rt1, snk1, self.rt2.id)
        request_handler.migrate(self.rt1, snk2, self.rt3.id)
        actuals1 = [[]]
        actuals2 = [[]]
        ids = [self.rt2.id, self.rt3.id]
        rts = [self.rt2, self.rt3]
        for i in range(5):
            time.sleep(0.2)
            to = rts[(i+1)%2]
            to_id = ids[(i+1)%2]
            fr = rts[i%2]
            fr_id = ids[i%2]
            actuals1.append(request_handler.report(fr, snk1))
            actuals2.append(request_handler.report(to, snk2))
            assert len(actuals1[i]) < len(actuals1[i+1])
            assert len(actuals2[i]) < len(actuals2[i+1])
            request_handler.migrate(fr, snk1, to_id)
            request_handler.migrate(to, snk2, fr_id)

        print actuals1, actuals2

        self.assert_lists_equal(list(range(1, 200)), sorted(actuals1[-1] + actuals2[-1]), min_length=60)

        d.destroy()

    def testActorPortProperty(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Col() token -> token {
            col : std.Collect()
            .token > col.token
            col.token > .token
        }
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        colcomp : Col()
        snk : io.StandardOut(store_tokens=1, quiet=1)
        src1.integer > colcomp.token
        src2.integer > colcomp.token
        colcomp.token > snk.token
        """

        app_info, errors, warnings = self.compile_script(script, "testActorPortProperty")
        print errors
        print app_info
        assert len(errors) == 0
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk = d.actor_map['testActorPortProperty:snk']
        actuals = [[]]
        ids = [self.rt1.id, self.rt2.id]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            time.sleep(0.2)
            to = rts[(i+1)%2]
            to_id = ids[(i+1)%2]
            fr = rts[i%2]
            actuals.append(request_handler.report(fr, snk))
            assert len(actuals[i]) < len(actuals[i+1])
            request_handler.migrate(fr, snk, to_id)

        print actuals

        high = [x for x in actuals[-1] if x > 999]
        low = [x for x in actuals[-1] if x < 999]
        self.assert_lists_equal(range(1001,1200), high, min_length=30)
        self.assert_lists_equal(range(1,200), low, min_length=30)
        d.destroy()
