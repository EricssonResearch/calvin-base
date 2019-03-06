# -*- coding: utf-8 -*-

# Copyright (c) 2015-2019 Ericsson AB
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


import os

import pytest

from calvin.runtime.north.calvinsys import CalvinSys
from calvin.runtime.north.calvinlib import CalvinLib
from calvin.runtime.north.actormanager import class_factory
from calvinservices.actorstore.store import Pathinfo 

from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port.endpoint import Endpoint
from calvin.runtime.north import scheduler
from calvin.runtime.north.plugins.port import queue
from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)

        
class MockCalvinSys(CalvinSys):

    def init(self, capabilities):
        for key, value in capabilities.items():
            module = value['module']
            value['path'] = module
            value['module'] = None # Why?
            _log.debug("Capability '%s' registered with module '%s'" % (key, module))
        self.capabilities = capabilities
        self.reg_sysobj = {} # FIXME: use set, we check one actor at a time and sys_objects are singletons

    def open(self, capability_name, actor, **kwargs):
        calvinsys = actor.test_calvinsys.get(capability_name, {})
        attr_data = dict({'calvinsys': calvinsys}, **kwargs)
        ref = super(MockCalvinSys, self).open(capability_name, actor, **attr_data)
        if actor not in self.reg_sysobj:
            self.reg_sysobj[actor] = []
        self.reg_sysobj[actor].append(ref)
        # print 'reg_sysobj', self.reg_sysobj
        return ref

    def can_write(self, ref):
        obj = self._get_capability_object(ref)
        data = obj.can_write()
        return data

    def write(self, ref, data):
        obj = self._get_capability_object(ref)
        obj.write(data)

    def can_read(self, ref):
        obj = self._get_capability_object(ref)
        data = obj.can_read()
        return data

    def read(self, ref):
        obj = self._get_capability_object(ref)
        data = obj.read()
        return data

    def read_called(self, actor):
        for ref in self.reg_sysobj.get(actor, []):
            obj = self._get_capability_object(ref)
            try:
                if obj.read_called:
                    return True
            except AttributeError:
                pass
            except Exception as e:
                raise e
        return False

    def write_called(self, actor):
        for ref in self.reg_sysobj.get(actor, []):
            obj = self._get_capability_object(ref)
            try:
                if obj.write_called:
                    return True
            except AttributeError:
                pass
            except Exception as e:
                raise e
        return False

    def verify_read_write_during_init(self, aut, actor_name):
        if self.read_called(aut):
            pytest.fail("Actor: {} calling calvinsys.read() from init().".format(actor_name))
        if self.write_called(aut):
            # FIXME: Mark as XFAIL until we have a generic 'initial_action' strategy
            pytest.xfail("Actor: {} calling calvinsys.write() from init().".format(actor_name))

    def init_done(self, actor_name):
        for ref in self.reg_sysobj.get(actor_name, []):
            obj = self._get_capability_object(ref)
            if obj:
                obj.start_verifying_calvinsys()


class MockCalvinLib(CalvinLib):

    def init(self, capabilities):
        """
        setup capabilities from config
        """
        for key, value in capabilities.items():
            module = value['module']
            value['path'] = module
            value['module'] = None
            _log.debug("Capability '%s' registered with module '%s'" % (key, module))
        self.capabilities = capabilities


