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
from calvin.actorstore.store import ActorStore
from calvin.runtime.north.calvin_token import Token
from calvin.runtime.south.endpoint import Endpoint
from calvin.runtime.north import metering


def fwrite(port, value):
    if isinstance(value, Token):
        port.fifo.write(value)
    else:
        port.fifo.write(Token(value=value))


def pwrite(actor, portname, value):
    port = actor.inports.get(portname)
    if not port:
        raise Exception("No such port %s" % (portname,))
    if isinstance(value, list):
        for v in value:
            fwrite(port, v)
    else:
        fwrite(port, value)


def pread(actor, portname, number=1):
    port = actor.outports.get(portname, None)
    assert port
    if number > 0:
        if pavailable(actor, portname) < number:
            raise AssertionError("Too few tokens available, %d, expected %d" % (pavailable(actor, portname), number))
    else:
        if pavailable(actor, portname) > number:
            raise AssertionError("Too many tokens available, %d, expected %d" % (pavailable(actor, portname), number))

    values = [port.fifo.read(actor.id).value for _ in range(number)]
    port.fifo.commit_reads(actor.id), True
    return values


def pavailable(actor, portname):
    port = actor.outports.get(portname, None)
    assert port
    return port.fifo.available_tokens(actor.id)


class DummyInEndpoint(Endpoint):

    """
    Dummy in endpoint for actor test
    """

    def __init__(self, port):
        super(DummyInEndpoint, self).__init__(port)

    def is_connected(self):
        return True

    def read_token(self):
        token = self.port.fifo.read(self.port.id)
        if token:
            self.port.fifo.commit_reads(self.port.id, True)
        return token

    def available_tokens(self):
        tokens = 0
        tokens += self.port.fifo.available_tokens(self.port.id)
        return tokens

    def peek_token(self):
        return self.port.fifo.read(self.port.id)

    def commit_peek_as_read(self):
        self.port.fifo.commit_reads(self.port.id)

    def peek_rewind(self):
        self.port.fifo.rollback_reads(self.port.id)


class FDMock(object):
    def __init__(self, fname, mode):
        self.fp = open(fname, mode)
        if 'r' in mode:
            self.buffer = self.fp.read()
        else:
            self.buffer = ""

    def close(self):
        self.fp.close()

    def eof(self):
        return len(self.buffer) == 0

    def has_data(self):
        return len(self.buffer) > 0

    def read(self):
        data = self.buffer
        self.buffer = ""
        return data

    def write(self, data):
        self.buffer += data
        self.fp.write(data)

    def read_line(self):
        if '\n' in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
        else:
            line = self.buffer
            self.buffer = ""
        return line

    def write_line(self, data):
        self.buffer += data + "\n"
        self.fp.write(data + "\n")


class StdInMock(FDMock):
    def __init__(self):
        self.buffer = "stdin\nstdin_second_line"


class TimerMock(object):

    def __init__(self):
        self._triggered = False

    @property
    def triggered(self):
        return self._triggered

    def ack(self):
        assert self._triggered
        self._triggered = False

    def cancel(self):
        del self._triggered

    def trigger(self):
        assert not self._triggered
        self._triggered = True


class CalvinSysTimerMock(object):
    def repeat(self, delay):
        return TimerMock()

    def once(self, delay):
        return TimerMock()


class CalvinSysFileMock(object):
    def open(self, fname, mode):
        return FDMock(fname, mode)

    def open_stdin(self):
        return StdInMock()

    def close(self, fdmock):
        fdmock.close()


def load_python_requirement(req):
    import importlib
    loaded = importlib.import_module("calvin.calvinsys.native." + req)
    return loaded.register

requirements = \
    {
        'calvinsys.io.filehandler': CalvinSysFileMock,
        'calvinsys.events.timer': CalvinSysTimerMock,
        'calvinsys.native.python-os-path': load_python_requirement('python-os-path'),
        'calvinsys.native.python-re': load_python_requirement('python-re'),
        'calvinsys.native.python-json': load_python_requirement('python-json'),
        'calvinsys.native.python-copy': load_python_requirement('python-copy'),
        'calvinsys.native.python-base64': load_python_requirement('python-base64')

    }


class CalvinSysMock(dict):
    def use_requirement(self, actor, requirement):
        return requirements[requirement]()


class ActorTester(object):

    def __init__(self):
        self.store = ActorStore()
        self.actors = {}
        self.illegal_actors = {}
        self.components = {}
        self.id = "ActorTester"
        self.metering = metering.set_metering(metering.Metering(self))

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
                return
            actor._calvinsys = CalvinSysMock()
            actor._calvinsys['file'] = CalvinSysFileMock()
            actor._calvinsys['timer'] = CalvinSysTimerMock()
            actor.init(*actorclass.test_args, **actorclass.test_kwargs)
            actor.setup_complete()
        except Exception as e:
            self.illegal_actors[actorname] = "Failed to instantiate"
            sys.stderr.write("Actor %s: %s" % (actorname, e))
            import traceback
            sys.stderr.write(''.join(traceback.format_exc()))
            raise e

        for inport in actor.inports.values():
            inport.endpoint = DummyInEndpoint(inport)
        for outport in actor.outports.values():
            outport.fifo.add_reader(actor.id)

        self.actors[actorname] = actor

    def instantiate_actors(self):
        for a in self.actor_names:
            found, primitive, actorclass = self.store.lookup(a)
            if found and primitive:
                self.instantiate_actor(actorclass, a)
            elif found and not primitive:
                self.components[a] = "TODO: Cannot test components (%s)" % (a,)
            else:
                self.illegal_actors[a] = "Unknown actor - probably parsing issues"

    def load_actor(self, path):
        actorclass = self.store.load_from_path(path)
        if actorclass:
            self.instantiate_actor(actorclass, path)
        else:
            self.illegal_actors[path] = "Unknown actor - probably parsing issues"

    def test_actor(self, actor, aut):
        for idx in range(len(aut.test_set)):
            test_index = idx + 1
            test = aut.test_set[idx]

            setups = test.get('setup', [])
            inputs = test.get('in', {})
            outputs = test.get('out', {})
            postconds = test.get('postcond', [])

            for f in setups:
                try:
                    f(aut)
                except Exception as e:
                    print "Actor %s failed during setup of test %d: %s" % (actor, test_index, e.message)
                    raise Exception("Failed during setup of test %d" % (test_index, ))

            for port, values in inputs.iteritems():
                pwrite(aut, port, values)

            aut.fire()

            for port, values in outputs.iteritems():
                try:
                    vals = pread(aut, port, len(values))
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
                # raise e
            except Exception as e:
                self.illegal_actors[actor] = str(e)

        return {'pass': test_pass, 'fail': test_fail, 'skipped': no_test,
                'errors': self.illegal_actors, 'components': self.components}


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
        t.load_actor(path)
    else:
        t.collect_actors(actor)
        t.instantiate_actors()
    results = t.test_actors()

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
