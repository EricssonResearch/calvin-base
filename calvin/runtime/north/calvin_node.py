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

from calvin.runtime.north import actormanager
from calvin.runtime.north import appmanager
from calvin.runtime.north import scheduler
from calvin.runtime.north import storage
from calvin.runtime.north import calvincontrol
from calvin.runtime.north.calvin_network import CalvinNetwork
from calvin.runtime.north.calvin_proto import CalvinProto
from calvin.runtime.north.portmanager import PortManager
from calvin.runtime.south.monitor import Event_Monitor
from calvin.runtime.south.plugins.async import async

from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities import calvinuuid
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class Node(object):

    """A node of calvin
       the uri is used as server connection point
       the control_uri is the local console
       attributes is a supplied list of external defined attributes that will be used as the key when storing index
       such as name of node
    """

    def __init__(self, uri, control_uri, attributes=None):
        super(Node, self).__init__()
        self.uri = uri
        self.control_uri = control_uri
        self.attributes = attributes
        self.id = calvinuuid.uuid("NODE")
        _log.debug("Calvin init 1")
        self.monitor = Event_Monitor()
        _log.debug("Calvin init 2")
        self.am = actormanager.ActorManager(self)
        _log.debug("Calvin init 3")
        self.control = calvincontrol.get_calvincontrol()
        _log.debug("Calvin init 4")
        self.sched = scheduler.Scheduler(self, self.am, self.monitor)
        _log.debug("Calvin init 5")
        self.control.start(node=self, uri=control_uri)
        self.async_msg_ids = {}
        _log.debug("Calvin init 6")
        self.storage = storage.Storage()
        self.storage.start()
        _log.debug("Calvin init 7")
        self.network = CalvinNetwork(self)
        _log.debug("Calvin init 8")
        self.proto = CalvinProto(self, self.network)
        self.pm = PortManager(self, self.proto)
        _log.debug("Calvin init 9")
        self.app_manager = appmanager.AppManager(self)
        _log.debug("Calvin init 10")
        # The initialization that requires the main loop operating is deferred to start function
        async.DelayedCall(0, self.start)
        _log.debug("Calvin init 11")

    def insert_local_reply(self):
        msg_id = calvinuuid.uuid("LMSG")
        self.async_msg_ids[msg_id] = None
        return msg_id

    def set_local_reply(self, msg_id, reply):
        if msg_id in self.async_msg_ids:
            self.async_msg_ids[msg_id] = reply

    def connect(self, actor_id=None, port_name=None, port_dir=None, port_id=None,
                peer_node_id=None, peer_actor_id=None, peer_port_name=None,
                peer_port_dir=None, peer_port_id=None):
        # FIXME callback needed to send back a proper reply !!!!!
        self.pm.connect(actor_id=actor_id,
                        port_name=port_name,
                        port_dir=port_dir,
                        port_id=port_id,
                        peer_node_id=peer_node_id,
                        peer_actor_id=peer_actor_id,
                        peer_port_name=peer_port_name,
                        peer_port_dir=peer_port_dir,
                        peer_port_id=peer_port_id,
                        callback=CalvinCB(self.logging_callback, preamble="connect cb"))

    def disconnect(self, actor_id=None, port_name=None, port_dir=None, port_id=None):
        # FIXME callback needed to send back a proper reply !!!!!
        _log.debug("disconnect(actor_id=%s, port_name=%s, port_dir=%s, port_id=%s)" %
                   (actor_id if actor_id else "", port_name if port_name else "",
                    port_dir if port_dir else "", port_id if port_id else ""))
        self.pm.disconnect(actor_id=actor_id, port_name=port_name,
                           port_dir=port_dir, port_id=port_id,
                           callback=CalvinCB(self.logging_callback, preamble="disconnect cb"))

    def peersetup(self, peers):
        """ Sets up a RT to RT communication channel, only needed if the peer can't be found in storage.
            peers: a list of peer uris, e.g. ["calvinip://127.0.0.1:5001"]
        """
        # FIXME callback needed to send back a proper reply !!!!!
        _log.debug("peersetup(%s)" % (peers))
        self.network.join(peers, callback=CalvinCB(self.logging_callback, preamble="peersetup cb"))

    def logging_callback(self, preamble=None, *args, **kwargs):
        _log.debug("\n%s# NODE: %s \n# %s %s %s \n%s" %
                   ('#' * 40, self.id, preamble if preamble else "*", args, kwargs, '#' * 40))

    def new(self, actor_type, args, deploy_args=None, state=None, prev_connections=None, connection_list=None):
        actor_id = self.am.new(actor_type, args, state, prev_connections, connection_list)
        if deploy_args:
            app_id = deploy_args['app_id']
            if 'app_name' not in deploy_args:
                app_name = app_id
            else:
                app_name = deploy_args['app_name']
            self.app_manager.add(app_id, app_name, actor_id)
        return actor_id

    #
    # Event loop
    #
    def run(self):
        """main loop on node"""
        _log.debug("Node %s is running" % self.id)
        self.sched.run()

    def start(self):
        """ Run once when main loop is started """
        # FIXME hardcoded which transport and encoder plugin we use, should be based on
        self.network.register(['calvinip'], ['json'])
        self.network.start_listeners([self.uri])
        self.storage.add_node(self)

    def stop(self, callback=None):
        def stopped(*args):
            _log.debug(args)
            self.sched.stop()
            self.control.stop()
        def deleted_node(*args, **kwargs):
            self.storage.stop(stopped)
        self.storage.delete_node(self, cb=deleted_node)


def create_node(uri, control_uri, trace_exec=False, attributes=None):
    _log.debug("create_node")
    n = Node(uri, control_uri, attributes)
    _log.debug("create_node 2")
    if trace_exec:
        _, host = uri.split('://')
        # Trace execution and dump in output file "<host>_<port>.trace"
        with open("%s.trace" % (host, ), "w") as f:
            tmp = sys.stdout
            # Modules to ignore
            modlist = ['fifo', 'calvin', 'actor', 'pickle', 'socket',
                       'uuid', 'codecs', 'copy_reg', 'string_escape', '__init__']
            with f as sys.stdout:
                tracer = trace.Trace(trace=1, count=0, ignoremods=modlist)
                tracer.runfunc(n.run)
            sys.stdout = tmp
    else:
        n.run()
        _log.info('Quitting node "%s"' % n.uri)


def start_node(uri, control_uri, trace_exec=False, attributes=None):
    p = Process(target=create_node, args=(uri, control_uri, trace_exec, attributes))
    p.start()
