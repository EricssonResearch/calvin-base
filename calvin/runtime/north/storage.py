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

from calvin.runtime.north.plugins.storage import storage_factory
from calvin.runtime.north.plugins.coders.messages import message_coder_factory
from calvin.runtime.south.plugins.async import async
from calvin.utilities import calvinlogger
from calvin.utilities.calvin_callback import CalvinCB
from calvin.actor import actorport
import re

_log = calvinlogger.get_logger(__name__)


class Storage(object):

    """
    Storage helper functions.
    All functions in this class should be async and never block.
    """

    def __init__(self):
        self.localstore = {}
        self.localstore_sets = {}
        self.started = False
        self.storage = storage_factory.get("dht") # TODO: read storage type from config?
        self.coder = message_coder_factory.get("json")  # TODO: always json? append/remove requires json at the moment
        self.flush_delayedcall = None
        self.flush_timout = 1

    ### Storage life cycle management ###

    def flush_localdata(self):
        """ Write data in localstore to storage
        """
        _log.debug("Flush local storage data")
        self.flush_delayedcall = None
        for key in self.localstore:
            self.storage.set(key=key, value=self.localstore[key],
                             cb=CalvinCB(func=self.set_cb, org_key=None, org_value=None, org_cb=None))
        for key, value in self.localstore_sets.iteritems():
            if value['+']:
                _log.debug("Flush append on key %s: %s" % (key, list(value['+'])))
                coded_value = self.coder.encode(list(value['+']))
                self.storage.append(key=key, value=coded_value,
                                    cb=CalvinCB(func=self.append_cb, org_key=None, org_value=None, org_cb=None))
            if value['-']:
                _log.debug("Flush remove on key %s: %s" % (key, list(value['-'])))
                coded_value = self.coder.encode(list(value['-']))
                self.storage.remove(key=key, value=coded_value,
                                    cb=CalvinCB(func=self.remove_cb, org_key=None, org_value=None, org_cb=None))

    def started_cb(self, *args, **kwargs):
        """ Called when storage has started, flushes localstore
        """
        if args[0] == True:
            self.started = True
            self.flush_localdata()
            if kwargs["org_cb"]:
                kwargs["org_cb"](args[0])

    def start(self, iface='', cb=None):
        """ Start storage
        """
        self.storage.start(iface=iface, cb=CalvinCB(self.started_cb, org_cb=cb))

    def stop(self, cb=None):
        """ Stop storage
        """
        if self.started:
            self.storage.stop(cb=cb)
        self.started = False

    ### Storage operations ###

    def set_cb(self, key, value, org_key, org_value, org_cb):
        """ set callback, on error store in localstore and retry after flush_timout
        """
        if value == True:
            if org_cb:
                org_cb(key=key, value=True)
            if key in self.localstore:
                del self.localstore[key]
        else:
            _log.error("Failed to store %s" % key)
            if org_key and org_value:
                if not org_value is None:
                    self.localstore[key] = org_value
            if org_cb:
                org_cb(key=key, value=False)
            if self.flush_delayedcall is None:
                self.flush_delayedcall = async.DelayedCall(self.flush_timout, self.flush_localdata)
            else:
                self.flush_delayedcall.reset()

    def set(self, prefix, key, value, cb):
        """ Set key: prefix+key value: value
        """
        if value:
            value = self.coder.encode(value)

        if prefix + key in self.localstore_sets:
            del self.localstore_sets[prefix + key]

        if self.started:
            self.storage.set(key=prefix + key, value=value, cb=CalvinCB(func=self.set_cb, org_key=key, org_value=value, org_cb=cb))
        else:
            if value:
                self.localstore[prefix + key] = value
            if cb:
                cb(key=key, value=True)

    def get_cb(self, key, value, org_cb, org_key):
        """ get callback
        """
        if value:
            value = self.coder.decode(value)
        org_cb(org_key, value)

    def get(self, prefix, key, cb):
        """ Get value for key: prefix+key, first look in localstore
        """
        if cb:
            if prefix + key in self.localstore:
                value = self.localstore[prefix + key]
                if value:
                    value = self.coder.decode(value)
                cb(key=key, value=value)
            else:
                try:
                    self.storage.get(key=prefix + key, cb=CalvinCB(func=self.get_cb, org_cb=cb, org_key=key))
                except:
                    _log.error("Failed to get: %s" % key)
                    cb(key=key, value=False)

    def get_concat_cb(self, key, value, org_cb, org_key):
        """ get callback
        """
        if value:
            value = self.coder.decode(value)
        org_cb(org_key, value)

    def get_concat(self, prefix, key, cb):
        """ Get value for key: prefix+key, first look in localstore
            Return value is list. The storage could be eventually consistent.
            For example a remove might only have reached part of the
            storage and hence the return list might contain removed items,
            but also missing items.
        """
        if cb:
            if prefix + key in self.localstore_sets:
                value = self.localstore_sets[prefix + key]
                # Return the set that we intended to append since that's all we have until it is synced
                cb(key=key, value=list(value['+']))
            else:
                try:
                    self.storage.get_concat(key=prefix + key, cb=CalvinCB(func=self.get_concat_cb, org_cb=cb, org_key=key))
                except:
                    _log.error("Failed to get: %s" % key)
                    cb(key=key, value=False)

    def append_cb(self, key, value, org_key, org_value, org_cb):
        """ append callback, on error retry after flush_timout
        """
        if value == True:
            if org_cb:
                org_cb(key=org_key, value=True)
            if key in self.localstore_sets:
                if self.localstore_sets[key]['-']:
                    self.localstore_sets[key]['+'] = set([])
                else:
                    del self.localstore_sets[key]
        else:
            _log.error("Failed to update %s" % key)
            if org_cb:
                org_cb(key=org_key, value=False)
            if self.flush_delayedcall is None:
                self.flush_delayedcall = async.DelayedCall(self.flush_timout, self.flush_localdata)
            else:
                self.flush_delayedcall.reset()

    def append(self, prefix, key, value, cb):
        """ set operation append on key: prefix+key value: value is a list of items
        """
        # Keep local storage for sets updated until confirmed
        if (prefix + key) in self.localstore_sets:
            # Append value items
            self.localstore_sets[prefix + key]['+'] |= set(value)
            # Don't remove value items any more
            self.localstore_sets[prefix + key]['-'] -= set(value)
        else:
            self.localstore_sets[prefix + key] = {'+': set(value), '-': set([])}

        if self.started:
            coded_value = self.coder.encode(list(self.localstore_sets[prefix + key]['+']))
            self.storage.append(key=prefix + key, value=coded_value,
                                cb=CalvinCB(func=self.append_cb, org_key=key, org_value=value, org_cb=cb))
        else:
            if cb:
                cb(key=key, value=True)

    def remove_cb(self, key, value, org_key, org_value, org_cb):
        """ remove callback, on error retry after flush_timout
        """
        if value == True:
            if org_cb:
                org_cb(key=org_key, value=True)
            if key in self.localstore_sets:
                if self.localstore_sets[key]['+']:
                    self.localstore_sets[key]['-'] = set([])
                else:
                    del self.localstore_sets[key]
        else:
            _log.error("Failed to update %s" % key)
            if org_cb:
                org_cb(key=org_key, value=False)
            if self.flush_delayedcall is None:
                self.flush_delayedcall = async.DelayedCall(self.flush_timout, self.flush_localdata)
            else:
                self.flush_delayedcall.reset()

    def remove(self, prefix, key, value, cb):
        """ set operation remove on key: prefix+key value: value is a list of items
        """
        # Keep local storage for sets updated until confirmed
        if (prefix + key) in self.localstore_sets:
            # Don't append value items any more
            self.localstore_sets[prefix + key]['+'] -= set(value)
            # Remove value items
            self.localstore_sets[prefix + key]['-'] |= set(value)
        else:
            self.localstore_sets[prefix + key] = {'+': set([]), '-': set(value)}

        if self.started:
            coded_value = self.coder.encode(list(self.localstore_sets[prefix + key]['-']))
            self.storage.remove(key=prefix + key, value=coded_value,
                                cb=CalvinCB(func=self.remove_cb, org_key=key, org_value=value, org_cb=cb))
        else:
            if cb:
                cb(key=key, value=True)

    def delete(self, prefix, key, cb):
        """ Delete key: prefix+key (value set to None)
        """
        if prefix + key in self.localstore:
            del self.localstore[prefix + key]
        if (prefix + key) in self.localstore_sets:
            del self.localstore_sets[prefix + key]
        if self.started:
            self.set(prefix, key, None, cb)
        else:
            if cb:
                cb(key, True)

    ### Calvin object handling ###

    def add_node(self, node, cb=None):
        """
        Add node to storage
        """
        self.set(prefix="node-", key=node.id,
                  value={"uri": node.uri,
                         "control_uri": node.control_uri,
                         "attributes": {'public': node.attributes.get_public(),
                                        'indexed_public': node.attributes.get_indexed_public(as_list=False)}}, cb=cb)
        # Add to index after a while since storage not up and running anyway
        #async.DelayedCall(1.0, self._add_node_index, node)
        self._add_node_index(node)

    def _add_node_index(self, node, cb=None):
        indexes = node.attributes.get_indexed_public()
        try:
            for index in indexes:
                # TODO add callback, but currently no users supply a cb anyway
                self.add_index(index, node.id)
        except:
            _log.debug("Add node index failed", exc_info=True)
            pass

    def get_node(self, node_id, cb=None):
        """
        Get node data from storage
        """
        self.get(prefix="node-", key=node_id, cb=cb)

    def delete_node(self, node, cb=None):
        """
        Delete node from storage
        """
        self.delete(prefix="node-", key=node.id, cb=None if node.attributes else cb)
        if node.attributes:
            self._delete_node_index(node, cb=cb)

    def _delete_node_index(self, node, cb=None):
        indexes = node.attributes.get_indexed_public()
        try:
            counter = [len(indexes)]  # counter value by reference used in callback
            for index in indexes:
                self.remove_index(index, node.id, cb=CalvinCB(self._delete_node_cb, counter=counter, org_cb=cb))
            # The remove index gets 1 second otherwise we call the callback anyway, i.e. stop the node
            async.DelayedCall(1.0, self._delete_node_timeout_cb, counter=counter, org_cb=cb)
        except:
            _log.debug("Remove node index failed", exc_info=True)
            if cb:
                cb()

    def _delete_node_cb(self, counter, org_cb, *args, **kwargs):
        counter[0] = counter[0] - 1
        if counter[0] == 0:
            org_cb(*args, **kwargs)

    def _delete_node_timeout_cb(self, counter, org_cb):
        if counter[0] > 0:
            _log.debug("Delete node index not finished but call callback anyway")
            org_cb()

    def add_application(self, application, cb=None):
        """
        Add application to storage
        """
        _log.debug("Add application %s id %s" % (application.name, application.id))

        self.set(prefix="application-", key=application.id,
                 value={"name": application.name,
                        "actors": application.actors,
                        "origin_node_id": application.origin_node_id},
                 cb=cb)

    def get_application(self, application_id, cb=None):
        """
        Get application from storage
        """
        self.get(prefix="application-", key=application_id, cb=cb)

    def delete_application(self, application_id, cb=None):
        """
        Delete application from storage
        """
        _log.debug("Delete application %s" % application_id)
        self.delete(prefix="application-", key=application_id, cb=cb)

    def add_actor(self, actor, node_id, cb=None):
        """
        Add actor and its ports to storage
        """
        _log.debug("Add actor %s id %s" % (actor, node_id))
        data = {"name": actor.name, "type": actor._type, "node_id": node_id}
        inports = []
        for p in actor.inports.values():
            port = {"id": p.id, "name": p.name}
            inports.append(port)
            self.add_port(p, node_id, actor.id, "in")
        data["inports"] = inports
        outports = []
        for p in actor.outports.values():
            port = {"id": p.id, "name": p.name}
            outports.append(port)
            self.add_port(p, node_id, actor.id, "out")
        data["outports"] = outports
        self.set(prefix="actor-", key=actor.id, value=data, cb=cb)

    def get_actor(self, actor_id, cb=None):
        """
        Get actor from storage
        """
        self.get(prefix="actor-", key=actor_id, cb=cb)

    def delete_actor(self, actor_id, cb=None):
        """
        Delete actor from storage
        """
        _log.debug("Delete actor id %s" % (actor_id))
        self.delete(prefix="actor-", key=actor_id, cb=cb)

    def add_port(self, port, node_id, actor_id=None, direction=None, cb=None):
        """
        Add port to storage
        """
        if direction is None:
            if isinstance(port, actorport.InPort):
                direction = "in"
            else:
                direction = "out"

        if actor_id is None:
            actor_id = port.owner.id

        data = {"name": port.name, "connected": port.is_connected(
        ), "node_id": node_id, "actor_id": actor_id, "direction": direction}
        if direction == "out":
            if port.is_connected():
                data["peers"] = port.get_peers()
            else:
                data["peers"] = []
        elif direction == "in":
            if port.is_connected():
                data["peer"] = port.get_peer()
            else:
                data["peer"] = None
        self.set(prefix="port-", key=port.id, value=data, cb=cb)

    def get_port(self, port_id, cb=None):
        """
        Get port from storage
        """
        self.get(prefix="port-", key=port_id, cb=cb)

    def delete_port(self, port_id, cb=None):
        """
        Delete port from storage
        """
        self.delete(prefix="port-", key=port_id, cb=cb)

    def index_cb(self, key, value, org_cb, index_items):
        """
        Collect all the index levels operations into one callback
        """
        _log.debug("index cb key:%s, value:%s, index_items:%s" % (key, value, index_items))
        #org_key = key.partition("-")[2]
        org_key = key
        # cb False if not already done it at first False value
        if not value and index_items:
            org_cb(key=org_key, value=False)
            del index_items[:]
        if org_key in index_items:
            # remove this index level from list
            index_items.remove(org_key)
            # If all done send True
            if not index_items:
                org_cb(key=org_key, value=True)

    def _index_strings(self, index, root_prefix_level):
        # Make the list of index levels that should be used
        # The index string must been escaped with \/ and \\ for / and \ within levels, respectively
        if isinstance(index, list):
            items = index
        else:
            items = re.split(r'(?<![^\\]\\)/', index.lstrip("/"))
        root = "/".join(items[:root_prefix_level])
        del items[:root_prefix_level]
        items.insert(0, root)

        # index strings for all levels
        indexes = ['/'+'/'.join(items[:l]) for l in range(1,len(items)+1)]
        return indexes

    def add_index(self, index, value, root_prefix_level=3, cb=None):
        """
        Add value (typically a node id) to the storage as a set.
        index: a string with slash as delimiter for finer level of index,
               e.g. node/address/example_street/3/buildingA/level3/room3003,
               node/affiliation/owner/com.ericsson/Harald,
               node/affiliation/name/com.ericsson/laptop
               OR a list of strings
        value: the value that is to be added to the set stored at each level of the index
        root_prefix_level: the top level of the index that can be searched,
               with =1 then e.g. node/address, node/affiliation
        cb: will be called when done.
        """

        # TODO this implementation will store the value to each level of the index.
        # When time permits a proper implementation should be done with for example
        # a prefix hash table on top of the DHT or using other storage backend with
        # prefix search built in.

        _log.debug("add index %s: %s" % (index, value))

        indexes = self._index_strings(index, root_prefix_level)

        # make copy of indexes since altered in callbacks
        for i in indexes[:]:
            self.append(prefix="index-", key=i, value=[value],
                        cb=CalvinCB(self.index_cb, org_cb=cb, index_items=indexes) if cb else None)

    def remove_index(self, index, value, root_prefix_level=2, cb=None):
        """
        Remove value (typically a node id) from the storage as a set.
        index: a string with slash as delimiter for finer level of index,
               e.g. node/address/example_street/3/buildingA/level3/room3003,
               node/affiliation/owner/com.ericsson/Harald,
               node/affiliation/name/com.ericsson/laptop
        value: the value that is to be removed from the set stored at each level of the index
        root_prefix_level: the top level of the index that can be searched,
               with =1 then e.g. node/address, node/affiliation
        cb: will be called when done.
        """

        # TODO this implementation will delete the value to each level of the index.
        # When time permits a proper implementation should be done with for example
        # a prefix hash table on top of the DHT or using other storage backend with
        # prefix search built in.

        # TODO Currently we don't go deeper than the specified index for a remove,
        # e.g. node/affiliation/owner/com.ericsson would remove the value from
        # all deeper indeces. But no current use case exist either.

        _log.debug("remove index %s: %s" % (index, value))

        indexes = self._index_strings(index, root_prefix_level)

        # make copy of indexes since altered in callbacks
        for i in indexes[:]:
            self.remove(prefix="index-", key=i, value=[value],
                        cb=CalvinCB(self.index_cb, org_cb=cb, index_items=indexes) if cb else None)

    def get_index(self, index, cb=None):
        """
        Get index from the storage.
        index: a string with slash as delimiter for finer level of index,
               e.g. node/address/example_street/3/buildingA/level3/room3003,
               node/affiliation/owner/com.ericsson/Harald,
               node/affiliation/name/com.ericsson/laptop
        cb: will be called when done. Should expect to be called several times with
               partial results. Currently only called once.

        Since storage might be eventually consistent caller must expect that the
        list can containe node ids that are removed and node ids have not yet reached
        the storage.
        """

        # TODO this implementation will get the value from the level of the index.
        # When time permits a proper implementation should be done with for example
        # a prefix hash table on top of the DHT or using other storage backend with
        # prefix search built in. A proper implementation might also have several callbacks
        # since might get index from several levels of index trie, and instead of building a complete
        # list before returning better to return iteratively for nodes with less memory
        # or system with large number of nodes, might also need a timeout.

        if not index.startswith("/"):
            index = "/" + index
        _log.debug("get index %s" % (index))
        self.get_concat(prefix="index-", key=index, cb=cb)

