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
import time
import glob
import importlib

from calvin.utilities import calvinuuid
from calvin.utilities.calvin_callback import CalvinCB
import calvin.requests.calvinresponse as response
from calvin.runtime.south.plugins.async import async
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig
_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()

# FIXME should be read from calvin config
TRANSPORT_PLUGIN_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), *['south', 'plugins', 'transports'])
TRANSPORT_PLUGIN_NS = "calvin.runtime.south.plugins.transports"


class CalvinBaseLink(object):
    """ Base class for a link
    """

    def __init__(self, peer_id):
        super(CalvinBaseLink, self).__init__()
        self.peer_id = peer_id
        self._rtt = None

    def reply_handler(self, payload):
        raise NotImplementedError()

    def send_with_reply(self, callback, msg, dest_peer_id=None):
        raise NotImplementedError()

    def send(self, msg, dest_peer_id=None):
        raise NotImplementedError()

    def close(self, dest_peer_id=None):
        raise NotImplemented()

    def get_rtt(self):
        return self._rtt

class CalvinLink(CalvinBaseLink):
    """ CalvinLink class manage one RT to RT link between
        rt_id and peer_id using transport as mechanism.
        transport: a plug-in transport object
        old_link: should be supplied when we replace an existing link, will be closed
    """

    def __init__(self, rt_id, peer_id, transport, server_node_name=None, old_link=None):
        super(CalvinLink, self).__init__(peer_id)
        self._rtt = transport.get_rtt()
        if self._rtt is None:
            self._rtt = 0.2
        self.rt_id = rt_id
        self.transport = transport
        self.routes = old_link.routes if old_link else []
        # FIXME replies should also be made independent on the link object,
        # to handle dying transports losing reply callbacks
        self.replies = old_link.replies if old_link else {}
        self.replies_timeout = old_link.replies_timeout if old_link else {}
        self.peer_is_sleeping = False
        self.buffered_msgs = []
        if old_link:
            # close old link after a period, since might still receive messages on the transport layer
            # TODO chose the delay based on RTT instead of arbitrary 3 seconds
            _log.analyze(self.rt_id, "+ DELAYED LINK CLOSE", {})
            async.DelayedCall(3.0, old_link.close)

    def reply_handler(self, payload):
        """ Gets called when a REPLY messages arrives on this link """
        try:
            # Cancel timeout
            self.replies_timeout.pop(payload['msg_uuid']).cancel()
        except KeyError:
            _log.warning("Tried to handle reply for unknown message msgid %s", payload['msg_uuid'])
            # We ignore any errors in cancelling timeout
            pass

        try:
            # Call the registered callback,for the reply message id, with the reply data as argument
            reply = self.replies.pop(payload['msg_uuid'])

            # RTT here also inlcudes delay(actors running...) times in remote runtime
            self._rtt = (self._rtt*2 + (time.time() - reply['send_time']))/3

            reply['callback'](response.CalvinResponse(encoded=payload['value']))
        except KeyError:
            _log.warning("Tried to handle reply for unknown message msgid %s", payload['msg_uuid'])
        except: # Dangerous but needed
            _log.exception("Unknown exception in response handler")
            # We ignore unknown replies
            return

    def reply_timeout(self, msg_id):
        """ Gets called when a request times out """
        try:
            # remove timeout
            self.replies_timeout.pop(msg_id)
        except KeyError:
            _log.warning("Tried to handle reply for unknown message msgid {}".format(msg_id))
            # We ignore any errors in cancelling timeout
            pass

        try:
            self.replies.pop(msg_id)['callback'](response.CalvinResponse(response.GATEWAY_TIMEOUT))
        except KeyError:
            _log.warning("Tried to handle reply for unknown message msgid {}".format(msg_id))
        except: # Dangerous but needed
            _log.exception("Unknown exception in response handler")
            # We ignore unknown replies

    def send_with_reply(self, callback, msg, dest_peer_id=None):
        """ Adds a message id to the message and send it,
            also registers the callback for the reply.
        """
        msg_id = calvinuuid.uuid("MSGID")
        self.replies[msg_id] = {'callback': callback, 'send_time': time.time()}
        self.replies_timeout[msg_id] = async.DelayedCall(10.0, CalvinCB(self.reply_timeout, msg_id))
        msg['msg_uuid'] = msg_id
        self.send(msg, dest_peer_id)

    def send(self, msg, dest_peer_id=None):
        """ Adds the from and to node ids to the message and
            sends the message using the transport.

            The from and to node ids seems redundant since the link goes only between
            two nodes. But is included for verification and to later allow routing of messages.
        """
        msg['from_rt_uuid'] = self.rt_id
        msg['to_rt_uuid'] = self.peer_id if dest_peer_id is None else dest_peer_id
        if not self.peer_is_sleeping:
            _log.analyze(self.rt_id, "SEND", msg)
            self.transport.send(msg)
        else:
            _log.analyze(self.rt_id, "SEND_BUFFERED", msg)
            self.buffered_msgs.append(msg)

    def close(self, dest_peer_id=None):
        """ Disconnect the transport and hence the link object won't work anymore """
        _log.analyze(self.rt_id, "+ LINK", {})
        if dest_peer_id is None:
            self.transport.disconnect()

    def flush_buffered_msgs(self):
        for msg in self.buffered_msgs:
            self.send(msg)
        self.buffered_msgs = []

    def set_peer_insleep(self):
        self.peer_is_sleeping = True


