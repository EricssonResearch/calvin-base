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
import os
import trace
import logging

from calvin.calvinsys import Sys as CalvinSys
from calvin.runtime.north.calvinsys import get_calvinsys
from calvin.runtime.north.calvinlib import get_calvinlib

import calvin.runtime.south.plugins.ui.uicalvinsys
from calvin.runtime.north import actormanager
from calvin.runtime.north import replicationmanager
from calvin.runtime.north import appmanager
from calvin.runtime.north import scheduler
from calvin.runtime.north import storage
from calvin.runtime.north import calvincontrol
from calvin.runtime.north.certificate_authority import certificate_authority
from calvin.runtime.north.authentication import authentication
from calvin.runtime.north.authorization import authorization
from calvin.runtime.north.calvin_network import CalvinNetwork
from calvin.runtime.north.calvin_proto import CalvinProto
from calvin.runtime.north.portmanager import PortManager
from calvin.runtime.south.plugins.async import async
from calvin.utilities.attribute_resolver import AttributeResolver
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.security import security_modules_check
from calvin.utilities.runtime_credentials import RuntimeCredentials
from calvin.utilities import calvinuuid
from calvin.utilities import certificate
from calvin.utilities.calvinlogger import get_logger, set_file
from calvin.utilities import calvinconfig
from calvin.runtime.north.resource_monitor.cpu import CpuMonitor
from calvin.runtime.north.resource_monitor.memory import MemMonitor
from calvin.runtime.north.proxyhandler import ProxyHandler

_log = get_logger(__name__)
_conf = calvinconfig.get()


def addr_from_uri(uri):
    _, host = uri.split("://")
    addr, _ = host.split(":")
    return addr