@pytest.fixture
def mock_calvinsys():
    """Mock calvinsys instance"""
    cs = MockCalvinSys()
    cs.init(capabilities={
        "io.button": {
            "module": "mock.MockInput",
            "attributes": {"data": [1, 0, 1, 0]}
        },
        "io.digitalin": {
            "module": "mock.MockInput",
            "attributes": {"data": [1, 0, 1, 0]}
        },
        "io.knob": {
            "module": "mock.MockInput",
            "attributes": {"data": [-1, 1, 0, 1]}
        },
        "io.hallswitch": {
            "module": "mock.MockInput",
            "attributes": {"data": [False, True, False, True]}
        },
        "io.switch": {
            "module": "mock.MockInput",
            "attributes": {"data": [0, 1, 0, 1]}
        },
        "io.tiltswitch": {
            "module": "mock.MockInput",
            "attributes": {"data": [1, 0, 1, 0]}
        },
        "io.lightbreaker": {
            "module": "mock.MockInput",
            "attributes": {"data": [False, True, False, True]}
        },
        "io.pickupgesture": {
            "module": "mock.MockInput",
            "attributes": {"data": [False, True, False, True]}
        },
        "io.buzzer": {
            "module": "mock.MockOutput",
            "attributes": {}
        },
        "io.digitalout": {
            "module": "mock.MockOutput",
            "attributes": {}
        },
        "io.light": {
            "module": "mock.MockOutput",
            "attributes": {}
        },
        "io.stdout": {
            "module": "mock.MockOutput",
            "attributes": {}
        },
        "io.pwm": {
            "module": "mock.MockOutput",
            "attributes": {}
        },
        "io.servomotor": {
            "module": "mock.MockOutput",
            "attributes": {}
        },
        "log.info": {
            "module": "mock.MockOutput",
            "attributes": {}
        },
        "log.warning": {
            "module": "mock.MockOutput",
            "attributes": {}
        },
        "log.error": {
            "module": "mock.MockOutput",
            "attributes": {}
        },
        "web.twitter.post": {
            "module": "mock.MockOutput",
            "attributes": {}
        },
        "notify.bell": {
            "module": "mock.MockOutput",
            "attributes": {}
        },
        "image.render": {
            "module": "mock.MockOutput",
            "attributes": {}
        },
        "web.pushbullet.channel.post": {
            "module": "mock.MockOutput",
            "attributes": {}
        },
        "sys.schedule": {
            "module": "mock.MockInputOutput",
            "attributes": {'data': ["dummy"]}
        },
        "sys.timer.once": {
            "module": "mock.MockInputOutput",
            "attributes": {'data': ["dummy"]}
        },
        "sys.timer.repeating": {
            "module": "mock.MockInputOutput",
            "attributes": {'data': ["dummy"]}
        },
        "sys.attribute.public": {
            "module": "mock.MockInputOutput",
            "attributes": {'data': ["dummy"]}
        },
        "sys.attribute.indexed": {
            "module": "mock.MockInputOutput",
            "attributes": {'data': ["dummy"]}
        },
        "image.facedetection": {
            "module": "mock.MockInputOutput",
            "attributes": {'data': ["dummy"]}
        },
        "image.facefinding": {
            "module": "mock.MockInputOutput",
            "attributes": {'data': ["dummy"]}
        },
        "image.source": {
            "module": "mock.MockInputOutput",
            "attributes": {'data': ["dummy"]}
        },
        "image.objectdetection": {
            "module": "mock.MockInputOutput",
            "attributes": {'data': ["dummy"]}
        },
        "image.objectfinding": {
            "module": "mock.MockInputOutput",
            "attributes": {'data': ["dummy"]}
        },
        "io.distance": {
            "module": "mock.MockInputOutput",
            "attributes": {"data": ["dummy"]}
        },
        "io.temperature": {
            "module": "mock.MockInputOutput",
            "attributes": {"data": ["dummy"]}
        },
        "io.pressure": {
            "module": "mock.MockInputOutput",
            "attributes": {"data": ["dummy"]}
        },
        "io.accelerometer": {
            "module": "mock.MockInputOutput",
            "attributes": {"data": ["dummy"]}
        },
        "io.gyroscope": {
            "module": "mock.MockInputOutput",
            "attributes": {"data": ["dummy"]}
        },
        "io.soilmoisture": {
            "module": "mock.MockInputOutput",
            "attributes": {"data": ["dummy"]}
        },
        "io.humidity": {
            "module": "mock.MockInputOutput",
            "attributes": {"data": ["dummy"]}
        },
        "io.stepcounter": {
            "module": "mock.MockInputOutput",
            "attributes": {"data": ["dummy"]}
        },
        "io.filesize": {
            "module": "mock.MockInput",
            "attributes": {"data": [44]}
        },
        "io.filereader": {
            "module": "mock.MockInput",
            "attributes": {"data": ["the quick brown fox jumped over the lazy dog"]}
        },
        "io.filewriter": {
            "module": "mock.MockOutput",
            "attributes": {}
        },
        "io.stdin": {
            "module": "mock.MockInput",
            "attributes": {"data": ["the quick brown fox jumped over the lazy dog"]}
        },
        "weather": {
            "module": "mock.MockInputOutput",
            "attributes": {"data": ["dummy"]}
        },
        "weather.local": {
            "module": "mock.MockInputOutput",
            "attributes": {"data": ["dummy"]}
        }
    })
    return cs


