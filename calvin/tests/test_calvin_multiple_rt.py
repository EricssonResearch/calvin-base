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
import numbers
from collections import Counter

from calvin.utilities import calvinconfig
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

def actual_tokens_multiple(rt, actor_ids, size=5, retries=20):
    return helpers.actual_tokens_multiple(request_handler, rt, actor_ids, size, retries)

def assert_lists_equal(expected, actual, min_length=5):
    assert len(actual) >= min_length
    assert actual
    assert reduce(lambda a, b: a and b[0] == b[1], zip(expected, actual), True)

def wait_for_migration(runtime, actors, retries=20):
    retry = 0
    if not isinstance(actors, list):
        actors = [ actors ]
    while retry < retries:
        try:
            current = request_handler.get_actors(runtime)
            if set(actors).issubset(set(current)):
                break
            else:
                _log.info("Migration not finished, retrying in %f" % (retry * 0.1,))
                retry += 1
                time.sleep(retry * 0.1)
        except Exception as e:
            _log.info("Migration not finished %s, retrying in %f" % (str(e), retry * 0.1,))
            retry += 1
            time.sleep(retry * 0.1)
    if retry == retries:
        _log.info("Migration failed, after %d retires" % (retry,))
        raise Exception("Migration failed")

def migrate(source, dest, actor):
    request_handler.migrate(source, actor, dest.id)
    wait_for_migration(dest, [actor])

def wait_until_nbr(rt, actor_id, size=5, retries=20, sleep=0.1):
    for i in range(retries):
        r = request_handler.report(rt, actor_id)
        l = r if isinstance(r, numbers.Number) else len(r)
        if l >= size:
            break
        time.sleep(sleep)
    assert l >= size

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

    helpers.teardown_test_type(test_type, [rt1, rt2, rt3], request_handler)


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

    def get_port_property(self, app_info, actor, port, direction, key):
        """Access port properties in a robust way since order might change between parser revisions"""
        # Get list of port properties
        props = app_info['port_properties'][actor]
        for p in props:
            found = p['direction'] == direction and p['port'] == port
            if not found:
                continue
            return p['properties'][key]
        raise KeyError("Property '{}' not present.".format(key))

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
                current = request_handler.get_actors(runtime)
                if set(actors).issubset(set(current)):
                    break
                else:
                    _log.info("Migration not finished, retrying in %f" % (retry * 0.1,))
                    retry += 1
                    time.sleep(retry * 0.1)
            except Exception as e:
                _log.info("Migration not finished %s, retrying in %f" % (str(e), retry * 0.1,))
                retry += 1
                time.sleep(retry * 0.1)
        if retry == retries:
            _log.info("Migration failed, after %d retires" % (retry,))
            raise Exception("Migration failed")

    def migrate(self, source, dest, actor):
        request_handler.migrate(source, actor, dest.id)
        self.wait_for_migration(dest, [actor])

@pytest.fixture(params=[("rt1", "rt2"), ("rt1", "rt1")])
def rt_order(request):
    return [globals()[p] for p in request.param]