class Node(object):

    """A node of calvin
       the uri is a list of server connection points
       the control_uri is the local console
       attributes is a supplied list of external defined attributes that will be used as the key when storing index
       such as name of node
    """

    def __init__(self, uris, control_uri, attributes=None):
        super(Node, self).__init__()
        self.quitting = False

        # Warn if its not a uri
        if not isinstance(uris, list):
            _log.error("Calvin uris must be a list %s" % uris)
            raise TypeError("Calvin uris must be a list!")

        # Uris
        self.uris = uris
        if attributes:
            ext_uris = attributes.pop('external_uri', None)
        if ext_uris is not None:
            self.uris += ext_uris

        # Control uri
        self.control_uri = control_uri
        self.external_control_uri = attributes.pop('external_control_uri', self.control_uri) \
            if attributes else self.control_uri

        try:
            self.attributes = AttributeResolver(attributes)
        except:
            _log.exception("Attributes not correct, uses empty attribute!")
            self.attributes = AttributeResolver(None)
        self.node_name = self.attributes.get_node_name_as_str()
        # Obtain node id, when using security also handle runtime certificate
        try:
            security_dir = _conf.get("security", "security_dir")
            self.runtime_credentials = RuntimeCredentials(self.node_name, node=self, security_dir=security_dir)
            self.id = self.runtime_credentials.get_node_id()
        except Exception as err:
            _log.debug("No runtime credentials, err={}".format(err))
            self.runtime_credentials = None
            self.id = calvinuuid.uuid("Node")
        self.certificate_authority = certificate_authority.CertificateAuthority(self)
        self.authentication = authentication.Authentication(self)
        self.authorization = authorization.Authorization(self)
        self.am = actormanager.ActorManager(self)
        self.rm = replicationmanager.ReplicationManager(self)
        self.control = calvincontrol.get_calvincontrol()

        # _scheduler = scheduler.DebugScheduler if _log.getEffectiveLevel() <= logging.DEBUG else scheduler.Scheduler
        # _scheduler = scheduler.NonPreemptiveScheduler
        # _scheduler = scheduler.RoundRobinScheduler
        _scheduler = scheduler.SimpleScheduler
        # _scheduler = scheduler.BaselineScheduler
        self.sched = _scheduler(self, self.am)
        self.async_msg_ids = {}
        self._calvinsys = CalvinSys(self)
        calvinsys = get_calvinsys()
        calvinsys.init(self)
        calvinlib = get_calvinlib()
        calvinlib.init()

        # Default will multicast and listen on all interfaces
        # TODO: be able to specify the interfaces
        # @TODO: Store capabilities
        self.storage = storage.Storage(self)

        self.network = CalvinNetwork(self)
        self.proto = CalvinProto(self, self.network)
        self.pm = PortManager(self, self.proto)
        self.app_manager = appmanager.AppManager(self)

        self.cpu_monitor = CpuMonitor(self.id, self.storage)
        self.mem_monitor = MemMonitor(self.id, self.storage)

        self.proxy_handler = ProxyHandler(self)

        # The initialization that requires the main loop operating is deferred to start function
        async.DelayedCall(0, self.start)

    def insert_local_reply(self):
        msg_id = calvinuuid.uuid("LMSG")
        self.async_msg_ids[msg_id] = None
        return msg_id

    def set_local_reply(self, msg_id, reply):
        if msg_id in self.async_msg_ids:
            self.async_msg_ids[msg_id] = reply

    def connect(self, actor_id=None, port_name=None, port_dir=None, port_properties=None, port_id=None,
                peer_node_id=None, peer_actor_id=None, peer_port_name=None,
                peer_port_dir=None, peer_port_properties=None, peer_port_id=None, cb=None):
        if port_properties is None and port_dir is not None:
            port_properties = {'direction': port_dir}
        if peer_port_properties is None and peer_port_dir is not None:
            peer_port_properties = {'direction': peer_port_dir}
        self.pm.connect(actor_id=actor_id,
                        port_name=port_name,
                        port_properties=port_properties,
                        port_id=port_id,
                        peer_node_id=peer_node_id,
                        peer_actor_id=peer_actor_id,
                        peer_port_name=peer_port_name,
                        peer_port_properties=peer_port_properties,
                        peer_port_id=peer_port_id,
                        callback=CalvinCB(self.logging_callback, preamble="connect cb")  if cb is None else cb)

    def peersetup(self, peers, cb=None):
        """ Sets up a RT to RT communication channel, only needed if the peer can't be found in storage.
            peers: a list of peer uris, e.g. ["calvinip://127.0.0.1:5001"]
        """
        _log.debug("peersetup(%s)" % (peers))
        peers_copy = peers[:]
        peer_node_ids = {}
        if not cb:
            callback = CalvinCB(self.logging_callback, preamble="peersetup cb")
        else:
            callback = CalvinCB(self.peersetup_collect_cb, peers=peers_copy, peer_node_ids=peer_node_ids, org_cb=cb)

        self.network.join(peers, callback=callback)

    def peersetup_collect_cb(self, status, uri, peer_node_id, peer_node_ids, peers, org_cb):
        if uri in peers:
            peers.remove(uri)
            peer_node_ids[uri] = (peer_node_id, status)
        if not peers:
            # Get highest status, i.e. any error
            comb_status = max([s for _, s in peer_node_ids.values()])
            org_cb(peer_node_ids=peer_node_ids, status=comb_status)

    def logging_callback(self, preamble=None, *args, **kwargs):
        _log.debug("\n%s# NODE: %s \n# %s %s %s \n%s" %
                   ('#' * 40, self.id, preamble if preamble else "*", args, kwargs, '#' * 40))

    def new(self, actor_type, args, deploy_args=None, state=None, prev_connections=None, connection_list=None, security=None, access_decision=None):
        # TODO requirements should be input to am.new
        # TODO: make it possible to use security/credentials here.
        actor_def, signer = self.am.lookup_and_verify(actor_type)
        actor_id = self.am.new(actor_type, args, state, prev_connections, connection_list,
                               signature=deploy_args['signature'] if deploy_args and 'signature' in deploy_args else None,
                               actor_def=actor_def,
                               security=security,
                               access_decision=access_decision)
        if deploy_args:
            app_id = deploy_args['app_id']
            if 'app_name' not in deploy_args:
                app_name = app_id
            else:
                app_name = deploy_args['app_name']
            self.app_manager.add(app_id, actor_id,
                                 deploy_info = deploy_args['deploy_info'] if 'deploy_info' in deploy_args else None)
        return actor_id

    def calvinsys(self):
        """Return a CalvinSys instance"""
        # FIXME: We still need to sort out actor requirements vs. node capabilities and user permissions.
        # @TODO: Write node capabilities to storage
        return self._calvinsys

    #
    # Event loop
    #
    def run(self):
        """main loop on node"""
        _log.debug("Node %s is running" % self.id)
        self.sched.run()

    def start(self):
        """ Run once when main loop is started """
        interfaces = _conf.get(None, 'transports')
        self.network.register(interfaces, ['json'])
        self.network.start_listeners(self.uris)
        # Start storage after network, proto etc since storage proxy expects them
        self.storage.start(cb=CalvinCB(self._storage_started_cb))
        self.storage.add_node(self)

        # Start control API
        proxy_control_uri = _conf.get(None, 'control_proxy')
        _log.debug("Start control API on %s with uri: %s and proxy: %s" % (self.id, self.control_uri, proxy_control_uri))
        if proxy_control_uri is not None:
            self.control.start(node=self, uri=proxy_control_uri, tunnel=True)
        else:
            if self.control_uri is not None:
                self.control.start(node=self, uri=self.control_uri, external_uri=self.external_control_uri)

    def stop(self, callback=None):
        # TODO: Handle blocking in poorly implemented calvinsys/runtime south.
        self.quitting = True
        def stopped(*args):
            _log.analyze(self.id, "+", {'args': args})
            _log.debug(args)
            self.sched.stop()
            _log.analyze(self.id, "+ SCHED STOPPED", {'args': args})
            self.control.stop()
            _log.analyze(self.id, "+ CONTROL STOPPED", {'args': args})

        def deleted_node(*args, **kwargs):
            _log.analyze(self.id, "+", {'args': args, 'kwargs': kwargs})
            self.storage.stop(stopped)

        _log.analyze(self.id, "+", {})
        self.storage.delete_node(self, cb=deleted_node)
        self.cpu_monitor.stop()
        self.mem_monitor.stop()
        for link in self.network.list_direct_links():
            self.network.link_get(link).close()

    def stop_with_cleanup(self):
        # Set timeout in case some actor is refusing to stop (or leave if already migrating)
        timeout = async.DelayedCall(50, self.stop)
        self.quitting = True
        # get all actors
        if not self.am.actors:
            # No actors, we're basically done
            return self.stop()
        actors = []
        for actor in self.am.actors.values():
            # Do not delete migrating actors (for now)
            if actor._migrating_to is None:
                actors.append(actor)
        # delete all actors
        for actor in actors:
            self.am.destroy(actor.id)
        # and die - hopefully, things should clean up nicely within reasonable time

        def poll_deleted(retry):
            if self.am.actors:
                _log.info("{} actors remaining, rechecking in {} secs".format(len(self.am.actors)))
                async.DelayedCall(1*retry, poll_deleted)
            else :
                _log.info("All done, exiting")
                timeout.cancel()
                self.stop()
        async.DelayedCall(0.5, poll_deleted, retry=1)

    def stop_with_migration(self, callback=None):
        # Set timeout if we are still failing after 50 seconds
        timeout_stop = async.DelayedCall(50, self.stop)
        self.quitting = True
        actors = []
        already_migrating = []
        if not self.am.actors:
            return self.stop(callback)
        for actor in self.am.actors.values():
            if actor._migrating_to is None:
                actors.append(actor)
            else:
                already_migrating.append(actor.id)

        def poll_migrated():
            # When already migrating, we can only poll, since we don't get the callback
            if self.am.actors:
                # Check again in a sec
                async.DelayedCall(1, poll_migrated)
                return
            timeout_stop.cancel()
            self.stop(callback)

        def migrated(actor_id, **kwargs):
            actor = self.am.actors.get(actor_id, None)
            status = kwargs['status']
            if actor is not None:
                # Failed to migrate according to requirements, try the current known peers
                peer_ids = self.network.list_direct_links()
                if peer_ids:
                    # This will remove the actor from the list of actors
                    self.am.robust_migrate(actor_id, peer_ids, callback=CalvinCB(migrated, actor_id=actor_id))
                    return
                else:
                    # Ok, we have failed migrate actor according to requirements and to any known peer
                    # FIXME find unknown peers and try migrate to them, now just destroy actor, so storage is cleaned
                    _log.error("Failed to evict actor %s before quitting" % actor_id)
                    self.am.destroy(actor_id)
            if self.am.actors:
                return
            timeout_stop.cancel()
            self.stop(callback)

        if already_migrating:
            async.DelayedCall(1, poll_migrated)
            if not actors:
                return
        elif not actors:
            # No actors
            return self.stop(callback)

        # Migrate the actors according to their requirements
        # (even actors without explicit requirements will migrate based on e.g. requires and port property needs)
        for actor in actors:
            if actor._replication_data.terminate_with_node(actor.id):
                _log.info("TERMINATE REPLICA")
                self.rm.terminate(actor.id, callback=CalvinCB(migrated, actor_id=actor.id))
            else:
                _log.info("TERMINATE MIGRATE ACTOR")
                self.am.update_requirements(actor.id, [], extend=True, move=True,
                            authorization_check=False, callback=CalvinCB(migrated, actor_id=actor.id))

    def _storage_started_cb(self, *args, **kwargs):
        self.authentication.find_authentication_server()
        self.authorization.register_node()