class CalvinRoutingLink(CalvinBaseLink):
    """ CalvinRoutingLink class manage one RT to RT link between
        this peer and peer_id using link as an proxy.
    """

    def __init__(self, peer_id, link):
        super(CalvinRoutingLink, self).__init__(peer_id)
        self.link = link

    def reply_handler(self, payload):
        """ Call reply_handler on link """
        self.link.reply_handler(payload)

    def send_with_reply(self, callback, msg, dest_peer_id=None):
        """ Call send_with_reply on link with peer_id.
        """
        self.link.send_with_reply(callback, msg, self.peer_id)

    def send(self, msg, dest_peer_id=None):
        """ Send msg on transport.
        """
        self.link.send(msg, self.peer_id)

    def close(self, dest_peer_id=None):
        """ Call disconnect on link """
        self.link.disconnect(self.peer_id)


class CalvinNetwork(object):
    """ CalvinNetwork keeps track of and establish all runtime to runtime links,
        registers the transport plugins and start their listeners of incoming
        join requests.

        The actual join protocol is handled by each transport plugin.

        TODO enable additional links to be established for other purposes
        than runtime to runtime communication, e.g. direct token transport etc.
    """

    def __init__(self, node):
        super(CalvinNetwork, self).__init__()
        self.node = node
        self.transport_modules = {}  # key module namespace string, value: imported module (must have register function)
        self.transports = {}  # key: URI schema, value: transport factory that handle URI
        self._links = {}  # key peer node id, value: CalvinLink obj
        self._peer_cache = {}  # key peer node id, value is a dict with uri list and timestamp(age) and a list with callbacks
        self._recv_handler = self.__recv_handler
        self.pending_joins = {}  # key: uri, value: list of callbacks or None
        self.pending_joins_by_id = {}  # key: peer id, value: uri
        self.control = self.node.control

    def __recv_handler(self, tp_link, payload):
        _log.debug("Dummy recv handler")
        pass

    def register_recv(self, recv_handler):
        """ Register THE function that will receive all incomming messages on all links """
        _log.debug("Register recv handler %s over old handler %s", recv_handler, self._recv_handler)
        self._recv_handler = recv_handler

    def register(self, schemas, formats):
        """ Load and registers all transport plug-in modules matching the list of schemas.
            The plug-in modules can register any number of schemas with corresponding
            transport factory.
            The transports factories are objects that we can request a join according to a specific
            uri schema or start listening for incoming requests.
        """
        # Find python files in plugins/transport
        module_paths = glob.glob(os.path.join(TRANSPORT_PLUGIN_PATH, "*.py"))
        modules = [os.path.basename(f)[:-3] for f in module_paths if not os.path.basename(
            f).startswith('_') and os.path.isfile(f)]

        # Find directories with __init__.py python file (which should have the register function)
        module_paths = glob.glob(os.path.join(TRANSPORT_PLUGIN_PATH, "*"))
        dirs = [f for f in module_paths if not os.path.basename(f).startswith('_') and os.path.isdir(f)]
        modules += [os.path.basename(d) for d in dirs if os.path.isfile(os.path.join(d, "__init__.py"))]

        # Try to register each transport plugin module
        for m in modules:
            schema_objects = {}
            try:
                self.transport_modules[m] = importlib.import_module(TRANSPORT_PLUGIN_NS + "." + m)
                # Get a dictionary of schemas -> transport factory
                if hasattr(self.transport_modules[m], 'register') and callable(self.transport_modules[m].register):
                    schema_objects = self.transport_modules[m].register(self.node.id,
                                                                        self.node.node_name,
                                                                        {'join_finished': [CalvinCB(self._join_finished)],
                                                                         'join_failed': [CalvinCB(self._join_failed)],
                                                                         'server_started': [CalvinCB(self._server_started)],
                                                                         'server_stopped': [CalvinCB(self._server_stopped)],
                                                                         'data_received': [CalvinCB(self._recv_handler)],
                                                                         'peer_connection_failed': [CalvinCB(self._peer_connection_failed)],
                                                                         'peer_disconnected': [CalvinCB(self._peer_disconnected)]},
                                                                        schemas, formats)
                else:
                    del self.transport_modules[m]
                    continue
            except:
                _log.warning("Could not register transport plugin %s.%s", TRANSPORT_PLUGIN_NS, m, exc_info=True)
                continue
            if schema_objects:
                _log.debug("Register transport plugin %s.%s", TRANSPORT_PLUGIN_NS, m,)
                # Add them to the list - currently only one module can handle one schema
                self.transports.update(schema_objects)

    def _server_started(self, *args):
        _log.debug("Server started %s", args)

    def _server_stopped(self, *args):
        _log.debug("Server stopped %s", args)

    def start_listeners(self, uris=None, stop_callback=None):
        """ Start the transport listening on the uris
            uris: optional list of uri strings. When not provided all schemas will be started.
                  a '<schema>:default' uri can be used to indicate that the transport should
                  use a default configuration, e.g. choose port number.
        """
        if not uris:
            uris = [schema + "://default" for schema in self.transports.keys()]

        for uri in uris:
            schema, addr = uri.split(':', 1)
            self.transports[schema].listen(uri)

    def stop_listeners(self, uris=None, start_callback=None):
        """ Start the transport listening on the uris
            uris: optional list of uri strings. When not provided all schemas will be started.
                  a '<schema>:default' uri can be used to indicate that the transport should
                  use a default configuration, e.g. choose port number.
        """
        if not uris:
            uris = [schema + "://default" for schema in self.transports.keys()]

        for uri in uris:
            schema, addr = uri.split(':', 1)
            self.transports[schema].stop_listening(uri)

    def join(self, uris, callback=None, corresponding_peer_ids=None, corresponding_server_node_names=None):
        """ Join the peers accessable from list of URIs
            It is possible to have a list of corresponding peer_ids,
            which is used to filter the uris list for already connected
            or pending peer's connections.
            URI can't be used for matching since not neccessarily the same if peer connect to us
            uris: list of uris
            callback: will get called for each uri with arguments status, peer_node_id and uri
            corresponding_peer_ids: list of node ids matching the list of uris

            TODO: If corresponding_peer_ids is not specified it is possible that the callback is never called
            when a simultaneous join happens due to that it is not possible to detect by URI only.
            Should add a timeout that cleans out callbacks with failed status replies and let client retry.
        """
        _log.analyze(self.node.id, "+ BEGIN", {'uris': uris,
                                               'peer_ids': corresponding_peer_ids,
                                               'server_node_names': corresponding_server_node_names,
                                               'pending_joins': self.pending_joins,
                                               'pending_joins_by_id': self.pending_joins_by_id}, tb=True)
        # For each URI and when available a peer id
        if not (corresponding_peer_ids and len(uris) == len(corresponding_peer_ids)):
            corresponding_peer_ids = [None] * len(uris)
        # For each URI and when available a server node name
        if not (corresponding_server_node_names and len(uris) == len(corresponding_server_node_names)):
            corresponding_server_node_names = [None] * len(uris)

        for uri, peer_id, server_node_name in zip(uris, corresponding_peer_ids, corresponding_server_node_names):
            if not (uri in self.pending_joins or peer_id in self.pending_joins_by_id or peer_id in self._links):
                # No simultaneous join detected
                schema = uri.split(":", 1)[0]
                _log.analyze(self.node.id, "+", {'uri': uri, 'peer_id': peer_id, 'schema': schema, 'transports': self.transports.keys()}, peer_node_id=peer_id)
                if schema in self.transports.keys():
                    # store we have a pending join and its callback
                    if peer_id:
                        self.pending_joins_by_id[peer_id] = uri
                    if callback:
                        self.pending_joins[uri] = [callback]
                    # Ask the transport plugin to do the join
                    _log.analyze(self.node.id, "+ TRANSPORT", {'uri': uri, 'peer_id': peer_id}, peer_node_id=peer_id)
                    self.transports[schema].join(uri, server_node_name)
                else:
                    _log.warning("Trying to join non existing transport %s", schema)
            else:
                # We have simultaneous joins
                _log.analyze(self.node.id, "+ SIMULTANEOUS", {'uri': uri, 'peer_id': peer_id}, peer_node_id=peer_id)
                if callback:
                    if peer_id in self._links:
                        # Link was already established, then need to call the callback now
                        callback(status=response.CalvinResponse(True), uri=uri)
                        continue
                    # Otherwise also want to be called when the ongoing link setup finishes
                    if uri in self.pending_joins:
                        self.pending_joins[uri].append(callback)
                    else:
                        self.pending_joins[uri] = [callback]

    def _join_finished(self, tp_link, peer_id, uri, is_orginator):
        """ Peer join is (not) accepted, called by transport plugin.
            This may be initiated by us (is_orginator=True) or by the peer,
            i.e. both nodes get called.
            When inititated by us pending_joins likely have a callback

            tp_link: the transport plugins object for the link (have send etc)
            peer_id: the node id we joined
            uri: the uri used for the join
            is_orginator: did this node request the join True/False
        """
        # while a link is pending it is the responsibility of the transport layer, since
        # higher layers don't have any use for it anyway
        _log.analyze(self.node.id, "+", {'uri': uri, 'peer_id': peer_id,
                                         'pending_joins': self.pending_joins,
                                         'pending_joins_by_id': self.pending_joins_by_id},
                                         peer_node_id=peer_id, tb=True)
        if tp_link is None:
            # This is a failed join lets send it upwards
            if uri in self.pending_joins:
                cbs = self.pending_joins.pop(uri)
                if cbs:
                    for cb in cbs:
                        cb(status=response.CalvinResponse(response.SERVICE_UNAVAILABLE), uri=uri, peer_node_id=peer_id)
            return
        # Only support for one RT to RT communication link per peer
        if peer_id in self._links:
            # If link with peer in sleep
            if self._links[peer_id].peer_is_sleeping:
                # Set new transport
                _log.analyze(self.node.id, "+ WAKE_SLEEPING_LINK", {'uri': uri, 'peer_id': peer_id}, peer_node_id=peer_id)
                self._links[peer_id].peer_is_sleeping = False
                self._links[peer_id].transport = tp_link
                self._links[peer_id].flush_buffered_msgs()
            else:
                # Likely simultaneous join requests, use the one requested by the node with highest id
                if is_orginator and self.node.id > peer_id:
                    # We requested it and we have highest node id, hence the one in links is the peer's and we replace it
                    _log.analyze(self.node.id, "+ REPLACE ORGINATOR", {'uri': uri, 'peer_id': peer_id}, peer_node_id=peer_id)
                    self._links[peer_id] = CalvinLink(self.node.id, peer_id, tp_link, self._links[peer_id])
                elif is_orginator and self.node.id < peer_id:
                    # We requested it and peer have highest node id, hence the one in links is peer's and we close this new
                    _log.analyze(self.node.id, "+ DROP ORGINATOR", {'uri': uri, 'peer_id': peer_id}, peer_node_id=peer_id)
                    tp_link.disconnect()
                elif not is_orginator and self.node.id > peer_id:
                    # Peer requested it and we have highest node id, hence the one in links is ours and we close this new
                    _log.analyze(self.node.id, "+ DROP", {'uri': uri, 'peer_id': peer_id}, peer_node_id=peer_id)
                    tp_link.disconnect()
                elif not is_orginator and self.node.id < peer_id:
                    # Peer requested it and peer have highest node id, hence the one in links is ours and we replace it
                    _log.analyze(self.node.id, "+ REPLACE", {'uri': uri, 'peer_id': peer_id}, peer_node_id=peer_id)
                    self._links[peer_id] = CalvinLink(self.node.id, peer_id, tp_link, old_link=self._links[peer_id])
        else:
            # No simultaneous join detected, just add the link
            _log.analyze(self.node.id, "+ INSERT", {'uri': uri, 'peer_id': peer_id}, peer_node_id=peer_id, tb=True)
            self._links[peer_id] = CalvinLink(self.node.id, peer_id, tp_link)

        # Find and call any callbacks registered for the uri or peer id
        _log.debug("join _finished: %s: peer_id: %s, uri: %s\npending_joins_by_id: %s\npending_joins: %s" % (self.node.id, peer_id,
                                                                                         uri,
                                                                                         self.pending_joins_by_id,
                                                                                         self.pending_joins))
        if peer_id in self.pending_joins_by_id:
            peer_uri = self.pending_joins_by_id.pop(peer_id)
            if peer_uri in self.pending_joins:
                cbs = self.pending_joins.pop(peer_uri)
                if cbs:
                    for cb in cbs:
                        cb(status=response.CalvinResponse(True), uri=peer_uri, peer_node_id=peer_id)

        if uri in self.pending_joins:
            cbs = self.pending_joins.pop(uri)
            if cbs:
                for cb in cbs:
                    cb(status=response.CalvinResponse(True), uri=uri, peer_node_id=peer_id)

        self.control.log_link_connected(peer_id, uri)
        return

    def _join_failed(self, tp_link, peer_id, uri, is_orginator, reason):
        cbs = self.pending_joins.pop(uri)
        if cbs:
            for cb in cbs:
                cb(status=response.CalvinResponse(False), uri=uri, peer_node_id=None)
        _log.warning("Join failed on uri %s, reason %s(%s)", uri, reason['reason'], reason['info'])

    def link_get(self, peer_id):
        """ Get a link by node id """
        return self._links.get(peer_id, None)

    def _callback_link(self, peer_id, callback=None):
        # TODO: Do checks here ?!?
        if callback:
            callback(peer_id, self._links[peer_id], status=response.CalvinResponse(True))
        else:
            _log.warning("Trying to send callback but got None!")

    def link_request(self, peer_id, callback=None, **kwargs):
        """
            Request that a link is established. This is the prefered way
            of joining other nodes.
            peer_id: the node id that the link should be establieshed to
            callback: will get called with arguments status and uri used
                      if the link needs to be established

            returns: True when link already exist, False when link needs to be established
        """
        status = kwargs.pop('status', True)
        if not status:
            callback(peer_id, None, status)

        if peer_id in self._links:
            # We have a link lets give it back
            self._callback_link(peer_id, callback)
            return self._links[peer_id]
        elif peer_id in self._peer_cache: # Cache will be invalidated on failures
            _log.analyze(self.node.id, "+ USE CACHE", {}, peer_node_id=peer_id, tb=True)
            self._link_request(peer_id, callback=callback)
            return None

        # We don't have the peer, let's ask for it in storage
        _log.analyze(self.node.id, "+ CHECK STORAGE", {}, peer_node_id=peer_id, tb=True)
        self._peer_cache[peer_id] = {'uris': [], 'timestamp': 0, 'callbacks': [callback]}
        self.node.storage.get_node(peer_id, CalvinCB(self._update_cache_request_finished, callback=None))
        return None

    def _execute_cached_callbacks(self, peer_id):
        if peer_id in self._peer_cache:
            cbs = self._peer_cache[peer_id].pop('callbacks')
            self._peer_cache[peer_id]['callbacks'] = []
            if cbs:
                for cb in cbs:
                    self._callback_link(peer_id, cb)

    def _link_request_finished(self, status=None, peer_node_id=None, uri=None, peer_id=None):
        """
            Will be called when join works or fails also on connection fails.
            Can be called multiple times one for each uri, but will stop on one success.
            This function will try all uris for a node and after that invalidate the cache if its too old.

            If all fails it will give up and make the callbacks, if join fails then it also stops.
            It means that the other end dont want us.

        """
        # TODO: Should save if we are the originator, for reconnect reasons
        _log.debug("link request finished %s, %s, %s", status, peer_node_id, uri)
        if status:
            # It worked!
            _log.debug("Join success on peer %s with uri %s", peer_id, uri)
            self._execute_cached_callbacks(peer_id)
            # trigger routed links on link
            link = self._links[peer_id]
            for route in link.routes:
                self._execute_cached_callbacks(peer_id)
        else:
            _ = self._peer_cache[peer_id]['uris'].pop(0)
            _log.debug("Failed to connect to uri %s", _)
            if self._peer_cache[peer_id]['uris']:
                _log.debug("Trying next %s", self._peer_cache[peer_id]['uris'][0])
                self._link_request(peer_id, force=True)
            elif self._peer_cache[peer_id]['timestamp'] + 5*60 < time.time():
                _log.debug("Cache old %s sec, updateing cache", time.time() - self._peer_cache[peer_id]['timestamp'])
                # Invalidate cache and try one more time
                # WARNING: here if one iteration takes more then 5 minutes then we are in a retry loop :/
                self.node.storage.get_node(peer_id, CalvinCB(self._update_cache_request_finished, callback=None))
            else:
                cbs = self._peer_cache[peer_id].pop('callbacks')
                self._peer_cache[peer_id]['callbacks'] = []
                if cbs:
                    for cb in cbs:
                        cb(peer_id, None, status=response.CalvinResponse(False))
                _log.warning("Join failed on peer %s on all uris", peer_id)

    def _link_request(self, peer_id, callback=None, force=False):
        """
            Called on the cached items when the node wants to
            connect to another node.
            Can be called multiple times and will generate callbacks for all requests.
            The callback will be called when all entries have failed or one have succeded.

            force: is for cache invalidation, same request

            When all the uris have failed or the cache is to old it will be invalidated and a new
            connection cycle is started.

        """
        _log.debug("Internal link request node %s, force %s", peer_id, force)
        if not self._peer_cache[peer_id]['callbacks'] or force:
            if not self._peer_cache[peer_id]['callbacks'] and callback:
                self._peer_cache[peer_id]['callbacks'] = [callback]
            _log.debug("First call or force")
            self.join([self._peer_cache[peer_id]['uris'][0]], CalvinCB(self._link_request_finished, peer_id=peer_id),
                      corresponding_server_node_names=[self._peer_cache[peer_id]['server_name']])
        elif callback:
            _log.debug("Trying to join already ongoing join, just adding callback %s", callback)
            self._peer_cache[peer_id]['callbacks'].append(callback)

    def _routing_link_finished(self, peer_id, link, status, dest_peer_id, callback):
        if not link or not status:
            _log.error("Failed to create routed link to '%s' through '%s'", dest_peer_id, peer_id)
        else:
            self._links[dest_peer_id] = CalvinRoutingLink(dest_peer_id, link)
            link.routes.append(dest_peer_id)
            self._execute_cached_callbacks(dest_peer_id)

    def _update_cache_request_finished(self, key, value, callback, force=False):
        """ Called by storage when the node is (not) found """
        _log.debug("Got response from storage key = %s, value = %s, callback = %s, force = %s", key, value, callback, force)
        _log.analyze(self.node.id, "+", {'value': value}, peer_node_id=key, tb=True)

        if response.isfailresponse(value):
            # the peer_id did not exist in storage
            _log.info("Failed to get node %s info from storage", key)
            if key in self._peer_cache:
                self._peer_cache.pop(key)
            callback(status=response.CalvinResponse(response.NOT_FOUND, {'peer_node_id': key}))
            return

        matching = [s for s in value['attributes']['indexed_public'] if "node_name" in s]
        if matching:
            first_match = matching[0].split("node_name/")[1]
            server_node_name_as_str = first_match.replace("/","-")
        else:
            server_node_name_as_str = None

        # Set values from storage
        self._peer_cache[key]['uris'] = value['uris']
        self._peer_cache[key]['timestamp'] = time.time()
        self._peer_cache[key]['server_name'] = server_node_name_as_str

        if 'proxy' not in value:
            # join the peer node
            self._link_request(key, callback=callback, force=True)
        else:
            if value['proxy'] == self.node.id:
                _log.error("No link to proxy client '%s'", key)
            else:
                self.link_request(value['proxy'], CalvinCB(self._routing_link_finished, dest_peer_id=key, callback=callback))

    # Static
    def get_supported_uri(self, uri_or_uris):
        """ Match configured transport interfaces with uris and return first match.
            returns: First supported uri, None if no match
        """
        if not isinstance(uri_or_uris, list):
            uris = [uri_or_uris]
        else :
            uris = uri_or_uris

        transports = _conf.get(None, 'transports')

        supported_uris = []

        for uri in uris:
            for transport in transports:
                if uri.startswith(transport):
                    supported_uris.append(uri)

        if supported_uris:
            return supported_uris
        return None

    # TODO: send the peer_id and so on upstream
    def _peer_connection_failed(self, tp_link, uri, status):
        cbs = self.pending_joins.pop(uri)
        if cbs:
            for cb in cbs:
                cb(status=response.CalvinResponse(False), uri=uri, peer_node_id=None)

        _log.warning("Connection failed on uri {}, status {}".format(uri, status))

    def _peer_disconnected(self, link, rt_id, reason):
        if reason == "ERROR": _log.warning("Peer disconnected %s with reason %s", rt_id, reason)
        else: _log.debug("Peer disconnected %s with reason %s", rt_id, reason)
        _log.analyze(self.node.id, "+", {'reason': reason,
                                         'links_equal': link == self._links[rt_id].transport if rt_id in self._links else "Gone"},
                                         peer_node_id=rt_id)
        if rt_id in self._links and link == self._links[rt_id].transport:
            if not self._links[rt_id].peer_is_sleeping:
                for route in self._links[rt_id].routes[:]:
                    self.link_remove(route)
                    self.control.log_link_disconnected(route)
                self.link_remove(rt_id)
        self.control.log_link_disconnected(rt_id)

    def link_remove(self, peer_id):
        """ Removes a link to peer id """
        _log.analyze(self.node.id, "+", {}, peer_node_id=peer_id)
        try:
            link = self._links[peer_id]
            if isinstance(link, CalvinRoutingLink):
                link.link.routes.remove(peer_id)
                self._links.pop(peer_id)
            else:
                self._links.pop(peer_id)
        except KeyError:
            _log.error("Tried to remove non existing link to peer_id %s", peer_id)

    def link_check(self, rt_uuid):
        """ Check if we have the link otherwise raise exception """
        if rt_uuid not in self._links.iterkeys():
            raise KeyError("ERROR_LINK_NOT_ESTABLISHED")

    def list_links(self):
        return list(self._links.keys())

    def list_direct_links(self):
        return [peer_id for peer_id, l in self._links.items() if isinstance(l, CalvinLink)]