@pytest.fixture
def mock_calvinlib():
    """Mock calvinlib instance"""
    cl = MockCalvinLib()    
    cl.init(capabilities={
        "math.arithmetic.compare": {
            "module": "mathlib.Arithmetic"
        },
        "math.arithmetic.operator": {
            "module": "mathlib.Arithmetic"
        },
        "math.arithmetic.eval": {
            "module": "mathlib.Arithmetic"
        },
        "math.random": {
            "module": "mathlib.Random",
            "attributes": {"seed": 10}
        },
        "math.hash": {
            "module": "hash.Hash",
        },
        "json": {
            "module": "jsonlib.Json"
        },
        "base64": {
            "module": "base64lib.Base64"
        },
        "copy": {
            "module": "datalib.Copy"
        },
        "mustache": {
            "module": "textformatlib.Pystache"
        },
        "time": {
            "module": "timelib.Time"
        },
        "regexp": {
            "module": "regexp.PyRegexp",
        }
    })
    return cl
    
class DummyInEndpoint(Endpoint):

    """
    Dummy in endpoint for actor test
    """

    def __init__(self, port):
        super(DummyInEndpoint, self).__init__(port)

    def is_connected(self):
        return True


class DummyOutEndpoint(Endpoint):

    """
    Dummy out endpoint for actor test
    """

    def __init__(self, port):
        super(DummyOutEndpoint, self).__init__(port)

    def is_connected(self):
        return True

def fwrite(port, value):
    if isinstance(value, Token):
        port.queue.write(value, None)
    else:
        port.queue.write(Token(value=value), None)


def pwrite(actor, portname, value):
    port = actor.inports.get(portname)
    if not port:
        raise Exception("No such port %s" % (portname,))
    try:
        if isinstance(value, (list, tuple)):
            for v in value:
                fwrite(port, v)
        else:
            fwrite(port, value)
    except queue.common.QueueFull:
        # Some tests seems to enter too many tokens but we ignore it
        # TODO make all actors' test compliant and change to raise exception
        pytest.xfail("Queue full")

def pread(actor, portname, number=1):
    port = actor.outports.get(portname, None)
    assert port
    if number > 0:
        if not pavailable(actor, portname, number):
            try:
                # Dig deep into queue, can break at any time
                available = port.queue.write_pos - port.queue.tentative_read_pos[next(iter(port.queue.readers))]
            except:
                available = -9999
            raise AssertionError("Too few tokens available, %d, expected %d" % (available, number))
    else:
        if pavailable(actor, portname, number+1):
            raise AssertionError("Too many tokens available, expected %d" % number)

    values = [port.queue.peek(actor.id).value for _ in range(number)]
    port.queue.commit(actor.id)
    return values


def pavailable(actor, portname, number):
    port = actor.outports.get(portname, None)
    assert port
    return port.queue.tokens_available(number, actor.id)