def setup_logging(filename):

    #from twisted.python import log
    #from twisted.internet import defer
    #import sys
    #defer.setDebugging(True)
    #log.startLogging(sys.stdout)

    levels = os.getenv('CALVIN_TESTS_LOG_LEVELS', "").split(':')

    set_file(filename)

    if not levels:
        get_logger().setLevel(logging.INFO)
        return

    for level in levels:
        module = None
        if ":" in level:
            module, level = level.split(":")
        if level == "CRITICAL":
            get_logger(module).setLevel(logging.CRITICAL)
        elif level == "ERROR":
            get_logger(module).setLevel(logging.ERROR)
        elif level == "WARNING":
            get_logger(module).setLevel(logging.WARNING)
        elif level == "INFO":
            get_logger(module).setLevel(logging.INFO)
        elif level == "DEBUG":
            get_logger(module).setLevel(logging.DEBUG)
        elif level == "ANALYZE":
            get_logger(module).setLevel(5)


def create_node(uri, control_uri, attributes=None):
    logfile = os.getenv('CALVIN_TEST_LOG_FILE', None)
    setup_logging(logfile)
    n = Node(uri, control_uri, attributes)
    n.run()
    _log.info('Quitting node "%s"' % n.uris)


def create_tracing_node(uri, control_uri, attributes=None, logfile=None):
    """
    Same as create_node, but will trace every line of execution.
    Creates trace dump in output file '<host>_<port>.trace'
    """
    logfile = os.getenv('CALVIN_TEST_LOG_FILE', None)
    setup_logging(logfile)
    n = Node(uri, control_uri, attributes)
    _, host = uri.split('://')
    with open("%s.trace" % (host, ), "w") as f:
        tmp = sys.stdout
        # Modules to ignore
        ignore = [
            'queue', 'calvin', 'actor', 'pickle', 'socket',
            'uuid', 'codecs', 'copy_reg', 'string_escape', '__init__',
            'colorlog', 'posixpath', 'glob', 'genericpath', 'base',
            'sre_parse', 'sre_compile', 'fdesc', 'posixbase', 'escape_codes',
            'fnmatch', 'urlparse', 're', 'stat', 'six'
        ]
        with f as sys.stdout:
            paths = sys.path
            #tracer = trace.Trace(trace=1, count=0, ignoremods=ignore)
            tracer = trace.Trace(trace=1, count=0, ignoredir=paths)
            tracer.runfunc(n.run)
        sys.stdout = tmp
    _log.info('Quitting node "%s"' % n.uris)


def start_node(uri, control_uri, trace_exec=False, attributes=None):
    if not security_modules_check():
        raise Exception("Security module missing")
    _create_node = create_tracing_node if trace_exec else create_node
    p = Process(target=_create_node, args=(uri, control_uri, attributes))
    p.daemon = True
    p.start()
    return p
