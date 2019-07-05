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


import re

# from calvin.runtime.north.plugins.storage import storage_factory
from calvin.actor.port_property_syntax import list_port_property_capabilities
from calvin.runtime.south import asynchronous
from calvin.common import calvinlogger
from calvin.common.calvin_callback import CalvinCB
from calvin.common import calvinconfig
from calvin.common import dynops
from calvin.common import calvinresponse
from calvin.runtime.north.calvinsys import get_calvinsys
from calvin.runtime.north.calvinlib import get_calvinlib
from calvin.runtime.north.plugins.storage.storage_clients import LocalRegistry, NullRegistryClient, registry
from .storage_proxyserver import StorageProxyServer

_log = calvinlogger.get_logger(__name__)

# FIXME: How and when and by whom is this used? Where does it belong?
def _index_strings(index, root_prefix_level):
    # Add default behaviour here to make it less fragile.
    if root_prefix_level is None:
        root_prefix_level = 2
    # Make the list of index levels that should be used
    # The index string must been escaped with \/ and \\ for / and \ within levels, respectively
    if isinstance(index, list):
        items = index
    else:
        items = re.split(r'(?<![^\\]\\)/', index.lstrip("/"))
    if root_prefix_level > 0:
        root = "/".join(items[:root_prefix_level])
        del items[:root_prefix_level]
        items.insert(0, root)

    return items


class PrivateStorage(object):

    """
    Storage helper functions.
    All functions in this class should be async and never block.
    """

    def __init__(self, node, storage_type, server=None):
        self.node = node
        self.localstorage = LocalRegistry()
        self.storage = NullRegistryClient()

        self.storage_type = storage_type
        self.storage_host = server

        self.storage_proxy_server = None

        self.flush_delayedcall = None
        self.reset_flush_timeout()

    ### Storage life cycle management ###

    def reset_flush_timeout(self):
        """ Reset flush timeout
        """
        self.flush_timeout = 0.2

    def trigger_flush(self, delay=None):
        """ Trigger a flush of internal data
        """
        # if self.localstore or self.localstore_sets:
        if delay is None:
            delay = self.flush_timeout
        if self.flush_delayedcall is None:
            self.flush_delayedcall = asynchronous.DelayedCall(delay, self.flush_localdata)

    def flush_localdata(self):
        """ Write data in localstore to storage
        """
        _log.debug("Flush local storage data")
        if self.flush_timeout < 600:
            self.flush_timeout = self.flush_timeout * 2
        self.flush_delayedcall = None

        # FIXME: localstorage iterable as a stop-gap measure?
        # N.B. Must use copy of keys here since content may change
        for key in list(self.localstorage.localstore.keys()):
            _log.debug("Flush key %s: " % (key,))
            value = self.localstorage.get(key)
            self.storage.set(key=key, value=value, cb=CalvinCB(func=self.set_cb, key=key, org_key=None, org_value=None, org_cb=None, silent=True))

        # FIXME: localstorage_sets iterable as a stop-gap measure?
        # N.B. Must use copy of items here since content may change
        for key, value in list(self.localstorage.localstore_sets.items()):
            if isinstance(key, tuple):
                self._flush_add_index(key, value['+'])
                self._flush_remove_index(key, value['-'])
            else:
                self._flush_append(key, value['+'])
                self._flush_remove(key, value['-'])


    #
    # These callbacks or now only used during flush, and ALWAYS with org_cb = None
    #
    def append_cb(self, key, value, org_key, org_value, org_cb, silent=False):
        """ append callback, on error retry after flush_timeout
        """
        if value:
            self.localstorage._update_sets_add(key)
            self.reset_flush_timeout() # FIXME: Only if change made?
        # else:
        #     if not silent:
        #         _log.warning("Failed to update %s" % key)

        # if org_cb:
        #     org_cb(key=org_key, value=value)
        self.trigger_flush()

    def remove_cb(self, key, value, org_key, org_value, org_cb, silent=False):
        """ remove callback, on error retry after flush_timeout
        """
        if value:
            self.localstorage._update_sets_remove(key)
            self.reset_flush_timeout() # FIXME: Only if change made?
        # else:
        #     if not silent:
        #         _log.warning("Failed to update %s" % key)

        # if org_cb:
        #     org_cb(key=org_key, value=value)
        self.trigger_flush()

    def _flush_append(self, key, value):
        if not value: return

        _log.debug("Flush append on key %s: %s" % (key, list(value)))
        self.storage._append(key=key, value=list(value), cb=CalvinCB(func=self.append_cb, org_key=None, org_value=None, org_cb=None, silent=True))

    def _flush_remove(self, key, value):
        if not value:
            return

        _log.debug("Flush remove on key %s: %s" % (key, list(value)))
        self.storage._remove(key=key, value=list(value), cb=CalvinCB(func=self.remove_cb, org_key=None, org_value=None, org_cb=None, silent=True))


    def _flush_add_index(self, key, value):
        if not value:
            return

        _log.debug("Flush add_index on %s: %s" % (key, list(value)))
        self.storage.add_index(indexes=list(key), value=list(value),
            cb=CalvinCB(self.add_index_cb, org_value=value, org_cb=None, index_items=list(key), silent=True))

    def _flush_remove_index(self, key, value):
        if not value:
            return

        _log.debug("Flush remove_index on %s: %s" % (key, list(value)))
        self.storage.remove_index(indexes=list(key), value=list(value),
            cb=CalvinCB(self.remove_index_cb, org_value=value, org_cb=None, index_items=list(key), silent=True))


    def dump(self):
        "Dump the local storage to a temp file"
        import tempfile
        import json
        data = self.localstorage.dump()
        with tempfile.NamedTemporaryFile(mode='w', prefix="storage", delete=False) as fp:
            json.dump(data, fp, indent=4, sort_keys=True)
        return fp.name


    def dump_original(self):
        "Dump the local storage to a temp file"
        import tempfile
        import json
        with tempfile.NamedTemporaryFile(mode='w', prefix="storage", delete=False) as fp:
            fp.write("[")
            json.dump({str(k): str(v) for k, v in iter(self.localstorage.localstore.items())}, fp)
            fp.write(", ")
            json.dump({str(k): list(v['+']) for k, v in iter(self.localstorage.localstore_sets.items())}, fp)
            fp.write("]")
            name = fp.name
        return name