def run_actor_unittests(aut, actor_type, mock_sys):
    for idx in range(len(aut.test_set)):
        test_index = idx + 1
        test = aut.test_set[idx]
        setups = test.get('setup', [])
        inputs = test.get('inports', {})
        outputs = test.get('outports', {})
        postconds = test.get('postcond', [])

        for f in setups:
            try:
                f(aut)
            except Exception as e:
                __tracebackhide__ = True
                pytest.fail("Actor {} failed during setup of test {}: {}".format(actor_type, test_index, e.message))

        for port, values in inputs.items():
            pwrite(aut, port, values)

        mock_sys.verify_read_write_during_init(aut, actor_type)
        mock_sys.init_done(actor_type)

        sched = scheduler.BaseScheduler(None, None)
        sched._fire_actor(aut)

        for port, expected in outputs.items():
            actual = pread(aut, port, len(expected))
            if type(expected) is set:
                actual = set(actual)
            if actual != expected:
                __tracebackhide__ = True
                pytest.fail("Failed test {}, {}\nActual output '{}' does not match expected '{}'".format(test_index, test, actual, expected))    

        if not all(f(aut) for f in postconds):
            __tracebackhide__ = True
            pytest.fail("Failed post condition of test {}".format(test_index))
    


def actor_list():
    # return ['std.Sum', 'flow.Init']
    dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path = os.path.join(dir_path, "../../../calvinservices/actorstore/systemactors")    
    actors = []
    for dirpath, dirnames, filenames in os.walk(dir_path):
        filenames = [os.path.join(dirpath, f) for f in filenames if f.endswith('.py') and f != '__init__.py']
        for f in filenames:
            basepath, _ = os.path.splitext(f)
            _, ns, name = basepath.rsplit('/', 2)
            actor_type = "{}.{}".format(ns, name)
            actors.append(actor_type)
    return actors


@pytest.mark.parametrize('actor_type', actor_list())
def test_actors(mock_calvinsys, mock_calvinlib, monkeypatch, store, actor_type):
    # Patch the global _calvinsys used by get_calvinsys
    import calvin.runtime.north.calvinsys
    monkeypatch.setattr(calvin.runtime.north.calvinsys, '_calvinsys', mock_calvinsys)    
    import calvin.runtime.north.calvinlib
    monkeypatch.setattr(calvin.runtime.north.calvinlib, '_calvinlib', mock_calvinlib)    
    
    # 1. Load class from store
    info, src, metadata = store.get_info(actor_type)
    assert info is Pathinfo.actor
    actor_class = class_factory(src, metadata, actor_type)

    # 2. Check for unit test information
    if hasattr(actor_class, 'test_args') and actor_class.test_args:
        pytest.fail("Actor unittest argument 'test_args' is deprecated and only 'test_kwargs' should be used")
    kwargs = actor_class.test_kwargs if hasattr(actor_class, 'test_kwargs') else {}  
    test_set = actor_class.test_set if hasattr(actor_class, 'test_set') else []
    if not test_set:
        pytest.skip("No 'test_set' provided for {}".format(actor_type)) 
    
    # 3. Instatiate actor
    actor = actor_class('aut', disable_state_checks=True)
    assert not actor.is_shadow()
    actor.init(**kwargs)
    actor.setup_complete()
    
    # 4. Attach ports
    for inport in actor.inports.values():
        inport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 100, 'direction': "in"}, {}))
        inport.endpoint = DummyInEndpoint(inport)
        inport.queue.add_reader(inport.id, {})
    for outport in actor.outports.values():
        outport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 100, 'direction': "out"}, {}))
        outport.queue.add_reader(actor.id, {})
        outport.endpoints.append(DummyOutEndpoint(outport))
    
    # 5. Run unittests
    run_actor_unittests(actor, actor_type, mock_calvinsys) 
    
    
if __name__ == '__main__':
    print(actor_list())    
