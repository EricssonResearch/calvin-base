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
import time
import pytest

from calvin.csparser import cscompile as compiler
from calvin.Tools import deployer
from calvin.utilities import calvinconfig
from calvin.utilities import calvinlogger
from calvin.requests.request_handler import RequestHandler

from . import helpers

_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()


runtimes = []
peerlist = []
test_type = None
request_handler = None


def expected_tokens(rt, actor_id, t_type):
    return helpers.expected_tokens(request_handler, rt, actor_id, t_type)


def wait_for_tokens(rt, actor_id, size=5, retries=20):
    return helpers.wait_for_tokens(request_handler, rt, actor_id, size, retries)

    
def actual_tokens(rt, actor_id, size=5, retries=20):
    return helpers.actual_tokens(request_handler, rt, actor_id, size, retries)
    
        
def setup_module(module):
    global runtimes
    global peerlist
    global request_handler
    global test_type

    request_handler = RequestHandler()

    _log.info(" ---> Setup")
    test_type, runtimes, peerlist = helpers.setup_test_type(request_handler)


def teardown_module(module):
    global runtimes
    global test_type
    global request_handler

    _log.info(" ---> Teardown")
    helpers.teardown_test_type(request_handler, runtimes, test_type)


class CalvinTestBase(unittest.TestCase):

    def assert_lists_equal(self, expected, actual):
        assert actual
        assert reduce(lambda a, b: a and b[0] == b[1], zip(expected, actual), True) 
        
    def setUp(self):
        self.runtime = runtimes[0]
        self.runtimes = runtimes[1:]
        self.peerlist = peerlist

    def compile_script(self, script, name):
        # Instead of rewriting tests after compiler.compile_script changed
        # from returning app_info, errors, warnings to app_info, issuetracker
        # use this stub in tests to keep old behaviour
        app_info, issuetracker = compiler.compile_script(script, name)
        return app_info, issuetracker.errors(), issuetracker.warnings()

    def wait_for_migration(self, runtime, actors, retries=10):
        from functools import partial
        
        if not isinstance(actors, list):
            actors = [ actors ]
        
        for actor in actors:
            check_actors = partial(request_handler.get_actor, runtime, actor)
            criteria = lambda _ : True
            helpers.retry(retries, check_actors, criteria, "Migration of '%r' failed" % (actor, ))


    def migrate(self, source, dest, actor):
        request_handler.migrate(source, actor, dest.id)
        self.wait_for_migration(dest, [actor])
        
        
@pytest.mark.slow
@pytest.mark.essential
class TestNodeSetup(CalvinTestBase):

    """Testing starting a node"""

    def testStartNode(self):
        """Testing starting node"""

        rt, id_, peers = self.runtime, self.runtime.id, self.peerlist
        assert request_handler.get_node(rt, id_)['uri'] == rt.uri