#
# Start of primitive methods
#
    def _started_cb(self, *args, **kwargs):
        """ Called when storage has started, flushes localstore
        """
        if args:
            value = args[0]
        else:
            value = False

        if kwargs.get("value") :
            value = kwargs.get("value")
        # self.storage = registry(self.node, self.storage_type)

        if kwargs.get("flush", True):
            # Default is to flush
            self.trigger_flush(0)
        else:
            _log.warning("Not flushing local store")

        if kwargs["org_cb"]:
            asynchronous.DelayedCall(0, kwargs["org_cb"], value)
        else:
            _log.warning("No original callback in storage started")

    def started_cb(self, *args, **kwargs):
        try:
            self._started_cb(*args, **kwargs)
        except Exception as e:
            _log.exception(f"Failed to start storage: {e}")

    def start(self, cb=None):
        """ Start storage
        """
        _log.analyze(self.node.id, "+", None)
        name = self.node.attributes.get_node_name_as_str() or self.node.id
        # start is handled by the NullRegistryClient and two things can happen here:
        # 1) if we are in "local" mode, it will call the org_cb, and stay forever in place
        # 2) for all other modes, it will call started_cb and NullRegistryClient will get replaced by RegistryClient
        #    handling all communication with the remote registry.
        # self.storage.start(iface=iface, cb=CalvinCB(self.started_cb, org_cb=cb), name=name, nodeid=self.node.id)
        if self.storage_type != 'local':
            self.storage = registry(self.storage_type, self.node, self.storage_host)
        self.storage.start(CalvinCB(self.started_cb, org_cb=cb))

        if self.storage_type != 'proxy':
            self.storage_proxy_server = StorageProxyServer(self.node, self)


    def stop(self, cb=None):
        """ Stop storage
        """
        # self.storage.stop(cb=cb)
        self.storage = NullRegistryClient(self.storage_type)
        if cb:
            cb()

    def barrier(self):
        self.storage.barrier()

    ### Storage operations ###

    def set_cb(self, key, value, org_key, org_value, org_cb, silent=False):
        """ set callback, on error store in localstore and retry after flush_timeout
        """
        if value:
            self.localstorage.delete(key)
            self.reset_flush_timeout() # FIXME: Only if change made?

        if org_cb:
            org_cb(key=key, value=value)

        self.trigger_flush()


    def set(self, prefix, key, value, cb):
        """ Set registry key: prefix+key to be single value: value
            It is assumed that the prefix and key are strings,
            the sum has to be an immutable object.
            Callback cb with signature cb(key=key, value=True/False)
            note that the key here is without the prefix and
            value indicate success.
        """
        _log.debug("Set key %s, value %s" % (prefix + key, value))

        self.localstorage.set(prefix + key, value)
        self.storage.set(key=prefix + key, value=value, cb=CalvinCB(func=self.set_cb, org_key=key, org_value=value, org_cb=cb))

    def get_cb(self, key, value, org_cb, org_key):
        """ get callback
        """
        org_cb(org_key, value)

    def get(self, prefix, key, cb):
        """ Get single value for registry key: prefix+key,
            first look in locally set but not yet distributed registry
            It is assumed that the prefix and key are strings,
            the sum has to be an immutable object.
            Callback cb with signature cb(key=key, value=<retrived value>/CalvinResponse)
            note that the key here is without the prefix.
            CalvinResponse object is returned when value is not found.
        """
        if not cb:
            return
        try:
            value = self.localstorage.get(prefix + key)
            cb(key=key, value=value)
        except:
            self.storage.get(key=prefix + key, cb=CalvinCB(func=self.get_cb, org_cb=cb, org_key=key))


    def delete_cb(self, key, value, org_cb, org_key):
        # FIXME: To work properly we need an extra callback layer...
        """ delete callback
        """
        if org_cb:
            org_cb(key=org_key, value=value)

    def delete(self, prefix, key, cb):
        r""" Delete registry key: prefix+key
            It is assumed that the prefix and key are strings,
            the sum has to be an immutable object.
            This is equivalent to set(..., value=None, ...).
            Callback cb with signature cb(key=key, value=True/False)
            note that the key here is without the prefix and
            value indicate success.
        """
        _log.debug("Deleting key %s" % prefix + key)
        self.localstorage.delete(prefix + key)
        self.storage.delete(prefix + key, cb=CalvinCB(func=self.delete_cb, org_cb=cb, org_key=key))


    def add_index_cb(self, value, org_value, org_cb, index_items, silent=False):
        _log.debug("add index cb value:%s, index_items:%s" % (value, index_items))
        key = tuple(index_items)
        if value:
            # Success
            self.localstorage._update_sets_add_index(key, org_value)
            self.reset_flush_timeout() # FIXME: Only if change made?
        else:
            if not silent:
                _log.warning(f"Failed to update {key}")

        if org_cb:
            org_cb(value=value)
        self.trigger_flush()

    def add_index(self, index, value, root_prefix_level=None, cb=None):
        r"""
        Add single value (e.g. a node id) or list to a set stored in registry
        later retrivable for each level of the index.
        index: The multilevel key:
               a string with slash as delimiter for finer level of index,
               e.g. node/address/example_street/3/buildingA/level3/room3003,
               index string must been escaped with \/ and \\ for / and \ within levels
               OR a list of each levels strings
        value: the value or list that is to be added to the set stored at each level of the index
        root_prefix_level: the top level of the index that can be searched separately,
               with e.g. =1 then node/address can't be split
        cb: Callback with signature cb(value=<CalvinResponse>)
            value indicate success.
        """

        _log.debug("add index %s: %s" % (index, value))
        # Get a list of the index levels
        indexes = _index_strings(index, root_prefix_level)

        self.localstorage.add_index(indexes=indexes, value=value)

        self.storage.add_index(indexes=indexes, value=value,
                cb=CalvinCB(self.add_index_cb, org_cb=cb, index_items=indexes, org_value=value))

    def remove_index_cb(self, value, org_value, org_cb, index_items, silent=False):
        _log.debug("remove index cb value:%s, index_items:%s" % (value, index_items))
        key = tuple(index_items)
        if value:
            # Success
            self.localstorage._update_sets_remove_index(key, org_value)
            self.reset_flush_timeout() # FIXME: Only if change made?
        else:
            if not silent:
                _log.warning(f"Failed to update {key}")

        if org_cb:
            org_cb(value=value)
        self.trigger_flush()

    def remove_index(self, index, value, root_prefix_level=None, cb=None):
        r"""
        Remove single value (e.g. a node id) or list from a set stored in registry
        index: The multilevel key:
               a string with slash as delimiter for finer level of index,
               e.g. node/address/example_street/3/buildingA/level3/room3003,
               node/affiliation/owner/com.ericsson/Harald,
               node/affiliation/name/com.ericsson/laptop,
               index string must been escaped with \/ and \\ for / and \ within levels
               OR a list of each levels strings
        value: the value or list that is to be removed from the set stored at each level of the index
        root_prefix_level: the top level of the index that can be searched separately,
               with e.g. =1 then node/address can't be split
        cb: Callback with signature cb(value=<CalvinResponse>)
            note that the key here is without the prefix and
            value indicate success.
        """

        _log.debug("remove index %s: %s" % (index, value))
        # Get a list of the index levels
        indexes = _index_strings(index, root_prefix_level)

        self.localstorage.remove_index(indexes=indexes, value=value)

        self.storage.remove_index(indexes=indexes, value=value,
                cb=CalvinCB(self.remove_index_cb, org_cb=cb, index_items=indexes, org_value=value))

    def delete_index(self, index, root_prefix_level=None, cb=None):
        r"""
        Delete index entry in registry - this have the semantics of
        remove_index(index, get_index(index)) - NOT IMPLEMENTED since never used
        index: The multilevel key:
               a string with slash as delimiter for finer level of index,
               e.g. node/address/example_street/3/buildingA/level3/room3003,
               node/affiliation/owner/com.ericsson/Harald,
               node/affiliation/name/com.ericsson/laptop,
               index string must been escaped with \/ and \\ for / and \ within levels
               OR a list of each levels strings
        root_prefix_level: the top level of the index that can be searched separately,
               with e.g. =1 then node/address can't be split
        cb: Callback with signature cb(value=<CalvinResponse>)
            value indicate success.
        """

        raise NotImplementedError()

    def get_index_cb(self, value, local_values, org_cb, index_items, silent=False):
        _log.debug("get index cb value:%s, index_items:%s" % (value, index_items))
        if value:
            # Success
            value = set(value).union(local_values)
        else:
            value = local_values
            if not silent:
                _log.warning("Failed to find {}".format("/".join(index_items)))

        if org_cb:
            org_cb(value=list(value))

    def get_index(self, index, root_prefix_level=None, cb=None):
        r"""
        Get multiple values from the registry stored at the index level or
        below it in hierarchy.
        index: The multilevel key:
               a string with slash as delimiter for finer level of index,
               e.g. node/address/example_street/3/buildingA/level3/room3003,
               node/affiliation/owner/com.ericsson/Harald,
               node/affiliation/name/com.ericsson/laptop,
               index string must been escaped with \/ and \\ for / and \ within levels
               OR a list of each levels strings
        cb: Callback cb with signature cb(value=<retrived values>),
            value is a list.

        The registry can be eventually consistent,
        e.g. a removal of a value might only have reached part of a
        distributed registry and hence still be part of returned
        list of values, it may also miss values added by others but
        not yet distributed.
        """

        _log.debug("get index %s" % (index))
        indexes = _index_strings(index, root_prefix_level)
        # Collect a value set from all key-indexes that include the indexes, always compairing full index levels
        local_values = self.localstorage.get_index(indexes=indexes)
        self.storage.get_index(indexes=indexes,
                cb=CalvinCB(self.get_index_cb, org_cb=cb, index_items=indexes, local_values=local_values))

    def get_index_iter_cb(self, value, it, org_key):
        _log.debug("get index iter cb key: %s value: %s" % (org_key, value))
        if calvinresponse.isnotfailresponse(value):
            it.extend(value)
        it.final()

    # FIXME: include_key and root_prefix_level are UNUSED
    def get_index_iter(self, index, root_prefix_level=None):
        r"""
        Get multiple values from the registry stored at the index level or
        below it in hierarchy.
        index: The multilevel key:
               a string with slash as delimiter for finer level of index,
               e.g. node/address/example_street/3/buildingA/level3/room3003,
               node/affiliation/owner/com.ericsson/Harald,
               node/affiliation/name/com.ericsson/laptop,
               index string must been escaped with \/ and \\ for / and \ within levels
               OR a list of each levels strings
        include_key: When the parameter include_key is True a tuple of (index, value)
               is placed in dynamic interable instead of only the retrived value,
               note it is only the supplied index, not for each sub-level.
        returned: Dynamic iterable object
            Values are placed in the dynamic iterable object.
            The dynamic iterable are of the List subclass to
            calvin.common.dynops.DynOps, see DynOps for details
            of how they are used. The final method will be called when
            all values are appended to the returned dynamic iterable.
        """
        _log.debug("get index iter %s" % (index))
        indexes = _index_strings(index, root_prefix_level)
        org_key = "/".join(indexes)
        # TODO push also iterable into plugin?
        it = dynops.List()
        self.get_index(index=index, root_prefix_level=root_prefix_level,
            cb=CalvinCB(self.get_index_iter_cb, it=it, org_key=org_key))
        return it

