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

import os
import logging
import uuid

from calvin.runtime.north.calvinsys import get_calvinsys
from calvin.runtime.north.calvinlib import get_calvinlib
from calvin.runtime.north import actormanager
from calvin.runtime.north import appmanager
from calvin.runtime.north import scheduler
from calvin.runtime.north import storage
from calvin.runtime.north import calvincontrol
from calvin.runtime.north.calvin_network import CalvinNetwork
from calvin.runtime.north.calvin_proto import CalvinProto
from calvin.runtime.north.portmanager import PortManager
from calvin.runtime.south import asynchronous
from calvin.common.attribute_resolver import AttributeResolver
from calvin.common.calvin_callback import CalvinCB
from calvin.common.calvinlogger import get_logger, set_file
from calvin.common import calvinconfig
from calvin.common import metadata_proxy as mdproxy
from calvin.runtime.north.resource_monitor.cpu import CpuMonitor
from calvin.runtime.north.resource_monitor.memory import MemMonitor
from calvin.runtime.north.proxyhandler import ProxyHandler



_log = get_logger(__name__)
_conf = calvinconfig.get()


class Node(object):
    """
    Calvin runtime node
    
    Arguments:       
        uris : a list of calvinip URIs that this runtime listens to
        control_uri : the URI of the REST API (control) that this runtime listens to
        attributes : an (optional) dictionary of externally defined attributes
    
    Properties:
        quitting : a boolean set during shutdown
        uris : 
        control_uri : 
        external_control_uri : 
        attributes : 
        node_name : 
        id : 
        actorstore : 
        am : 
        sched : 
        storage : 
        control : 
        network : 
        proto : 
        pm : 
        app_manager : 
        cpu_monitor : 
        mem_monitor : 
        proxy_handler :         
    """

    def __init__(self, uris, control_uri, attributes=None):
        super(Node, self).__init__()
        self.quitting = False
        self.super_node_class = None

        attributes = attributes or {}
        if not isinstance(uris, list):
            _log.error("Calvin uris must be a list %s" % uris)
            raise TypeError("Calvin uris must be a list!")

        # Uris
        self.uris = uris + attributes.pop('external_uri', [])

        # Control uri
        self.control_uri = control_uri
        self.external_control_uri = attributes.pop('external_control_uri', self.control_uri)

        self.attributes = AttributeResolver(attributes)
        
        self.node_name = self.attributes.get_node_name_as_str()
        # Obtain node id, when using security also handle runtime certificate
        self.id = str(uuid.uuid4())
        
        actorstore_uri = _conf.get('global', 'actorstore')
        self.actorstore = mdproxy.ActorMetadataProxy(actorstore_uri)
        
        self.am = actormanager.ActorManager(self)

        self.sched = scheduler.SimpleScheduler(self, self.am)
        
        
        calvinsys = get_calvinsys()
        calvinsys.init(self)
        calvinlib = get_calvinlib()
        calvinlib.init()


        storage_type = _conf.get('global', 'storage_type')
        storage_host = _conf.get('global', 'storage_host')
        self.storage = storage.Storage(self, storage_type, server=storage_host)
        
        #
        # FIXME: The following section is sensitive to order due to circular references
        #
        proxy_control_uri = _conf.get(None, 'control_proxy')
        self.control = self.start_control(proxy_control_uri)

        self.network = CalvinNetwork(self.id, self.node_name, self.storage, self.control)
        self.proto = CalvinProto(node=self, network=self.network)
        #
        # FIXME: The above section is sensitive to order due to circular references
        #

        self.pm = PortManager(node=self)
        self.app_manager = appmanager.AppManager(node=self)

        self.cpu_monitor = CpuMonitor(self.id, self.storage)
        self.mem_monitor = MemMonitor(self.id, self.storage)

        self.proxy_handler = ProxyHandler(node=self)

        # The initialization that requires the main loop operating is deferred to start function
        asynchronous.DelayedCall(0, self.start)


    def start_control(self, proxy_control_uri):
        _log.info("+++++++++++++++ proxy_control_uri: %s" % proxy_control_uri)
        _log.info("+++++++++++++++ self.control_uri: %s" % self.control_uri)
        if proxy_control_uri:
            _log.info("+++++++++++++++ proxy_control_uri overrides control_uri")
        if proxy_control_uri:
            control = calvincontrol.factory(self, True, proxy_control_uri)
        else:
            control = calvincontrol.factory(self, False, self.control_uri, self.external_control_uri)
        return control
        
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
        self.control.start()

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
        timeout = asynchronous.DelayedCall(50, self.stop)
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
                asynchronous.DelayedCall(1*retry, poll_deleted)
            else :
                _log.info("All done, exiting")
                timeout.cancel()
                self.stop()
        asynchronous.DelayedCall(0.5, poll_deleted, retry=1)

    def stop_with_migration(self, callback=None):
        # Set timeout if we are still failing after 50 seconds
        timeout_stop = asynchronous.DelayedCall(50, self.stop)
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
                asynchronous.DelayedCall(1, poll_migrated)
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
            asynchronous.DelayedCall(1, poll_migrated)
            if not actors:
                return
        elif not actors:
            # No actors
            return self.stop(callback)

        # Migrate the actors according to their requirements
        # (even actors without explicit requirements will migrate based on e.g. requires and port property needs)
        for actor in actors:
            _log.info("TERMINATE MIGRATE ACTOR")
            self.am.update_requirements(actor.id, [], extend=True, move=True, callback=CalvinCB(migrated, actor_id=actor.id))

    def _storage_started_cb(self, *args, **kwargs):
        pass
        
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


