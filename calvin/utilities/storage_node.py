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

from multiprocessing import Process
# For trace
import sys
import trace
import logging


from calvin.runtime.north import scheduler
from calvin.runtime.north import storage
from calvin.runtime.north import calvincontrol
from calvin.runtime.south.plugins.async import async
from calvin.utilities import calvinuuid
from calvin.utilities.calvinlogger import get_logger
_log = get_logger(__name__)


class FakeAM(object):
    def enabled_actors():
        return []


class FakeMonitor(object):
    def loop():
        return False


class StorageNode(object):

    def __init__(self, control_uri):
        super(StorageNode, self).__init__()
        self.id = calvinuuid.uuid("NODE")
        self.control_uri = control_uri
        self.control = calvincontrol.get_calvincontrol()
        _scheduler = scheduler.DebugScheduler if _log.getEffectiveLevel() <= logging.DEBUG else scheduler.Scheduler
        self.sched = _scheduler(self, FakeAM(), FakeMonitor())
        self.control.start(node=self, uri=control_uri)
        self.storage = storage.Storage(self)
        async.DelayedCall(0, self.start)

    #
    # Event loop
    #
    def run(self):
        """main loop on node"""
        _log.debug("Node %s is running" % self.id)
        self.sched.run()

    def start(self):
        """ Run once when main loop is started """
        self.storage.start()

    def stop(self, callback=None):
        def stopped(*args):
            _log.analyze(self.id, "+", {'args': args})
            self.sched.stop()
            self.control.stop()

        _log.analyze(self.id, "+", {})
        self.storage.stop(stopped)


def create_node(uri, control_uri, attributes=None):
    n = StorageNode(control_uri)
    n.run()
    _log.info('Quitting node "%s"' % n.control_uri)


def create_tracing_node(uri, control_uri, attributes=None):
    """
    Same as create_node, but will trace every line of execution.
    Creates trace dump in output file '<host>_<port>.trace'
    """
    n = StorageNode(control_uri)
    _, host = uri.split('://')
    with open("%s.trace" % (host, ), "w") as f:
        tmp = sys.stdout
        # Modules to ignore
        ignore = [
            'fifo', 'calvin', 'actor', 'pickle', 'socket',
            'uuid', 'codecs', 'copy_reg', 'string_escape', '__init__',
            'colorlog', 'posixpath', 'glob', 'genericpath', 'base',
            'sre_parse', 'sre_compile', 'fdesc', 'posixbase', 'escape_codes',
            'fnmatch', 'urlparse', 're', 'stat', 'six'
        ]
        with f as sys.stdout:
            tracer = trace.Trace(trace=1, count=0, ignoremods=ignore)
            tracer.runfunc(n.run)
        sys.stdout = tmp
    _log.info('Quitting node "%s"' % n.control_uri)


def start_node(uri, control_uri, trace_exec=False, attributes=None):
    """ Start storage only node, keeps same param list as full node, but
        uses only the control_uri
    """
    _create_node = create_tracing_node if trace_exec else create_node
    p = Process(target=_create_node, args=(uri, control_uri, attributes))
    p.daemon = True
    p.start()
    return p