@pytest.mark.essential
@pytest.mark.slow
class TestAdvancedConnectDisconnect(object):

    """Testing advanced connect/disconnect """
    # Can't use the unittest.TestCase class since uses parameterization

    def testAdvancedSourceDisconnectTerminate(self, rt_order):
        rt1 = rt_order[0]
        rt2 = rt_order[1]

        # Setup
        src = request_handler.new_actor(rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(rt2, 'test.Sink', 'snk', store_tokens=1, quiet=1)
        request_handler.set_port_property(rt2, snk, 'in', 'token',
                                            port_properties={'routing': 'collect-unordered'})
        request_handler.connect(rt2, snk, 'token', rt1.id, src, 'integer')

        # Wait for some tokens to arrive
        wait_for_tokens(rt2, snk)

        src_meta = request_handler.get_actor(rt1, src)
        src_port = src_meta['outports'][0]['id']
        src_port_meta = request_handler.get_port(rt1, src, src_port)
        snk_meta = request_handler.get_actor(rt2, snk)
        snk_port = snk_meta['inports'][0]['id']
        snk_port_meta = request_handler.get_port(rt2, snk, snk_port)

        # Check what was sent
        expected = expected_tokens(rt1, src, 'seq')

        request_handler.disconnect(rt1, src, terminate="TERMINATE")

        for i in range(10):
            src_port_meta_dc = request_handler.get_port(rt1, src, src_port)
            snk_port_meta_dc = request_handler.get_port(rt2, snk, snk_port)
            if not src_port_meta_dc['peers'] and not snk_port_meta_dc['peers']:
                break
            time.sleep(0.5)

        #print src_port_meta, snk_port_meta
        #print src_port_meta_dc, snk_port_meta_dc

        assert not src_port_meta_dc['peers']
        assert not snk_port_meta_dc['peers']

        # Wait for it to arrive
        #actual = actual_tokens(rt, snk, len(expected))
        #print actual

        # Assert the sent and arrived are identical
        #assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt1, src)
        request_handler.delete_actor(rt2, snk)

    def testAdvancedSinkDisconnectTerminate(self, rt_order):
        rt1 = rt_order[0]
        rt2 = rt_order[1]

        # Setup
        src = request_handler.new_actor(rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(rt2, 'test.Sink', 'snk', store_tokens=1, quiet=1)
        request_handler.set_port_property(rt2, snk, 'in', 'token',
                                            port_properties={'routing': 'collect-unordered'})
        request_handler.connect(rt2, snk, 'token', rt1.id, src, 'integer')

        # Wait for some tokens to arrive
        wait_for_tokens(rt2, snk)

        src_meta = request_handler.get_actor(rt1, src)
        src_port = src_meta['outports'][0]['id']
        src_port_meta = request_handler.get_port(rt1, src, src_port)
        snk_meta = request_handler.get_actor(rt2, snk)
        snk_port = snk_meta['inports'][0]['id']
        snk_port_meta = request_handler.get_port(rt2, snk, snk_port)

        # Check what was sent
        expected = expected_tokens(rt1, src, 'seq')

        request_handler.disconnect(rt2, snk, terminate="TERMINATE")

        for i in range(10):
            src_port_meta_dc = request_handler.get_port(rt1, src, src_port)
            snk_port_meta_dc = request_handler.get_port(rt2, snk, snk_port)
            if not src_port_meta_dc['peers'] and not snk_port_meta_dc['peers']:
                break
            time.sleep(0.5)

        #print src_port_meta, snk_port_meta
        #print src_port_meta_dc, snk_port_meta_dc

        assert not src_port_meta_dc['peers']
        assert not snk_port_meta_dc['peers']

        # Wait for it to arrive
        #actual = actual_tokens(rt, snk, len(expected))
        #print actual

        # Assert the sent and arrived are identical
        #assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt1, src)
        request_handler.delete_actor(rt2, snk)

    def testAdvancedSinkDisconnectExhaust(self, rt_order):
        rt1 = rt_order[0]
        rt2 = rt_order[1]

        # Setup
        src = request_handler.new_actor(rt1, 'std.Counter', 'src')
        snk = request_handler.new_actor_wargs(rt2, 'test.Sink', 'snk', store_tokens=1, quiet=1, active=False)
        request_handler.set_port_property(rt2, snk, 'in', 'token',
                                            port_properties={'routing': 'collect-unordered'})
        request_handler.connect(rt2, snk, 'token', rt1.id, src, 'integer')

        src_meta = request_handler.get_actor(rt1, src)
        src_port = src_meta['outports'][0]['id']
        src_port_meta = request_handler.get_port(rt1, src, src_port)
        snk_meta = request_handler.get_actor(rt2, snk)
        snk_port = snk_meta['inports'][0]['id']
        snk_port_meta = request_handler.get_port(rt2, snk, snk_port)

        # Check what was sent
        for i in range(10):
            time.sleep(0.1)
            expected = expected_tokens(rt1, src, 'seq')
            if len(expected) >= 8:
                break
        assert len(expected) >= 8

        # Sink is paused, hence 4 + 4 tokens in out and in queues.
        # Disconnect exhaust will move the tokens to in queue
        request_handler.disconnect(rt2, snk, terminate="EXHAUST")

        for i in range(10):
            src_port_meta_dc = request_handler.get_port(rt1, src, src_port)
            snk_port_meta_dc = request_handler.get_port(rt2, snk, snk_port)
            if not src_port_meta_dc['peers'] and not snk_port_meta_dc['peers']:
                break
            time.sleep(0.5)

        print src_port_meta, snk_port_meta
        print src_port_meta_dc, snk_port_meta_dc

        assert not src_port_meta_dc['peers']
        assert not snk_port_meta_dc['peers']

        # Wait for tokens to arrive
        request_handler.report(rt2, snk, kwargs={'active': True})
        # Wait for it to arrive
        actual = actual_tokens(rt2, snk, len(expected))
        print actual

        port_state_dc = request_handler.report(rt2, snk, kwargs={'port': None})

        # Assert the sent and arrived are identical
        assert_lists_equal(expected, actual)
        assert not port_state_dc['queue']['writers']

        request_handler.delete_actor(rt1, src)
        request_handler.delete_actor(rt2, snk)

    def testAdvancedSourceDisconnectExhaust(self, rt_order):
        rt1 = rt_order[0]
        rt2 = rt_order[1]

        # Setup
        src = request_handler.new_actor(rt1, 'std.Counter', 'src')
        snk = request_handler.new_actor_wargs(rt2, 'test.Sink', 'snk', store_tokens=1, quiet=1, active=False)
        request_handler.set_port_property(rt2, snk, 'in', 'token',
                                            port_properties={'routing': 'collect-unordered'})
        request_handler.connect(rt2, snk, 'token', rt1.id, src, 'integer')

        src_meta = request_handler.get_actor(rt1, src)
        src_port = src_meta['outports'][0]['id']
        src_port_meta = request_handler.get_port(rt1, src, src_port)
        snk_meta = request_handler.get_actor(rt2, snk)
        snk_port = snk_meta['inports'][0]['id']
        snk_port_meta = request_handler.get_port(rt2, snk, snk_port)
        port_state = request_handler.report(rt2, snk, kwargs={'port': None})

        # Check what was sent
        for i in range(10):
            time.sleep(0.1)
            expected = expected_tokens(rt1, src, 'seq')
            if len(expected) >= 8:
                break
        assert len(expected) >= 8

        # Sink is paused, hence 4 + 4 tokens in out- and in-queues.
        # Disconnect exhaust will move the tokens to in queue
        request_handler.disconnect(rt1, src, terminate="EXHAUST")

        for i in range(10):
            src_port_meta_dc = request_handler.get_port(rt1, src, src_port)
            if not src_port_meta_dc['peers']:
                break
            time.sleep(0.5)

        print src_port_meta
        print src_port_meta_dc

        assert not src_port_meta_dc['peers']

        # Accept tokens and wait for tokens to arrive
        request_handler.report(rt2, snk, kwargs={'active': True})
        actual = actual_tokens(rt2, snk, len(expected))
        print actual

        for i in range(10):
            snk_port_meta_dc = request_handler.get_port(rt2, snk, snk_port)
            if not snk_port_meta_dc['peers']:
                break
            time.sleep(0.5)

        port_state_dc = request_handler.report(rt2, snk, kwargs={'port': None})

        print port_state
        print port_state_dc
        print snk_port_meta
        print snk_port_meta_dc

        assert not port_state_dc['queue']['writers']
        assert not snk_port_meta_dc['peers']

        # Assert the sent and arrived are identical
        assert_lists_equal(expected, actual)

        request_handler.delete_actor(rt1, src)
        request_handler.delete_actor(rt2, snk)

@pytest.mark.essential
@pytest.mark.slow
class TestRemoteConnection(CalvinTestBase):

    """Testing remote connections"""

    def testRemoteOneActor(self):
        """Testing remote port"""
        from twisted.python import log
        from twisted.internet import defer
        import sys
        defer.setDebugging(True)
        log.startLogging(sys.stdout)

        rt = self.rt1
        peer = self.rt2

        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
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

        snk1 = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk1', store_tokens=1, quiet=1)
        alt = request_handler.new_actor(peer, 'flow.Alternate2', 'alt')
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

        snk1 = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(peer, 'test.Sink', 'snk2', store_tokens=1, quiet=1)
        alt = request_handler.new_actor(peer, 'flow.Alternate2', 'alt')
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

        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
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
        snk_1 = request_handler.new_actor_wargs(rt, "test.Sink", "snk-1", store_tokens=1, quiet=1)
        snk_2 = request_handler.new_actor_wargs(rt, "test.Sink", "snk-2", store_tokens=1, quiet=1)

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

        snk1 = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk1', store_tokens=1, quiet=1)
        snk2 = request_handler.new_actor_wargs(peer, 'test.Sink', 'snk2', store_tokens=1, quiet=1)
        alt = request_handler.new_actor(peer, 'flow.Alternate2', 'alt')
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

        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
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

        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
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

        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
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

        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
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

        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
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

        snk = request_handler.new_actor_wargs(rt, 'test.Sink', 'snk', store_tokens=1, quiet=1)
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

        snk = request_handler.new_actor_wargs(peer0, 'test.Sink', 'snk', store_tokens=1, quiet=1)
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

    def testDestroyAppWithMigratedActors(self):
        rt, rt1, rt2 = get_runtime(3)

        script = """
      src : std.CountTimer()
      snk : test.Sink(store_tokens=1, quiet=1)
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

    def testMigrateSink(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = request_handler.new_actor_wargs(self.rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

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
        snk = request_handler.new_actor_wargs(self.rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

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
        snk = request_handler.new_actor_wargs(self.rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

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
        snk = request_handler.new_actor_wargs(self.rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

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


class TestStateMigration(CalvinTestBase):

    def testSimpleState(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          sum : std.Sum()
          snk : test.Sink(store_tokens=1, quiet=1)
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
          snk : test.Sink(store_tokens=1, quiet=1)
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
                try:
                    a = request_handler.get_actor(runtime, actor)
                    if a is not None:
                        _log.info("Actor '%r' still present on runtime '%r" % (actor, runtime.id, ))
                        return False
                except:
                    pass
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
                if msg.startswith("404"):
                    return True
            return app is None

        for rt in [ self.rt1, self.rt2, self.rt3 ]:
            check_rt = partial(check_application_gone, rt)
            all_gone = helpers.retry(20, check_rt, lambda x: x, "Application still present on rt '%r'" % (rt.id, ))
            assert all_gone

    def testAppDestructionAllRemote(self):
        from functools import partial
        _log.analyze("TESTRUN", "+", {})
        script = """
          src : std.CountTimer()
          sum : std.Sum()
          snk : test.Sink(store_tokens=1, quiet=1)
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
                try:
                    a = request_handler.get_actor(runtime, actor)
                    if a is not None:
                        _log.info("Actor '%r' still present on runtime '%r" % (actor, runtime.id, ))
                        return False
                except:
                    pass
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
                if msg.startswith("404"):
                    return True
            return app is None

        for rt in [ self.rt1, self.rt2, self.rt3 ]:
            check_rt = partial(check_application_gone, rt)
            all_gone = helpers.retry(20, check_rt, lambda x: x, "Application still present on rt '%r'" % (rt.id, ))
            assert all_gone


@pytest.mark.essential
class TestEnabledToEnabledBug(CalvinTestBase):

    def test21(self):
        _log.analyze("TESTRUN", "+", {})
        src = request_handler.new_actor(self.rt1, 'std.Counter', 'src')
        ity = request_handler.new_actor(self.rt2, 'std.Identity', 'ity')
        snk = request_handler.new_actor_wargs(self.rt3, 'test.Sink', 'snk', store_tokens=1, quiet=1)

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
        snk = request_handler.new_actor_wargs(self.rt3, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        request_handler.connect(self.rt2, ity, 'token', self.rt1.id, src, 'integer')
        request_handler.connect(self.rt3, snk, 'token', self.rt2.id, ity, 'token')

        actual = actual_tokens(self.rt3, snk, 10)
        self.assert_lists_equal(range(1,10), actual)

        actual = actual_tokens(self.rt3, snk, len(actual)+1)
        self.assert_lists_equal(range(1,len(actual)), actual)

        request_handler.delete_actor(self.rt1, src)
        request_handler.delete_actor(self.rt2, ity)
        request_handler.delete_actor(self.rt3, snk)

@pytest.mark.essential
class TestCollectPort(CalvinTestBase):

    def testCollectPortRemote(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.01, start=1, steps=5)
        src2 : std.CountTimer(sleep=0.01, start=1001, steps=5)
        snk : test.Sink(store_tokens=1, quiet=1)
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
        assert (self.get_port_property(app_info, 'testCollectPort:snk', 'token', 'in', 'nbr_peers') == 2)
        d = deployer.Deployer(self.rt1, app_info)
        d.deploy()
        snk = d.actor_map['testCollectPort:snk']
        self.migrate(self.rt1, self.rt2, snk)
        actual = wait_for_tokens(self.rt2, snk, 10)

        high = [x for x in actual if x > 999]
        low = [x for x in actual if x < 999]
        self.assert_lists_equal(range(1001,1006), high, min_length=4)
        self.assert_lists_equal(range(1,6), low, min_length=4)
        helpers.destroy_app(d)


@pytest.mark.essential
class TestPortRouting(CalvinTestBase):

    def testCollectPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
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
        rts = [self.rt1, self.rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            self.migrate(fr, to, snk)

        print actuals

        high = [x for x in actuals[-1] if x > 999]
        low = [x for x in actuals[-1] if x < 999]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    def testCollectPortRemoteMoveMany2(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
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
        self.migrate(self.rt1, self.rt2, src2)
        actuals = [[]]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            self.migrate(fr, to, snk)

        print actuals

        high = [x for x in actuals[-1] if x > 999]
        low = [x for x in actuals[-1] if x < 999]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    def testCollectPortRemoteMoveMany3(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
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
        self.migrate(self.rt1, self.rt2, src1)
        self.migrate(self.rt1, self.rt3, src2)
        actuals = [[]]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            self.migrate(fr, to, snk)

        print actuals

        high = [x for x in actuals[-1] if x > 999]
        low = [x for x in actuals[-1] if x < 999]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    def testCollectTagPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
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
        rts = [self.rt1, self.rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            self.migrate(fr, to, snk)

        print actuals

        assert all([len(t)==1 for t in actuals[-1]])
        # Check that src_one tag is there also after last migration
        assert "src_one" in set([t.keys()[0] for t in actuals[-1][len(actuals[-2])+1:]])
        # Check that src_one tag is there before migration
        assert "src_one" in set([t.keys()[0] for t in actuals[1]])

        nbrs = [t.values()[0] for t in actuals[-1]]
        high = [x for x in nbrs if x > 999]
        low = [x for x in nbrs if x < 999]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    def testCollectTagPortRemoteMoveMany2(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
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
        self.migrate(self.rt1, self.rt2, src2)
        actuals = [[]]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            assert len(actuals[i]) < len(actuals[i+1])
            self.migrate(fr, to, snk)

        print actuals

        assert all([len(t)==1 for t in actuals[-1]])
        # Check that src_one tag is there also after last migration
        assert "src_one" in set([t.keys()[0] for t in actuals[-1][len(actuals[-2])+1:]])
        # Check that src_one tag is there before migration
        assert "src_one" in set([t.keys()[0] for t in actuals[1]])

        nbrs = [t.values()[0] for t in actuals[-1]]
        high = [x for x in nbrs if x > 999]
        low = [x for x in nbrs if x < 999]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    def testCollectTagPortRemoteMoveMany3(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
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
        self.migrate(self.rt1, self.rt2, src1)
        self.migrate(self.rt1, self.rt3, src2)
        actuals = [[]]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            self.migrate(fr, to, snk)

        print actuals

        assert all([len(t)==1 for t in actuals[-1]])
        # Check that src_one tag is there also after last migration
        assert "src_one" in set([t.keys()[0] for t in actuals[-1][len(actuals[-2])+1:]])
        # Check that src_one tag is there before migration
        assert "src_one" in set([t.keys()[0] for t in actuals[1]])

        nbrs = [t.values()[0] for t in actuals[-1]]
        high = [x for x in nbrs if x > 999]
        low = [x for x in nbrs if x < 999]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    def testCollectAllTagPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
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
        rts = [self.rt1, self.rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            self.migrate(fr, to, snk)

        print actuals

        assert all([len(t)==2 for t in actuals[-1]])
        # Check that src_one tag is there also after last migration
        assert "src_one" in set([k for t in actuals[-1][len(actuals[-2])+1:] for k in t.keys()])
        # Check that src_one tag is there before migration
        assert "src_one" in set([k for t in actuals[1] for k in t.keys()])

        high = [x['src_two'] for x in actuals[-1]]
        low = [x['src_one'] for x in actuals[-1]]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)

    def testCollectAnyTagPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        snk : test.Sink(store_tokens=1, quiet=1)
        snk.token(routing="collect-any-tagged", nbr_peers=2)
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
        rts = [self.rt1, self.rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, len(actuals[i]) + 10))
            self.migrate(fr, to, snk)

        print actuals

        assert all([len(t) in [1, 2] for t in actuals[-1]])
        # Check that src_one tag is there also after last migration
        assert "src_one" in set([k for t in actuals[-1][len(actuals[-2])+1:] for k in t.keys()])
        # Check that src_one tag is there before migration
        assert "src_one" in set([k for t in actuals[1] for k in t.keys()])

        high = [x['src_two'] for x in actuals[-1] if 'src_two' in x]
        low = [x['src_one'] for x in actuals[-1] if 'src_one' in x]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=20)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=20)
        helpers.destroy_app(d)


    def testRoundRobinPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
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
        rts = [self.rt1, self.rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actual1, actual2 = actual_tokens_multiple(fr, [snk1, snk2],
                                min(100, len(actuals1[i]) + len(actuals2[i]) + 10))
            actuals1.append(actual1)
            actuals2.append(actual2)
            self.migrate(fr, to, snk1)
            self.migrate(fr, to, snk2)

        print actuals1, actuals2

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals1[-1][:-4], min_length=20)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals2[-1][:-4], min_length=20)

        helpers.destroy_app(d)

    def testRoundRobinPortRemoteMoveMany2(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
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
        self.migrate(self.rt1, self.rt2, snk2)
        actuals1 = [[]]
        actuals2 = [[]]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actual1, actual2 = actual_tokens_multiple([fr, to], [snk1, snk2],
                                min(100, len(actuals1[i]) + len(actuals2[i]) + 10))
            actuals1.append(actual1)
            actuals2.append(actual2)
            self.migrate(fr, to, snk1)
            self.migrate(to, fr, snk2)

        print actuals1, actuals2

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals1[-1][:-4], min_length=20)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals2[-1][:-4], min_length=20)

        helpers.destroy_app(d)

    def testRoundRobinPortRemoteMoveMany3(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
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
        self.migrate(self.rt1, self.rt2, snk1)
        self.migrate(self.rt1, self.rt3, snk2)
        actuals1 = [[]]
        actuals2 = [[]]
        rts = [self.rt2, self.rt3]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actual1, actual2 = actual_tokens_multiple([fr, to], [snk1, snk2],
                                min(100, len(actuals1[i]) + len(actuals2[i]) + 10))
            actuals1.append(actual1)
            actuals2.append(actual2)
            self.migrate(fr, to, snk1)
            self.migrate(to, fr, snk2)

        print actuals1, actuals2

        # Round robin lowest peer id get first token
        start = 1 if snk1_token_id < snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals1[-1][:-4], min_length=20)
        start = 1 if snk1_token_id > snk2_token_id else 2
        self.assert_lists_equal(list(range(start, 200, 2)), actuals2[-1][:-4], min_length=20)

        helpers.destroy_app(d)

    def testRandomPortRemoteMoveMany1(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
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
        rts = [self.rt1, self.rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actual1, actual2 = actual_tokens_multiple(fr, [snk1, snk2],
                                min(100, len(actuals1[i]) + len(actuals2[i]) + 10))
            actuals1.append(actual1)
            actuals2.append(actual2)
            self.migrate(fr, to, snk1)
            self.migrate(fr, to, snk2)

        print actuals1, actuals2

        self.assert_lists_equal(list(range(1, 200)), sorted(actuals1[-1] + actuals2[-1])[:-4], min_length=40)

        helpers.destroy_app(d)

    def testRandomPortRemoteMoveMany2(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
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
        self.migrate(self.rt1, self.rt2, snk2)
        actuals1 = [[]]
        actuals2 = [[]]
        rts = [self.rt1, self.rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actual1, actual2 = actual_tokens_multiple([fr, to], [snk1, snk2],
                                min(100, len(actuals1[i]) + len(actuals2[i]) + 10))
            actuals1.append(actual1)
            actuals2.append(actual2)
            self.migrate(fr, to, snk1)
            self.migrate(to, fr, snk2)

        print actuals1, actuals2

        self.assert_lists_equal(list(range(1, 200)), sorted(actuals1[-1] + actuals2[-1])[:-4], min_length=40)

        helpers.destroy_app(d)

    def testRandomPortRemoteMoveMany3(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
            src    : std.CountTimer(sleep=0.02, start=1, steps=100)
            snk1   : test.Sink(store_tokens=1, quiet=1)
            snk2   : test.Sink(store_tokens=1, quiet=1)
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
        self.migrate(self.rt1, self.rt2, snk1)
        self.migrate(self.rt1, self.rt3, snk2)
        actuals1 = [[]]
        actuals2 = [[]]
        rts = [self.rt2, self.rt3]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actual1, actual2 = actual_tokens_multiple([fr, to], [snk1, snk2],
                                min(100, len(actuals1[i]) + len(actuals2[i]) + 10))
            actuals1.append(actual1)
            actuals2.append(actual2)
            self.migrate(fr, to, snk1)
            self.migrate(to, fr, snk2)

        print actuals1, actuals2

        self.assert_lists_equal(list(range(1, 200)), sorted(actuals1[-1] + actuals2[-1])[:-4], min_length=40)

        helpers.destroy_app(d)

    def testActorPortProperty(self):
        _log.analyze("TESTRUN", "+", {})
        script = """
        component Col() token -> token {
            col : flow.Collect()
            .token > col.token
            col.token > .token
        }
        src1 : std.CountTimer(sleep=0.02, start=1, steps=100)
        src2 : std.CountTimer(sleep=0.02, start=1001, steps=100)
        colcomp : Col()
        snk : test.Sink(store_tokens=1, quiet=1)
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
        rts = [self.rt1, self.rt2]
        for i in range(5):
            to = rts[(i+1)%2]
            fr = rts[i%2]
            actuals.append(wait_for_tokens(fr, snk, i*10))
            self.migrate(fr, to, snk)

        print actuals

        high = [x for x in actuals[-1] if x > 999]
        low = [x for x in actuals[-1] if x < 999]
        self.assert_lists_equal(range(1001,1200), high[:-4], min_length=15)
        self.assert_lists_equal(range(1,200), low[:-4], min_length=15)
        helpers.destroy_app(d)


@pytest.fixture(params=[("rt1", "rt1", "rt1"), ("rt1", "rt2", "rt3"), ("rt1", "rt2", "rt2")])
def rt_order3(request):
    return [globals()[p] for p in request.param]


@pytest.fixture(params=[1, 4])
def nbr_replicas(request):
    return request.param


@pytest.mark.skipif(
    calvinconfig.get().get("testing","proxy_storage") != 1 and 
    calvinconfig.get().get("testing","force_replication") != 1,
    reason="Will fail on some systems with DHT")
@pytest.mark.essential
@pytest.mark.slow
class TestReplication(object):
    def testSimpleReplication(self, rt_order3, nbr_replicas):
        _log.analyze("TESTRUN", "+", {})
        script = r"""
            src   : std.Counter()
            proc  : test.TestProcess(eval_str="data + kwargs[\"base\"]",
                        replicate_str="state.kwargs[\"base\"] = 10000 * state.replication_count",
                        kwargs={"base": 0}, dump=false)
            snk   : test.Sink(store_tokens=1, quiet=1)
            src.integer(routing="random")
            snk.token(routing="collect-unordered")
            src.integer > proc.data
            proc.result > snk.token
        """
        rt1 = rt_order3[0]
        rt2 = rt_order3[1]
        rt3 = rt_order3[2]
        response = helpers.deploy_script(request_handler, "testScript", script, rt1)

        src = response['actor_map']['testScript:src']
        proc = response['actor_map']['testScript:proc']
        snk = response['actor_map']['testScript:snk']

        migrate(rt1, rt2, proc)

        wait_until_nbr(rt1, src, 8)

        proc_rep = []
        for n in range(nbr_replicas):
            result = request_handler.replicate(rt2, proc, dst_id=rt3.id)
            print n, result
            proc_rep.append(result['actor_id'])
        actual1 = request_handler.report(rt1, snk)

        actual2 = wait_for_tokens(rt1, snk, len(actual1) + 100)
        request_handler.report(rt1, src, kwargs={'stopped': True})
        expected = expected_tokens(rt1, src, 'seq')
        actual2 = wait_for_tokens(rt1, snk, len(expected))
        # Token can take either way, but only one of each count value
        actual_mod = sorted([t % 10000 for t in actual2])
        #print expected
        #print actual_mod
        assert_lists_equal(expected, actual_mod, min_length=len(actual1)+100)
        # Check OK distribution of paths
        dist = Counter([t // 10000 for t in actual2])
        print dist
        assert all([dist.values() > 10])
        assert len(dist) == (nbr_replicas + 1)

        #print request_handler.report(rt2, proc, kwargs={'cmd_str': "self.state()"})

        # Make sure none is stalled
        request_handler.report(rt1, src, kwargs={'stopped': False})
        actual3 = wait_for_tokens(rt1, snk, len(expected) + 100)
        dist2 = Counter([t // 10000 for t in actual3])
        print dist2
        assert all([dist[k] < dist2[k] for k in dist.keys()])

        helpers.delete_app(request_handler, rt1, response['application_id'],
                           check_actor_ids=response['actor_map'].values()+ proc_rep)
        # Check all actors and replicas deleted
        actors = set(request_handler.get_actors(rt1) + request_handler.get_actors(rt2) + request_handler.get_actors(rt3))
        assert src not in actors
        assert snk not in actors
        assert proc not in actors
        for p in proc_rep:
            assert p not in actors

    def testSimpleDereplication(self, rt_order3, nbr_replicas):
        _log.analyze("TESTRUN", "+", {})
        script = r"""
            src   : std.Counter()
            proc  : test.TestProcess(eval_str="data + kwargs[\"base\"]",
                        replicate_str="state.kwargs[\"base\"] = 10000 * state.replication_count",
                        kwargs={"base": 0}, dump=false)
            snk   : test.Sink(store_tokens=1, quiet=1, active=true)
            src.integer(routing="random")
            snk.token(routing="collect-unordered")
            src.integer > proc.data
            proc.result > snk.token
        """
        rt1 = rt_order3[0]
        rt2 = rt_order3[1]
        rt3 = rt_order3[2]
        response = helpers.deploy_script(request_handler, "testScript", script, rt1)

        src = response['actor_map']['testScript:src']
        proc = response['actor_map']['testScript:proc']
        snk = response['actor_map']['testScript:snk']

        migrate(rt1, rt2, proc)

        wait_until_nbr(rt1, src, 8)

        proc_rep = []
        for n in range(nbr_replicas):
            result = request_handler.replicate(rt2, proc, dst_id=rt3.id)
            print n, result
            proc_rep.append(result['actor_id'])
        actual1 = request_handler.report(rt1, snk)

        actual2 = wait_for_tokens(rt1, snk, len(actual1) + 100)
        # Pause sink, fill the queues a bit
        request_handler.report(rt1, snk, kwargs={'active': False})
        time.sleep(0.1)

        # Dereplicate
        async_results = []
        proc_derep = []
        for n in range(nbr_replicas):
            async_results.append(request_handler.async_replicate(rt2, proc, dereplicate=True, exhaust=True))
            if n == 0:
                # let the tokens flow again, but no new tokens
                request_handler.report(rt1, snk, kwargs={'active': True})
                request_handler.report(rt1, src, kwargs={'stopped': True})
            # Need to wait for first dereplication to finish before a second, since no simultaneous (de)replications
            proc_derep.append(request_handler.async_response(async_results[-1]))
        print proc_derep
        expected = expected_tokens(rt1, src, 'seq')
        actual2 = wait_for_tokens(rt1, snk, len(expected))

        # Check replicas deleted
        actors = set(request_handler.get_actors(rt1) + request_handler.get_actors(rt2) + request_handler.get_actors(rt3))
        for p in proc_rep:
            assert p not in actors

        # Token can take either way, but only one of each count value
        actual_mod = sorted([t % 10000 for t in actual2])
        #print expected
        #print actual_mod
        assert_lists_equal(expected, actual_mod, min_length=len(actual1)+100)
        # Check OK distribution of paths
        dist = Counter([t // 10000 for t in actual2])
        print dist
        assert all([dist.values() > 10])
        assert len(dist) == (nbr_replicas + 1)

        #print request_handler.report(rt2, proc, kwargs={'cmd_str': "self.state()"})

        helpers.delete_app(request_handler, rt1, response['application_id'],
                           check_actor_ids=response['actor_map'].values()+ proc_rep)
        # Check all actors and replicas deleted
        actors = set(request_handler.get_actors(rt1) + request_handler.get_actors(rt2) + request_handler.get_actors(rt3))
        assert src not in actors
        assert snk not in actors
        assert proc not in actors
        for p in proc_rep:
            assert p not in actors

    def testMultiDereplication(self, rt_order3, nbr_replicas):
        _log.analyze("TESTRUN", "+", {})
        script = r"""
            src   : test.FiniteCounter(start=1)
            proc  : test.TestProcess(eval_str="{data.keys()[0]: data.values()[0] + kwargs[\"base\"]}",
                        replicate_str="state.kwargs[\"base\"] = 10000 * state.replication_count",
                        kwargs={"base": 0}, dump=false)
            snk   : test.Sink(store_tokens=1, quiet=1, active=true)
            src.integer(routing="random")
            proc.data(routing="collect-tagged")
            snk.token(routing="collect-unordered")
            src.integer > proc.data
            proc.result > snk.token
        """
        rt1 = rt_order3[0]
        rt2 = rt_order3[1]
        rt3 = rt_order3[2]
        response = helpers.deploy_script(request_handler, "testScript", script, rt1)

        src = response['actor_map']['testScript:src']
        proc = response['actor_map']['testScript:proc']
        snk = response['actor_map']['testScript:snk']
        meta = request_handler.get_actor(rt1, src)
        src_port = [meta['outports'][0]['id']]

        migrate(rt1, rt2, proc)

        wait_until_nbr(rt1, src, 8)

        # Replicate
        proc_rep = []
        src_rep = []
        for n in range(nbr_replicas):
            # Replicate connected actors simultaneously
            proc_result = request_handler.async_replicate(rt2, proc, dst_id=rt3.id)
            src_result = request_handler.async_replicate(rt1, src)

            # ... but wait for each pair, since not allowed to (de)replicate multiple at the same time
            proc_rep.append(request_handler.async_response(proc_result)['actor_id'])
            src_rep.append(request_handler.async_response(src_result)['actor_id'])
            meta = request_handler.get_actor(rt1, src_rep[-1])
            src_port.append(meta['outports'][0]['id'])
        actual1 = request_handler.report(rt1, snk)

        actual2 = wait_for_tokens(rt1, snk, (nbr_replicas + 1) * len(actual1) + 100)
        # Pause sink, fill the queues a bit
        request_handler.report(rt1, snk, kwargs={'active': False})
        time.sleep(0.1)

        # No new tokens
        request_handler.report(rt1, src, kwargs={'stopped': True})
        for r in src_rep:
            request_handler.report(rt1, r, kwargs={'stopped': True})
        expected = [expected_tokens(rt1, src, 'seq')]
        for r in src_rep:
            expected.append(expected_tokens(rt1, r, 'seq'))

        # Dereplicate
        proc_derep = []
        src_derep = []
        for n in range(nbr_replicas):
            # Dereplicate connected actors simultaneously
            proc_result = request_handler.async_replicate(rt2, proc, dereplicate=True, exhaust=True)
            src_result = request_handler.async_replicate(rt1, src, dereplicate=True, exhaust=True)
            if n == 0:
                # let the tokens flow again in the sink
                request_handler.report(rt1, snk, kwargs={'active': True})
            # ... but wait for each pair, since not allowed to (de)replicate multiple at the same time
            proc_derep.append(request_handler.async_response(proc_result))
            src_derep.append(request_handler.async_response(src_result))
        print proc_derep
        print src_derep

        total_len = sum([len(e) - 1 for e in expected])
        actual2 = wait_for_tokens(rt1, snk, total_len)

        # Check replicas deleted
        actors = set(request_handler.get_actors(rt1) + request_handler.get_actors(rt2) + request_handler.get_actors(rt3))
        for a in proc_rep:
            assert a not in actors
        for a in src_rep:
            assert a not in actors

        # Token can take either way, but only up to nbr_replicas of each count value
        actuals = []
        actuals_rem = []
        actuals_mod = []
        for p in src_port:
            actuals.append([t[p] for t in actual2 if p in t])
            actuals_rem.append(sorted([t % 10000 for t in actuals[-1]]))
            actuals_mod.extend([t // 10000 for t in actuals[-1]])
        for i in range(nbr_replicas + 1):
            #print expected[i]
            #print actuals_rem[i]
            assert_lists_equal(expected[i], actuals_rem[i], min_length=len(expected[i])-1)
        # Check OK distribution of paths
        dist = Counter(actuals_mod)
        print dist
        assert all([dist.values() > 10])
        assert len(dist) == (nbr_replicas + 1)

        helpers.delete_app(request_handler, rt1, response['application_id'],
                           check_actor_ids=response['actor_map'].values()+ proc_rep + src_rep)
        # Check all actors and replicas deleted
        actors = set(request_handler.get_actors(rt1) + request_handler.get_actors(rt2) + request_handler.get_actors(rt3))
        assert src not in actors
        assert snk not in actors
        assert proc not in actors
        for a in proc_rep:
            assert a not in actors
        for a in src_rep:
            assert a not in actors

