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

import pytest
import sys
import argparse
import traceback
from calvin.actorstore.store import ActorStore
from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port.endpoint import Endpoint
from calvin.runtime.north import scheduler
from calvin.runtime.north.plugins.port import queue
from calvin.utilities import calvinlogger
from calvin.runtime.north.calvinsys import CalvinSys

_log = calvinlogger.get_logger(__name__)


class MockCalvinSys(CalvinSys):

    def init(self, capabilities):
        for key, value in capabilities.iteritems():
            module = value['module']
            value['path'] = module
            value['module'] = None
            _log.info("Capability '%s' registered with module '%s'" % (key, module))
        self.capabilities = capabilities
        self.reg_sysobj = {}

    def open(self, capability_name, actor, **kwargs):
        calvinsys = actor.test_calvinsys.get(capability_name, {})
        attr_data = dict({'calvinsys': calvinsys}, **kwargs)
        ref = super(MockCalvinSys, self).open(capability_name, actor, **attr_data)
        if actor not in self.reg_sysobj:
            self.reg_sysobj[actor] = []
        self.reg_sysobj[actor].append(ref)
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
            _log.error("Actor: %s calling calvinsys.read() from init()." % (actor_name))
        if self.write_called(aut):
            _log.error("Actor: %s calling calvinsys.write() from init()." % (actor_name))

    def init_done(self, actor_name):
        for ref in self.reg_sysobj.get(actor_name, []):
            obj = self._get_capability_object(ref)
            if obj:
                obj.start_verifying_calvinsys()

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
        if isinstance(value, list):
            for v in value:
                fwrite(port, v)
        else:
            fwrite(port, value)
    except queue.common.QueueFull:
        # Some tests seems to enter too many tokens but we ignore it
        # TODO make all actors' test compliant and change to raise exception
        pass

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

def setup_calvinlib():
    import calvin.runtime.north.calvinlib as calvinlib
    calvinlib.TESTING=True
    from calvin.runtime.north.calvinlib import get_calvinlib
    lib = get_calvinlib()
    lib.init(capabilities={
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


def setup_calvinsys():
    import calvin.runtime.north.calvinsys as calvinsys
    calvinsys.TESTING = True
    from calvin.runtime.north.calvinsys import get_calvinsys
    sys = get_calvinsys()
    sys.init(capabilities={
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
    return sys


def teardown_calvinlib():
    import calvin.runtime.north.calvinlib as calvinlib
    calvinlib.TESTING=False
    del calvinlib._calvinlib
    calvinlib._calvinlib=None


def teardown_calvinsys():
    import calvin.runtime.north.calvinsys as calvinsys
    calvinsys.TESTING = False
    del calvinsys._calvinsys
    calvinsys._calvinsys = None


class ActorTester(object):

    def __init__(self):
        self.store = ActorStore()
        self.actors = {}
        self.illegal_actors = {}
        self.components = {}
        self.id = "ActorTester"
        setup_calvinlib()
        self.test_sys = setup_calvinsys()

    def collect_actors(self, actor):
        actors = [m + '.' + a for m in self.store.modules() for a in self.store.actors(m)]

        if actor:
            actors = [a for a in actors if actor in a]

        self.actor_names = actors

    def instantiate_actor(self, actorclass, actorname):
        try:
            actor = actorclass(actorname, disable_state_checks=True)
            if not hasattr(actor, 'test_set'):
                self.actors[actorname] = 'no_test'
                _log.warning("%s not tested, no test_set defined." % actorname)
                return

            actor.init(*actorclass.test_args, **actorclass.test_kwargs)
            actor.setup_complete()
        except AssertionError as e:
            raise e
        except Exception as e:
            self.illegal_actors[actorname] = "Failed to instantiate"
            sys.stderr.write("Actor %s: %s" % (actorname, e))
            sys.stderr.write(''.join(traceback.format_exc()))
            raise e

        for inport in actor.inports.values():
            inport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 100, 'direction': "in"}, {}))
            inport.endpoint = DummyInEndpoint(inport)
            inport.queue.add_reader(inport.id, {})
        for outport in actor.outports.values():
            outport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 100, 'direction': "out"}, {}))
            outport.queue.add_reader(actor.id, {})
            outport.endpoints.append(DummyOutEndpoint(outport))

        self.actors[actorname] = actor

    def instantiate_actors(self):
        test_fail = {}
        for a in self.actor_names:
            found, primitive, actorclass, signer = self.store.lookup(a)
            if found and primitive:
                try:
                    self.instantiate_actor(actorclass, a)
                except AssertionError as e:
                    test_fail[a] = e.message
                except Exception as e:
                    raise e
            elif found and not primitive:
                self.components[a] = "TODO: Cannot test components (%s)" % (a,)
            else:
                self.illegal_actors[a] = "Unknown actor - probably parsing issues"

        return test_fail

    def load_actor(self, path):
        test_fail = {}
        actorclass, _ = self.store.load_from_path(path)
        if actorclass:
            try:
                self.instantiate_actor(actorclass, path)
            except AssertionError as e:
                test_fail[path] = e.message
            except Exception as e:
                raise e
        else:
            self.illegal_actors[path] = "Unknown actor - probably parsing issues"
        return test_fail

    def test_actor(self, actor, aut):
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
                    print "Actor %s failed during setup of test %d: %s" % (actor, test_index, e.message)
                    raise Exception("Failed during setup of test %d" % (test_index, ))

            for port, values in inputs.iteritems():
                pwrite(aut, port, values)

            self.test_sys.verify_read_write_during_init(aut, actor)
            self.test_sys.init_done(actor)

            sched = scheduler.BaseScheduler(None, None)
            sched._fire_actor(aut)

            for port, values in outputs.iteritems():
                try:
                    vals = pread(aut, port, len(values))
                    if type(values) is set:
                        # disregard order
                        assert set(vals) == values, "Expected output set '%s' does not match '%s'" % (set(vals), values)
                    else:
                        assert vals == values, "Expected output '%s' does not match '%s'" % (vals, values)
                except AssertionError as e:
                    print "Error:", str(e)
                    raise AssertionError("Failed test %d" % (test_index,))

            if not all(f(aut) for f in postconds):
                raise AssertionError("Failed post condition of test %d" % (test_index, ))

        return True

    def test_actors(self):
        test_pass = []
        test_fail = {}
        no_test = []

        for actor in self.actors:
            aut = self.actors[actor]
            if aut == "no_test":
                no_test.append(actor)
                continue
            try:
                self.test_actor(actor, aut)
                test_pass.append(actor)
            except AssertionError as e:
                test_fail[actor] = e.message
            except Exception as e:
                self.illegal_actors[actor] = str(e) + '\n' + ''.join(
                    traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))

        return {'pass': test_pass, 'fail': test_fail, 'skipped': no_test,
                'errors': self.illegal_actors, 'components': self.components}