class Storage(PrivateStorage):
#
# Secondary methods (using the above methods)
#

    ### Calvin object handling ###

    def add_node(self, node, cb=None):
        """
        Add node to storage
        """
        self.set(prefix="node-", key=node.id,
                  value={"uris": node.uris,
                         "control_uris": [node.external_control_uri],
                         "attributes": {'public': node.attributes.get_public(),
                                        'indexed_public': node.attributes.get_indexed_public(as_list=False)}}, cb=cb)
        # add this node to set of super nodes if fulfill criteria
        self._add_super_node(node)
        # Fill the index
        self._add_node_index(node)
        # Store all actors on this node in storage

    def _add_super_node(self, node):
        """ The term super node is to list runtimes that are more capable/central than others.
            Currently it will contain calvin-base runtimes not using proxy storage,
            but this might change to include other criteria, like computational power,
            steady/temporary, etc.
            We will have 4 classes: 0-3 with class 3 most super.
            It is possible to search for a class or higher
        """
        if self.storage_type != 'proxy':
            node.super_node_class = 1
        else:
            node.super_node_class = 0
        self.add_index(['supernode'] + list(map(str, list(range(node.super_node_class + 1)))), node.id, root_prefix_level=1)

    def _remove_super_node(self, node):
        if node.super_node_class is not None:
            self.remove_index(['supernode'] + list(map(str, list(range(node.super_node_class + 1)))), node.id, root_prefix_level=1)

    def get_super_node(self, super_node_class, cb):
        self.get_index(['supernode'] + list(map(str, list(range(super_node_class + 1)))), root_prefix_level=1, cb=cb)

    def _add_node_index(self, node, cb=None):
        indexes = node.attributes.get_indexed_public()
        try:
            for index in indexes:
                # TODO add callback, but currently no users supply a cb anyway
                self.add_index(index, node.id)
        except:
            _log.debug("Add node index failed", exc_info=True)
            pass
        # Add the capabilities
        try:
            for c in get_calvinsys().list_capabilities():
                self.add_index(['node', 'capabilities', c], node.id, root_prefix_level=3)
            for c in get_calvinlib().list_capabilities():
                self.add_index(['node', 'capabilities', c], node.id, root_prefix_level=3)
        except:
            _log.debug("Add node capabilities failed", exc_info=True)
            pass
        # Add the port property capabilities
        try:
            for c in list_port_property_capabilities():
                self.add_index(['node', 'capabilities', c], node.id, root_prefix_level=3)
        except:
            _log.debug("Add node port property capabilities failed", exc_info=True)
            pass

    def remove_node_index(self, node, cb=None):
        indexes = node.attributes.get_indexed_public()
        try:
            for index in indexes:
                # TODO add callback, but currently no users supply a cb anyway
                self.remove_index(index, node.id)
        except:
            _log.debug("Remove node index failed", exc_info=True)

    def get_node(self, node_id, cb=None):
        """
        Get node data from storage
        """
        self.get(prefix="node-", key=node_id, cb=cb)

    def delete_node(self, node, cb=None):
        """
        Delete node from storage
        """
        self.delete(prefix="node-", key=node.id, cb=None if node.attributes.get_indexed_public() else cb)
        self._remove_super_node(node)
        if node.attributes.get_indexed_public():
            self._delete_node_index(node, cb=cb)


    def _delete_node_index(self, node, cb=None):
        indexes = node.attributes.get_indexed_public()
        _log.analyze(self.node.id, "+", {'indexes': indexes})
        try:
            counter = [len(indexes)]  # counter value by reference used in callback
            for index in indexes:
                self.remove_index(index, node.id, cb=CalvinCB(self._delete_node_cb, counter=counter, org_cb=cb))
            # The remove index gets 1 second otherwise we call the callback anyway, i.e. stop the node
            asynchronous.DelayedCall(1.0, self._delete_node_timeout_cb, counter=counter, org_cb=cb)
        except:
            _log.debug("Remove node index failed", exc_info=True)
            if cb:
                cb()

    def _delete_node_cb(self, counter, org_cb, *args, **kwargs):
        _log.analyze(self.node.id, "+", {'counter': counter[0]})
        counter[0] = counter[0] - 1
        if counter[0] == 0 and org_cb:
            org_cb(*args, **kwargs)

    def _delete_node_timeout_cb(self, counter, org_cb):
        _log.analyze(self.node.id, "+", {'counter': counter[0]})
        if counter[0] > 0:
            _log.debug("Delete node index not finished but call callback anyway")
            org_cb()

    def add_application(self, application, cb=None):
        """
        Add application to storage
        """
        # FIXME: Add method to application class: data_for_registry()?

        _log.debug("Add application %s id %s" % (application.name, application.id))

        data = application.data_for_registry()
        self.set(prefix="application-", key=application.id, value=data, cb=cb)

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
        # TODO need to store app-id
        _log.debug("Add actor %s id %s" % (actor, node_id))
        data = actor.data_for_registry()
        data["node_id"] = node_id

        ports = list(actor.inports.values()) + list(actor.outports.values())
        self._add_ports(ports, node_id)

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

    def _add_ports(self, ports, node_id):
        for p in ports:
            self.add_port(p, node_id)

    def add_port(self, port, node_id, cb=None):
        """
        Add port to storage
        """
        data = port.data_for_registry()
        data["node_id"] = node_id
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