@pytest.mark.essential
@pytest.mark.slow
class TestLocalConnectDisconnect(CalvinTestBase):

    """Testing local connect/disconnect/re-connect"""

    def testLocalSourceSink(self):
        """Testing local source and sink"""

        rt, id_, peers = self.runtime, self.runtime.id, self.peerlist

        # Setup
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        request_handler.connect(rt, snk, 'token', id_, src, 'integer')

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

        rt, id_ = self.runtime, self.runtime.id

        src = request_handler.new_actor(rt, "std.CountTimer", "src")
        snk = request_handler.new_actor_wargs(rt, "io.StandardOut", "snk", store_tokens=1, quiet=1)

        request_handler.connect(rt, snk, 'token', id_, src, 'integer')

        # Wait for some tokens
        actual = wait_for_tokens(rt, snk)

        # Disconnect/reconnect
        request_handler.disconnect(rt, snk)
        request_handler.connect(rt, snk, 'token', id_, src, 'integer')
        
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

        rt, id_ = self.runtime, self.runtime.id

        src = request_handler.new_actor(rt, "std.CountTimer", "src")
        snk = request_handler.new_actor_wargs(rt, "io.StandardOut", "snk", store_tokens=1, quiet=1)
        request_handler.connect(rt, snk, "token", id_, src, "integer")
        
        # Wait for some tokens
        actual = wait_for_tokens(rt, snk)
        
        # disconnect/reconnect
        request_handler.disconnect(rt, src)
        request_handler.connect(rt, snk, "token", id_, src, "integer")
        
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

        rt, id_ = self.runtime, self.runtime.id

        src = request_handler.new_actor(rt, "std.CountTimer", "src")
        sum_ = request_handler.new_actor(rt, "std.Sum", "sum")
        snk = request_handler.new_actor_wargs(rt, "io.StandardOut", "snk", store_tokens=1, quiet=1)

        request_handler.connect(rt, snk, "token", id_, sum_, "integer")
        request_handler.connect(rt, sum_, "integer", id_, src, "integer")
        
        # Wait for some tokens
        actual = wait_for_tokens(rt, snk)

        # disconnect/reconnect
        request_handler.disconnect(rt, sum_)
        request_handler.connect(rt, snk, "token", id_, sum_, "integer")
        request_handler.connect(rt, sum_, "integer", id_, src, "integer")
      
        # Wait for one more token
        wait_for_tokens(rt, snk, len(actual)+1)
        
        # Fetch sent/received
        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))

        request_handler.disconnect(rt, src)

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, src)
        request_handler.delete_actor(rt, sum_)
        request_handler.delete_actor(rt, snk)

    def testTimerLocalSourceSink(self):
        """Testing timer based local source and sink"""

        rt, id_, peers = self.runtime, self.runtime.id, self.peerlist

        src = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src', sleep=0.1, steps=10)
        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        request_handler.connect(rt, snk, 'token', id_, src, 'integer')

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

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        sum_ = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        request_handler.connect(peer, sum_, 'integer', id_, src, 'integer')
        
        # Wait for some tokens
        wait_for_tokens(rt, snk)

        request_handler.disconnect(rt, src)

        # Fetch sent/received
        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        
        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, sum_)
        request_handler.delete_actor(rt, src)

    def testRemoteSlowPort(self):
        """Testing remote slow port and that token flow control works"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk1 = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk1', store_tokens=1, quiet=1)
        alt = request_handler.new_actor(peer, 'std.Alternate', 'alt')
        src1 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src1', sleep=0.1, steps=100)
        src2 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src2', sleep=1.0, steps=10)

        request_handler.connect(rt, snk1, 'token', peer_id, alt, 'token')
        request_handler.connect(peer, alt, 'token_1', id_, src1, 'integer')
        request_handler.connect(peer, alt, 'token_2', id_, src2, 'integer')
        
        wait_for_tokens(rt, snk1)

        request_handler.disconnect(rt, src1)
        request_handler.disconnect(rt, src2)

        expected_1 = expected_tokens(rt, src1, 'seq')
        expected_2 = expected_tokens(rt, src2, 'seq')
        expected = helpers.flatten_zip(zip(expected_1, expected_2))

        actual = actual_tokens(rt, snk1, len(expected))

        self.assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt, snk1)
        request_handler.delete_actor(peer, alt)
        request_handler.delete_actor(rt, src1)
        request_handler.delete_actor(rt, src2)

    def testRemoteSlowFanoutPort(self):
        """Testing remote slow port with fan out and that token flow control works"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk1 = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(peer, 'io.StandardOut', 'snk2', store_tokens=1, quiet=1)
        alt = request_handler.new_actor(peer, 'std.Alternate', 'alt')
        src1 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src1', sleep=0.1, steps=100)
        src2 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src2', sleep=1.0, steps=10)

        request_handler.connect(rt, snk1, 'token', peer_id, alt, 'token')
        request_handler.connect(peer, snk2, 'token', id_, src1, 'integer')
        request_handler.connect(peer, alt, 'token_1', id_, src1, 'integer')
        request_handler.connect(peer, alt, 'token_2', id_, src2, 'integer')
        
        # Wait for some tokens
        wait_for_tokens(rt, snk1)
        wait_for_tokens(peer, snk2)
        
        request_handler.disconnect(rt, src1)
        request_handler.disconnect(rt, src2)
        
        expected_1 = expected_tokens(rt, src1, 'seq')
        expected_2 = expected_tokens(rt, src2, 'seq')
        expected = helpers.flatten_zip(zip(expected_1, expected_2))
        actual = actual_tokens(rt, snk1, len(expected))

        self.assert_lists_equal(expected, actual)
        
        actual = actual_tokens(peer, snk2, len(expected))
        self.assert_lists_equal(expected_1, actual)

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

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id
        
        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        sum_ = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        request_handler.connect(peer, sum_, 'integer', id_, src, 'integer')
        
        actual_1 = wait_for_tokens(rt, snk)
        
        self.migrate(rt, peer, src)
        
        # Wait for at least queue + 1 tokens
        wait_for_tokens(rt, snk, len(actual_1)+5)
        expected = expected_tokens(peer, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        
        self.assert_lists_equal(expected, actual)
        
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, sum_)
        request_handler.delete_actor(peer, src)

    def testFanOutPortLocalToRemoteMigration(self):
        """Testing outport with fan-out local to remote migration"""

        rt = self.runtime
        peer = self.runtimes[0]

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

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk1 = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(peer, 'io.StandardOut', 'snk2', store_tokens=1, quiet=1)
        alt = request_handler.new_actor(peer, 'std.Alternate', 'alt')
        src1 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src1', sleep=0.1, steps=100)
        src2 = request_handler.new_actor_wargs(rt, 'std.CountTimer', 'src2', sleep=0.1, steps=100)

        request_handler.set_port_property(peer, alt, 'out', 'token',
                                            port_properties={'routing': 'fanout', 'nbr_peers': 2})

        request_handler.connect(rt, snk1, 'token', peer_id, alt, 'token')
        request_handler.connect(peer, snk2, 'token', peer_id, alt, 'token')
        request_handler.connect(peer, alt, 'token_1', id_, src1, 'integer')
        request_handler.connect(peer, alt, 'token_2', id_, src2, 'integer')
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

        rt = self.runtime
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        sum_ = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(peer, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        request_handler.connect(peer, sum_, 'integer', peer_id, src, 'integer')
        wait_for_tokens(rt, snk)

        actual_1 = actual_tokens(rt, snk)
        self.migrate(peer, rt, src)
        
        # Make sure that we got at least 5 more tokens since we could have transfered but unprocessed in queue
        wait_for_tokens(rt, snk, len(actual_1)+5)
        
        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        self.assert_lists_equal(expected, actual)
        
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, sum_)
        request_handler.delete_actor(rt, src)

    def testOutPortLocalRemoteRepeatedMigration(self):
        """Testing outport local to remote migration and back repeatedly"""

        rt = self.runtime
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        sum_ = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(peer, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        request_handler.connect(peer, sum_, 'integer', peer_id, src, 'integer')
        
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
        request_handler.delete_actor(peer, sum_)
        request_handler.delete_actor(rt, src)

    def testInOutPortRemoteToLocalMigration(self):
        """Testing out- and inport remote to local migration"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]
        peer_id = peer.id

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        sum_ = request_handler.new_actor(peer, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer_id, sum_, 'integer')
        request_handler.connect(peer, sum_, 'integer', id_, src, 'integer')

        actual_1 = wait_for_tokens(rt, snk)

        self.migrate(peer, rt, sum_)

        wait_for_tokens(rt, snk, len(actual_1)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        self.assert_lists_equal(expected, actual)
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(rt, sum_)
        request_handler.delete_actor(rt, src)

    def testInOutPortLocalRemoteRepeatedMigration(self):
        """Testing outport local to remote migration and revers repeatedly"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        sum_ = request_handler.new_actor(rt, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', id_, sum_, 'integer')
        request_handler.connect(rt, sum_, 'integer', id_, src, 'integer')
        wait_for_tokens(rt, snk)

        actual_x = actual_tokens(rt, snk)
        for i in range(5):
            if i % 2 == 0:
                self.migrate(rt, peer, sum_)
            else:
                self.migrate(peer, rt, sum_)
            actual_x = actual_tokens(rt, snk, len(actual_x)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        self.assert_lists_equal(expected, actual)
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, sum_)
        request_handler.delete_actor(rt, src)

    def testInOutPortLocalToRemoteMigration(self):
        """Testing out- and inport local to remote migration"""

        rt = self.runtime
        id_ = rt.id
        peer = self.runtimes[0]

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        sum_ = request_handler.new_actor(rt, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', id_, sum_, 'integer')
        request_handler.connect(rt, sum_, 'integer', id_, src, 'integer')
        wait_for_tokens(rt, snk)

        actual_1 = wait_for_tokens(rt, snk)
        self.migrate(rt, peer, sum_)
        wait_for_tokens(rt, snk, len(actual_1)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        self.assert_lists_equal(expected, actual)
        
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer, sum_)
        request_handler.delete_actor(rt, src)


    def testInOutPortRemoteToRemoteMigration(self):
        """Testing out- and inport remote to remote migration"""

        rt = self.runtime
        id_ = rt.id
        peer0 = self.runtimes[0]
        peer0_id = peer0.id
        peer1 = self.runtimes[1]

        snk = request_handler.new_actor_wargs(rt, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        sum_ = request_handler.new_actor(peer0, 'std.Sum', 'sum')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(rt, snk, 'token', peer0_id, sum_, 'integer')
        request_handler.connect(peer0, sum_, 'integer', id_, src, 'integer')
        wait_for_tokens(rt, snk)

        actual_1 = actual_tokens(rt, snk)
        self.migrate(peer0, peer1, sum_)
        wait_for_tokens(rt, snk, len(actual_1)+5)

        expected = expected_tokens(rt, src, 'sum')
        actual = actual_tokens(rt, snk, len(expected))
        self.assert_lists_equal(expected, actual)
        request_handler.delete_actor(rt, snk)
        request_handler.delete_actor(peer1, sum_)
        request_handler.delete_actor(rt, src)

    def testExplicitStateMigration(self):
        """Testing migration of explicit state handling"""

        rt = self.runtime
        id_ = rt.id
        peer0 = self.runtimes[0]

        snk = request_handler.new_actor_wargs(peer0, 'io.StandardOut', 'snk', store_tokens=1, quiet=1)
        wrapper = request_handler.new_actor(rt, 'misc.ExplicitStateExample', 'wrapper')
        src = request_handler.new_actor(rt, 'std.CountTimer', 'src')

        request_handler.connect(peer0, snk, 'token', id_, wrapper, 'token')
        request_handler.connect(rt, wrapper, 'token', id_, src, 'integer')

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
        rt = self.runtime

        script = """
      src : std.CountTimer()
      snk : io.StandardOut(store_tokens=1, quiet=1)
      src.integer > snk.token
    """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt, app_info)
        d.deploy() # ignoring app_id here

        src = d.actor_map['simple:src']
        snk = d.actor_map['simple:snk']

        wait_for_tokens(rt, snk)
        expected = expected_tokens(rt, src, 'seq')
        actual = actual_tokens(rt, snk, len(expected))
        request_handler.disconnect(rt, src)


        self.assert_lists_equal(expected, actual)
        helpers.destroy_app(d)

    def testDestroyAppWithLocalActors(self):
        rt = self.runtime

        script = """
      src : std.CountTimer()
      snk : io.StandardOut(store_tokens=1, quiet=1)
      src.integer > snk.token
    """
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt, app_info)
        app_id = d.deploy()

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
        rt = self.runtime
        rt1 = self.runtimes[0]
        rt2 = self.runtimes[1]

        script = """
      src : std.CountTimer()
      snk : io.StandardOut(store_tokens=1, quiet=1)
      src.integer > snk.token"""
      
        app_info, errors, warnings = self.compile_script(script, "simple")
        d = deployer.Deployer(rt, app_info)
        app_id = d.deploy()

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