def merge_results(result1, result2):
  result = {}
  for k in result1.keys():
    x = result1[k]
    if type(x) is list:
      x.extend(result2[k])
    else:
      x.update(result2[k])
    result[k] = x
  return result


def show_result(header, result):
    print header
    for actor in result:
        print "  %s" % (actor, )


def show_issue(header, result):
    print header
    for actor, reason in result.iteritems():
        print "  %s: %s" % (actor, reason)


def show_issues(results):
    if results['errors']:
        show_issue("Actors with errors", results['errors'])
    if results['fail']:
        show_issue("Failed actor tests", results['fail'])


def show_results(results):
    if results['pass']:
        show_result("Passed tests", results['pass'])
    if results['skipped']:
        show_result("Skipped tests", results['skipped'])
    if results['components']:
        show_issue("Components", results['components'])
    show_issues(results)


@pytest.mark.essential
def test_actors(actor="", show=False, path=None):
    t = ActorTester()
    if path:
        failures = t.load_actor(path)
    else:
        t.collect_actors(actor)
        failures = t.instantiate_actors()
    results = t.test_actors()
    for actor, error in failures.iteritems():
        # Could be updated to support a list of errors, only one at a time for now.
        results['fail'][actor] = error

    if not any(results.values()):
        if actor:
            print "No actors matching '%s' found" % (actor,)
        else:
            raise Exception("No actors found")

    if show:
        return results

    if results['fail'] or results['errors']:
        show_issues(results)

    if results['errors']:
        raise Exception("%d actor(s) had errors" % (len(results['errors']), ))
    if results['fail']:
        raise Exception("%d actor(s) failed tests" % (len(results['fail']),))

    teardown_calvinlib()
    teardown_calvinsys()


if __name__ == '__main__':

    argparser = argparse.ArgumentParser(description="Run actor unittests")
    group = argparser.add_mutually_exclusive_group()
    group.add_argument('--path', '-p', type=str,
                       help='path to actor to test')
    group.add_argument('filter', type=str, nargs='?',
                       help='test actors matching filter')
    args = argparser.parse_args()

    if args.path:
        show_results(test_actors(path=args.path, show=True))
    elif args.filter:
        show_results(test_actors(actor=args.filter, show=True))
    else:
        show_results(test_actors(show=True))
