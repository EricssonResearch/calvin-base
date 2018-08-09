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
from calvin.csparser.port_property_syntax import list_port_property_capabilities
from calvin.runtime.south.async import async
from calvin.utilities import calvinlogger
from calvin.utilities.calvin_callback import CalvinCB
from calvin.actor import actorport
from calvin.actor.actor import ShadowActor
from calvin.utilities import calvinconfig
from calvin.actorstore.store import GlobalStore
from calvin.utilities.security import Security, security_enabled
from calvin.utilities import dynops
from calvin.requests import calvinresponse
from calvin.runtime.north.calvinsys import get_calvinsys
from calvin.runtime.north.calvinlib import get_calvinlib
import re
import itertools

_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()

class Storage(object):

    """
    Storage helper functions.
    All functions in this class should be async and never block.
    """

    def __init__(self, node, override_storage=None):
        self.localstore = {}
        self.localstore_sets = {}
        self.started = False
        self.node = node
        storage_type = _conf.get('global', 'storage_type')
        _log.info("#### STORAGE TYPE %s ####", storage_type)
        self.proxy = _conf.get('global', 'storage_proxy') if storage_type == 'proxy' else None
        _log.analyze(self.node.id, "+", {'proxy': self.proxy})
        self.tunnel = {}
        self.starting = storage_type != 'local'
        if override_storage:
            self.storage = override_storage
        else:
            self.storage = storage_factory.get(storage_type, node)
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
        if self.localstore or self.localstore_sets:
            if delay is None:
                delay = self.flush_timeout
            if self.flush_delayedcall is None:
                self.flush_delayedcall = async.DelayedCall(delay, self.flush_localdata)

    def flush_localdata(self):
        """ Write data in localstore to storage
        """
        _log.debug("Flush local storage data")
        if self.flush_timeout < 600:
            self.flush_timeout = self.flush_timeout * 2
        self.flush_delayedcall = None
        for key in self.localstore:
            _log.debug("Flush key %s: %s" % (key, self.localstore[key]))
            self.storage.set(key=key, value=self.localstore[key],
                             cb=CalvinCB(func=self.set_cb, org_key=None, org_value=None, org_cb=None, silent=True))

        for key, value in self.localstore_sets.iteritems():
            if isinstance(key, tuple):
                self._flush_add_index(key, value['+'])
                self._flush_remove_index(key, value['-'])
            else:
                self._flush_append(key, value['+'])
                self._flush_remove(key, value['-'])

    def _flush_append(self, key, value):
        if not value:
            return

        _log.debug("Flush append on key %s: %s" % (key, list(value)))
        self.storage.append(key=key, value=list(value),
                            cb=CalvinCB(func=self.append_cb, org_key=None, org_value=None, org_cb=None, silent=True))

    def _flush_remove(self, key, value):
        if not value:
            return

        _log.debug("Flush remove on key %s: %s" % (key, list(value)))
        self.storage.remove(key=key, value=list(value),
                            cb=CalvinCB(func=self.remove_cb, org_key=None, org_value=None, org_cb=None, silent=True))


    def _flush_add_index(self, key, value):
        if not value:
            return

        _log.debug("Flush add_index on %s: %s" % (key, list(value)))
        self.storage.add_index(prefix="index-", indexes=list(key), value=list(value),
            cb=CalvinCB(self.add_index_cb, org_value=value, org_cb=None, index_items=list(key), silent=True))

    def _flush_remove_index(self, key, value):
        if not value:
            return

        _log.debug("Flush remove_index on %s: %s" % (key, list(value)))
        self.storage.remove_index(prefix="index-", indexes=list(key), value=list(value),
            cb=CalvinCB(self.remove_index_cb, org_value=value, org_cb=None, index_items=list(key), silent=True))

    def started_cb(self, *args, **kwargs):
        """ Called when storage has started, flushes localstore
        """
        _log.debug("Storage started!!")
        if not args[0]:
            return

        self.started = True
        self.trigger_flush(0)
        if kwargs["org_cb"]:
            async.DelayedCall(0, kwargs["org_cb"], args[0])

    def dump(self):
        "Dump the local storage to a temp file"
        import tempfile
        import json
        with tempfile.NamedTemporaryFile(mode='w', prefix="storage", delete=False) as fp:
            fp.write("[")
            json.dump({str(k): str(v) for k, v in self.localstore.items()}, fp)
            fp.write(", ")
            json.dump({str(k): list(v['+']) for k, v in self.localstore_sets.items()}, fp)
            fp.write("]")
            name = fp.name
        return name

    def start(self, iface='', cb=None):
        """ Start storage
        """
        _log.analyze(self.node.id, "+", None)
        if self.starting:
            name = self.node.attributes.get_node_name_as_str() or self.node.id
            try:
                self.storage.start(iface=iface, cb=CalvinCB(self.started_cb, org_cb=cb), name=name, nodeid=self.node.id)
            except:
                _log.exception("Failed start of storage for name={}, switches to local".format(name))
        elif cb:
            async.DelayedCall(0, cb)

        self._init_proxy()

    def _init_proxy(self):
        _log.analyze(self.node.id, "+ SERVER", None)
        # We are not proxy client, so we can be proxy bridge/master
        self._proxy_cmds = {'GET': self.get,
                            'SET': self.set,
                            'GET_CONCAT': self.get_concat,
                            'APPEND': self.append,
                            'REMOVE': self.remove,
                            'DELETE': self.delete,
                            'REPLY': self._proxy_reply,
                            'ADD_INDEX': self.add_index,
                            'REMOVE_INDEX': self.remove_index,
                            'GET_INDEX': self.get_index
                            }
        try:
            self.node.proto.register_tunnel_handler('storage', CalvinCB(self.tunnel_request_handles))
        except:
            # OK, then skip being a proxy server
            pass

    def stop(self, cb=None):
        """ Stop storage
        """
        _log.analyze(self.node.id, "+", {'started': self.started})
        if self.started:
            self.storage.stop(cb=cb)
        elif cb:
            cb()
        self.started = False

    ### Storage operations ###

    def set_cb(self, key, value, org_key, org_value, org_cb, silent=False):
        """ set callback, on error store in localstore and retry after flush_timeout
        """
        if value:
            if key in self.localstore:
                del self.localstore[key]
            self.reset_flush_timeout()
        else:
            if not silent:
                _log.error("Failed to store %s" % key)
            if org_key and org_value:
                if not org_value is None:
                    self.localstore[key] = org_value

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

        if prefix + key in self.localstore_sets:
            del self.localstore_sets[prefix + key]

        # Always save locally
        self.localstore[prefix + key] = value
        if self.started:
            self.storage.set(key=prefix + key, value=value, cb=CalvinCB(func=self.set_cb, org_key=key, org_value=value, org_cb=cb))
        elif cb:
            async.DelayedCall(0, cb, key=key, value=calvinresponse.CalvinResponse(True))

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

        if prefix + key in self.localstore:
            value = self.localstore[prefix + key]
            async.DelayedCall(0, cb, key=key, value=value)
        else:
            try:
                self.storage.get(key=prefix + key, cb=CalvinCB(func=self.get_cb, org_cb=cb, org_key=key))
            except:
                if self.started:
                    _log.error("Failed to get: %s" % key)
                async.DelayedCall(0, cb, key=key, value=calvinresponse.CalvinResponse(calvinresponse.NOT_FOUND))

    def get_iter_cb(self, key, value, it, org_key, include_key=False):
        """ get callback
        """
        _log.analyze(self.node.id, "+ BEGIN", {'value': value, 'key': org_key})
        if calvinresponse.isnotfailresponse(value):
            it.append((key, value) if include_key else value)
            _log.analyze(self.node.id, "+", {'value': value, 'key': org_key})
        else:
            _log.analyze(self.node.id, "+", {'value': 'FailedElement', 'key': org_key})
            it.append((key, dynops.FailedElement) if include_key else dynops.FailedElement)

    def get_iter(self, prefix, key, it, include_key=False):
        """ Get single value for registry key: prefix+key,
            first look in locally set but not yet distributed registry.
            It is assumed that the prefix and key are strings,
            the sum has to be an immutable object.
            Value is placed in supplied dynamic iterable it parameter.
            The dynamic iterable are of a subclass to calvin.utilities.dynops.DynOps
            that supports the append function call (currently only List), see DynOps
            for details of how they are used. It is common to call auto_final method
            with parameter max_length to number of get_iter calls.
            If a key is not found the special value dynops.FailedElement is put in the
            iterable. When the parameter include_key is True a tuple of (key, value)
            is placed in it instead of only the retrived value,
            note that the key here is without the prefix.
            Value is False when value has been deleted and
            None if never set (this is current behaviour and might change).
        """
        if it:
            if prefix + key in self.localstore:
                value = self.localstore[prefix + key]
                _log.analyze(self.node.id, "+", {'value': value, 'key': key})
                it.append((key, value) if include_key else value)
            else:
                try:
                    self.storage.get(key=prefix + key,
                                     cb=CalvinCB(func=self.get_iter_cb, it=it, org_key=key, include_key=include_key))
                except:
                    if self.started:
                        _log.analyze(self.node.id, "+", {'value': 'FailedElement', 'key': key})
                        _log.error("Failed to get: %s" % key)
                    it.append((key, dynops.FailedElement) if include_key else dynops.FailedElement)

    def get_concat_cb(self, key, value, org_cb, org_key, local_list):
        """ get callback
        """
        if calvinresponse.isnotfailresponse(value):
            if isinstance(value, (list, tuple, set)):
                org_cb(org_key, list(set(value + local_list)))
            else:
                org_cb(org_key, local_list)
        else:
            org_cb(org_key, local_list)

    def get_concat(self, prefix, key, cb):
        """ Get multiple values for registry key: prefix+key,
            union of locally added but not yet distributed values
            and values added by others.
            It is assumed that the prefix and key are strings,
            the sum has to be an immutable object.
            Callback cb with signature cb(key=key, value=<retrived values>)
            note that the key here is without the prefix.
            Values are returned as a list.

            The registry can be eventually consistent,
            e.g. a removal of a value might only have reached part of a
            distributed registry and hence still be part of returned
            list of values, it may also miss values added by others but
            not yet distributed.
        """
        if not cb:
            return

        if prefix + key in self.localstore_sets:
            _log.analyze(self.node.id, "+ GET LOCAL", None)
            value = self.localstore_sets[prefix + key]
            # Return the set that we intended to append since that's all we have until it is synced
            local_list = list(value['+'])
        else:
            local_list = []
        try:
            self.storage.get_concat(key=prefix + key,
                                    cb=CalvinCB(func=self.get_concat_cb, org_cb=cb, org_key=key, local_list=local_list))
        except:
            if self.started:
                _log.error("Failed to get: %s" % key, exc_info=True)
            async.DelayedCall(0, cb, key=key, value=local_list)

    def append_cb(self, key, value, org_key, org_value, org_cb, silent=False):
        """ append callback, on error retry after flush_timeout
        """
        if value:
            if key in self.localstore_sets:
                if self.localstore_sets[key]['-']:
                    self.localstore_sets[key]['+'] = set([])
                else:
                    del self.localstore_sets[key]
                self.reset_flush_timeout()
        else:
            if not silent:
                _log.warning("Failed to update %s" % key)

        if org_cb:
            org_cb(key=org_key, value=value)
        self.trigger_flush()

    def append(self, prefix, key, value, cb):
        """ Add multiple values value to registry key: prefix+key,
            the stored values are a set, i.e. unordered without duplicates.
            It is assumed that the prefix and key are strings,
            the sum has to be an immutable object.
            value is a list, tuple or set of values.
            Callback cb with signature cb(key=key, value=True/False)
            note that the key here is without the prefix and
            value indicate success.
        """
        _log.debug("Append key %s, value %s" % (prefix + key, value))
        # Keep local storage for sets updated until confirmed
        if (prefix + key) in self.localstore_sets:
            # Append value items
            self.localstore_sets[prefix + key]['+'] |= set(value)
            # Don't remove value items any more
            self.localstore_sets[prefix + key]['-'] -= set(value)
        else:
            self.localstore_sets[prefix + key] = {'+': set(value), '-': set([])}

        if self.started:
            self.storage.append(key=prefix + key, value=list(self.localstore_sets[prefix + key]['+']),
                                cb=CalvinCB(func=self.append_cb, org_key=key, org_value=value, org_cb=cb))
        else:
            if cb:
                cb(key=key, value=calvinresponse.CalvinResponse(True))

    def remove_cb(self, key, value, org_key, org_value, org_cb, silent=False):
        """ remove callback, on error retry after flush_timeout
        """
        if value:
            if key in self.localstore_sets:
                if self.localstore_sets[key]['+']:
                    self.localstore_sets[key]['-'] = set([])
                else:
                    del self.localstore_sets[key]
            self.reset_flush_timeout()
        else:
            if not silent:
                _log.warning("Failed to update %s" % key)

        if org_cb:
            org_cb(key=org_key, value=value)
        self.trigger_flush()

    def remove(self, prefix, key, value, cb):
        """ Remove multiple values value from registry key: prefix+key,
            the stored values are a set, i.e. unordered without duplicates.
            It is assumed that the prefix and key are strings,
            the sum has to be an immutable object.
            value is a list, tuple or set of values.
            Callback cb with signature cb(key=key, value=True/False)
            note that the key here is without the prefix and
            value indicate success.
        """
        _log.debug("Remove key %s, value %s" % (prefix + key, value))
        # Keep local storage for sets updated until confirmed
        if (prefix + key) in self.localstore_sets:
            # Don't append value items any more
            self.localstore_sets[prefix + key]['+'] -= set(value)
            # Remove value items
            self.localstore_sets[prefix + key]['-'] |= set(value)
        else:
            self.localstore_sets[prefix + key] = {'+': set([]), '-': set(value)}

        if self.started:
            self.storage.remove(key=prefix + key, value=list(self.localstore_sets[prefix + key]['-']),
                                cb=CalvinCB(func=self.remove_cb, org_key=key, org_value=value, org_cb=cb))
        else:
            if cb:
                cb(key=key, value=calvinresponse.CalvinResponse(True))

    def delete(self, prefix, key, cb):
        """ Delete registry key: prefix+key
            It is assumed that the prefix and key are strings,
            the sum has to be an immutable object.
            This is equivalent to set(..., value=None, ...).
            Callback cb with signature cb(key=key, value=True/False)
            note that the key here is without the prefix and
            value indicate success.
        """
        _log.debug("Deleting key %s" % prefix + key)
        if prefix + key in self.localstore:
            del self.localstore[prefix + key]
        if (prefix + key) in self.localstore_sets:
            del self.localstore_sets[prefix + key]
        if self.started:
            self.storage.delete(prefix + key, cb)
        else:
            if cb:
                cb(key, calvinresponse.CalvinResponse(True))

    def _index_strings(self, index, root_prefix_level):
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

    def add_index_cb(self, value, org_value, org_cb, index_items, silent=False):
        _log.debug("add index cb value:%s, index_items:%s" % (value, index_items))
        key = tuple(index_items)
        if value:
            # Success
            if key in self.localstore_sets:
                self.localstore_sets[key]['+'] -= set(org_value)
                if not self.localstore_sets[key]['-'] and not self.localstore_sets[key]['+']:
                    del self.localstore_sets[key]
                self.reset_flush_timeout()
        else:
            if not silent:
                _log.warning("Failed to update %s" % key)

        if org_cb:
            org_cb(value=value)
        self.trigger_flush()

    def add_index(self, index, value, root_prefix_level=2, cb=None):
        """
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
        indexes = self._index_strings(index, root_prefix_level)
        # For local cache storage make the indexes the key
        key = tuple(indexes)
        # Make sure we send in a list as value
        value = list(value) if isinstance(value, (list, set, tuple)) else [value]

        if key in self.localstore_sets:
            # Append value items
            self.localstore_sets[key]['+'] |= set(value)
            # Don't remove value items any more
            self.localstore_sets[key]['-'] -= set(value)
        else:
            self.localstore_sets[key] = {'+': set(value), '-': set([])}

        if self.started:
            self.storage.add_index(prefix="index-", indexes=indexes, value=value,
                cb=CalvinCB(self.add_index_cb, org_cb=cb, index_items=indexes, org_value=value))
        elif cb:
            cb(value=calvinresponse.CalvinResponse(True))

    def remove_index_cb(self, value, org_value, org_cb, index_items, silent=False):
        _log.debug("remove index cb value:%s, index_items:%s" % (value, index_items))
        key = tuple(index_items)
        if value:
            # Success
            if key in self.localstore_sets:
                self.localstore_sets[key]['-'] -= set(org_value)
                if not self.localstore_sets[key]['-'] and not self.localstore_sets[key]['+']:
                    del self.localstore_sets[key]
                self.reset_flush_timeout()
        else:
            if not silent:
                _log.warning("Failed to update %s" % key)

        if org_cb:
            org_cb(value=value)
        self.trigger_flush()

    def remove_index(self, index, value, root_prefix_level=2, cb=None):
        """
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
        indexes = self._index_strings(index, root_prefix_level)
        # For local cache storage make the indexes the key
        key = tuple(indexes)
        # Make sure we send in a list as value
        value = list(value) if isinstance(value, (list, set, tuple)) else [value]

        if key in self.localstore_sets:
            # Remove value items
            self.localstore_sets[key]['+'] -= set(value)
            # Do remove value items
            self.localstore_sets[key]['-'] |= set(value)
        else:
            self.localstore_sets[key] = {'+': set([]), '-': set(value)}

        if self.started:
            self.storage.remove_index(prefix="index-", indexes=indexes, value=value,
                cb=CalvinCB(self.remove_index_cb, org_cb=cb, index_items=indexes, org_value=value))
        elif cb:
            cb(value=calvinresponse.CalvinResponse(True))

    def delete_index(self, index, root_prefix_level=2, cb=None):
        """
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
                _log.warning("Failed to find %s" % "/".join(index_items))

        if org_cb:
            org_cb(value=list(value))

    def get_index(self, index, root_prefix_level=2, cb=None):
        """
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
        indexes = self._index_strings(index, root_prefix_level)
        # Collect a value set from all key-indexes that include the indexes, always compairing full index levels
        local_values = set(itertools.chain(
            *(v['+'] for k, v in self.localstore_sets.items()
                if all(map(lambda x, y: False if x is None else True if y is None else x==y, k, indexes)))))
        if self.started:
            self.storage.get_index(prefix="index-", index=indexes,
                cb=CalvinCB(self.get_index_cb, org_cb=cb, index_items=indexes, local_values=local_values))
        elif cb:
            cb(value=list(local_values))

    def get_index_iter_cb(self, value, it, org_key, include_key=False):
        _log.debug("get index iter cb key: %s value: %s" % (org_key, value))
        if calvinresponse.isnotfailresponse(value):
            it.extend([(org_key, v) for v in value] if include_key else value)
        it.final()

    def get_index_iter(self, index, include_key=False, root_prefix_level=2):
        """
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
            calvin.utilities.dynops.DynOps, see DynOps for details
            of how they are used. The final method will be called when
            all values are appended to the returned dynamic iterable.
        """
        _log.debug("get index iter %s" % (index))
        indexes = self._index_strings(index, root_prefix_level)
        org_key = "/".join(indexes)
        # TODO push also iterable into plugin?
        it = dynops.List()
        self.get_index(index=index, root_prefix_level=root_prefix_level,
            cb=CalvinCB(self.get_index_iter_cb, it=it, include_key=include_key, org_key=org_key))
        return it

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
        GlobalStore(node=node, security=Security(node) if security_enabled() else None, verify=False).export()
        # If node is an authentication server, store information about it in storage
        _sec_conf = _conf.get('security', 'security_conf')
        if _sec_conf and 'authentication' in _sec_conf:
            if ('accept_external_requests' in _sec_conf['authentication'] and
                    _sec_conf['authentication']['accept_external_requests'] ):
                _log.debug("Node is an authentication server accepting external requests, list it in storage")
                #Add node to list of authentication servers accepting external clients
                self.add_index(['external_authentication_server'], node.id,
                               root_prefix_level=1, cb=cb)
                #Add node to list of authentication servers
                self.add_index(['authentication_server'], node.id,
                               root_prefix_level=1, cb=cb)
            elif ('procedure' in _sec_conf['authentication'] and
                        _sec_conf['authentication']['procedure']=='local' ):
                _log.debug("Node is a local authentication server NOT accepting external requests, there is no reason to store that information in storage")
            else:
                _log.debug("Node is NOT an authentication server")
        # If node is an authorization server, store information about it in storage
        if _sec_conf and 'authorization' in _sec_conf:
            if ('accept_external_requests' in _sec_conf['authorization'] and
                    _sec_conf['authorization']['accept_external_requests'] ):
                _log.debug("Node is an authorization server accepting external requests, list it in storage")
                #Add node to list of authorization servers accepting external clients
                self.add_index(['external_authorization_server'], node.id,
                               root_prefix_level=1, cb=cb)
                #Add node to list of authorization servers
                self.add_index(['authorization_server'], node.id,
                               root_prefix_level=1, cb=cb)
            elif ('procedure' in _sec_conf['authorization'] and
                        _sec_conf['authorization']['procedure']=='local' ):
                _log.debug("Node is a local authorization server NOT accepting external requests, list it in storage")
                #Add node to list of authorization servers
                self.add_index(['authorization_server'], node.id, root_prefix_level=1, cb=cb)
            else:
                _log.debug("Node is NOT an authorization server")
        #Store runtime certificate in storage
        certstring = self._get_runtime_certificate(node)
        if certstring:
            self.node.storage.add_index(['certificate',node.id], certstring, root_prefix_level=2, cb=cb)

    def _get_runtime_certificate(self, node):
        from calvin.utilities.runtime_credentials import RuntimeCredentials
        try:
            rt_cred = RuntimeCredentials(node.node_name)
            certpath, cert, certstr = rt_cred.get_own_cert()
            return certstr
        except Exception as err:
            _log.debug("No runtime credentials, err={}".format(err))
            return None

    def _add_super_node(self, node):
        """ The term super node is to list runtimes that are more capable/central than others.
            Currently it will contain calvin-base runtimes not using proxy storage,
            but this might change to include other criteria, like computational power,
            steady/temporary, etc.
            We will have 4 classes: 0-3 with class 3 most super.
            It is possible to search for a class or higher
        """
        if self.proxy is not None:
            node.super_node_class = 1
        else:
            node.super_node_class = 0
        self.add_index(['supernode'] + map(str, range(node.super_node_class + 1)), node.id, root_prefix_level=1)

    def _remove_super_node(self, node):
        if node.super_node_class is not None:
            self.remove_index(['supernode'] + map(str, range(node.super_node_class + 1)), node.id, root_prefix_level=1)

    def get_super_node(self, super_node_class, cb):
        self.get_index(['supernode'] + map(str, range(super_node_class + 1)), root_prefix_level=1, cb=cb)

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
        _sec_conf = _conf.get('security', 'security_conf')
        if _sec_conf and ('authorization' in _sec_conf):
            if ('accept_external_requests' in _sec_conf['authorization'] and
                    _sec_conf['authorization']['accept_external_requests'] ):
                #Remove node from list of authorization servers accepting external clients
                self.remove_index(['external_authorization_server', 'nodes'], self.node.id, root_prefix_level=2, cb=cb)
                #Remove node from list of authorization servers
                self.add_index(['authorization_server'], self.node.id, root_prefix_level=1, cb=cb)
            elif ('procedure' in _sec_conf['authorization'] and
                        _sec_conf['authorization']['procedure']=='local' ):
                #Remove node from list of authorization servers
                self.remove_index(['authorization_server'], self.node.id, root_prefix_level=1, cb=cb)

    def _delete_node_index(self, node, cb=None):
        indexes = node.attributes.get_indexed_public()
        _log.analyze(self.node.id, "+", {'indexes': indexes})
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
        _log.debug("Add application %s id %s" % (application.name, application.id))

        self.set(prefix="application-", key=application.id,
                 value={"name": application.name,
                        "ns": application.ns,
                        # FIXME when all users of the actors field is updated, save the full dict only
                        "actors": application.actors.keys(),
                        "actors_name_map": application.actors,
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
        # TODO need to store app-id
        _log.debug("Add actor %s id %s" % (actor, node_id))
        data = {"name": actor.name, "type": actor._type, "node_id": node_id}
        inports = []
        for p in actor.inports.values():
            port = {"id": p.id, "name": p.name}
            inports.append(port)
            self.add_port(p, node_id, actor.id)
        data["inports"] = inports
        outports = []
        for p in actor.outports.values():
            port = {"id": p.id, "name": p.name}
            outports.append(port)
            self.add_port(p, node_id, actor.id)
        data["outports"] = outports
        data["is_shadow"] = isinstance(actor, ShadowActor)
        if actor._replication_id.id is not None:
            data["replication_id"] = actor._replication_id.id
            data["replication_master_id"] = actor._replication_id.original_actor_id
            data["replication_index"] = actor._replication_id.index
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
        self.delete_actor_requirements(actor_id)
        try:
            replication_id = self.node.am.actors[actor_id]._replication_id.id
            if replication_id is None or self.node.am.actors[actor_id]._replication_id.original_actor_id == actor_id:
                return
            self.remove_replica(replication_id, actor_id)
            self.remove_replica_node(replication_id, actor_id)
        except:
            pass

    def add_actor_requirements(self, actor, cb=None):
        self.set(prefix="actorreq-", key=actor.id, value=actor.requirements_get(), cb=cb)

    def get_actor_requirements(self, actor_id, cb=None):
        self.get(prefix="actorreq-", key=actor_id, cb=cb)

    def delete_actor_requirements(self, actor_id, cb=None):
        self.delete(prefix="actorreq-", key=actor_id, cb=cb)

    def add_port(self, port, node_id, actor_id=None, exhausting_peers=None, cb=None):
        """
        Add port to storage
        """
        if actor_id is None:
            actor_id = port.owner.id

        data = {"name": port.name, "connected": port.is_connected(),
                "node_id": node_id, "actor_id": actor_id, "properties": port.properties}
        if port.is_connected():
            if exhausting_peers is None:
                exhausting_peers = []
            data["peers"] = [peer for peer in port.get_peers() if peer[1] not in exhausting_peers]
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

    def add_replica(self, replication_id, actor_id, node_id=None, cb=None):
        _log.analyze(self.node.id, "+", {'replication_id':replication_id, 'actor_id':actor_id})
        self.add_index(['replicas', 'actors', replication_id], actor_id, root_prefix_level=3, cb=cb)
        self.add_index(['replicas', 'nodes', replication_id],
                        self.node.id if node_id is None else node_id, root_prefix_level=3, cb=cb)

    def remove_replica(self, replication_id, actor_id, cb=None):
        _log.analyze(self.node.id, "+", {'replication_id':replication_id, 'actor_id':actor_id})
        self.remove_index(['replicas', 'actors', replication_id], actor_id, root_prefix_level=3, cb=cb)

    def remove_replica_node(self, replication_id, actor_id, cb=None):
        # Only remove the node if we are last
        if replication_id is None:
            return
        replica_ids = self.node.rm.list_replication_actors(replication_id)
        _log.debug("remove_replica_node %s %s" % (actor_id, replica_ids))
        try:
            replica_ids.remove(actor_id)
            replica_ids.remove(self.node.am.actors[actor_id]._replication_id.original_actor_id)
        except:
            pass
        if not replica_ids:
            _log.debug("remove_replica_node remove %s %s" % (self.node.id, actor_id))
            self.remove_index(['replicas', 'nodes', replication_id], self.node.id, root_prefix_level=3, cb=cb)

    def remove_replica_node_force(self, replication_id, node_id, cb=None):
        if replication_id is None:
            return
        _log.debug("remove_replica_node_force remove %s" % node_id)
        self.remove_index(['replicas', 'nodes', replication_id], node_id, root_prefix_level=3, cb=cb)

    def get_replica(self, replication_id, cb=None):
        self.get_index(['replicas', 'actors', replication_id], root_prefix_level=3, cb=cb)

    def get_replica_nodes(self, replication_id, cb=None):
        self.get_index(['replicas', 'nodes', replication_id], root_prefix_level=3, cb=cb)

    def set_replication_data(self, replication_data, cb=None):
        """ Save the replication data state any replica instances are stored seperate continously """
        state = replication_data.state()
        state.pop('instances', None)
        self.set(prefix="replicationdata-", key=replication_data.id, value=state, cb=cb)

    def delete_replication_data(self, replication_id, cb=None):
        """ Delete the replication id """
        self.delete(prefix="replicationdata-", key=replication_id, cb=cb)

    def get_replication_data(self, replication_id, cb=None):
        """ Get replication data """
        self.get(prefix="replicationdata-", key=replication_id, cb=cb)

    def get_full_replication_data(self, replication_id, cb=None):
        """ Get replication data as well as the replica instances """
        state = {}
        def _rd_cb(key, value):
            if calvinresponse.isnotfailresponse(value):
                try:
                    state.update(value)
                except:
                    state['id'] = calvinresponse.CalvinResponse(False)
            else:
                state['id'] = value
            if 'instances' in state:
                # Got both main data and instances
                if calvinresponse.isnotfailresponse(value):
                    state['instances'].append(state['original_actor_id'])
                    cb(key=replication_id, value=state)
                else:
                    cb(key=replication_id, value=value)

        def _rd_instances_cb(value):
            state['instances'] = value
            if 'id' in state:
                # Got both main data and instances
                if calvinresponse.isnotfailresponse(state['id']):
                    state['instances'].append(state['original_actor_id'])
                    cb(key=replication_id, value=state)
                else:
                    cb(key=replication_id, value=state['id'])

        self.get(prefix="replicationdata-", key=replication_id, cb=None if cb is None else _rd_cb)
        self.get_replica(replication_id, cb=None if cb is None else _rd_instances_cb)

    ### Storage proxy server ###

    def tunnel_request_handles(self, tunnel):
        """ Incoming tunnel request for storage proxy server"""
        # TODO check if we want a tunnel first
        _log.analyze(self.node.id, "+ SERVER", {'tunnel_id': tunnel.id})
        self.tunnel[tunnel.peer_node_id] = tunnel
        tunnel.register_tunnel_down(CalvinCB(self.tunnel_down, tunnel))
        tunnel.register_tunnel_up(CalvinCB(self.tunnel_up, tunnel))
        tunnel.register_recv(CalvinCB(self.tunnel_recv_handler, tunnel))
        # We accept it by returning True
        return True

    def tunnel_down(self, tunnel):
        """ Callback that the tunnel is not accepted or is going down """
        _log.analyze(self.node.id, "+ SERVER", {'tunnel_id': tunnel.id})
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def tunnel_up(self, tunnel):
        """ Callback that the tunnel is working """
        _log.analyze(self.node.id, "+ SERVER", {'tunnel_id': tunnel.id})
        # We should always return True which sends an ACK on the destruction of the tunnel
        return True

    def _proxy_reply(self, cb, *args, **kwargs):
        # Should not get any replies to the server but log it just in case
        _log.analyze(self.node.id, "+ SERVER", {args: args, 'kwargs': kwargs})

    def tunnel_recv_handler(self, tunnel, payload):
        """ Gets called when a storage client request"""
        _log.debug("Storage proxy request %s" % payload)
        _log.analyze(self.node.id, "+ SERVER", {'payload': payload})
        if 'cmd' in payload and payload['cmd'] in self._proxy_cmds:
            # Call this nodes storage methods, which could be local or DHT,
            # prefix is empty since that is already in the key (due to these calls come from the storage plugin level).
            kwargs = {k: v for k, v in payload.iteritems() if k in ('key', 'value', 'prefix', 'index')}
            kwargs.setdefault('prefix', "")
            if payload['cmd'].endswith("_INDEX"):
                kwargs.pop('prefix')
                kwargs['root_prefix_level'] = 0
                dummykey = {'key': None}
            else:
                dummykey = {}
            self._proxy_cmds[payload['cmd']](cb=CalvinCB(self._proxy_send_reply, tunnel=tunnel,
                                                         msgid=payload['msg_uuid'], **dummykey), **kwargs)
        else:
            _log.error("Unknown storage proxy request %s" % payload['cmd'] if 'cmd' in payload else "")

    def _proxy_send_reply(self, key, value, tunnel, msgid):
        _log.analyze(self.node.id, "+ SERVER", {'msgid': msgid, 'key': key, 'value': value})
        # When a CalvinResponse send it on key 'response' instead of 'value'
        status = isinstance(value, calvinresponse.CalvinResponse)
        svalue = value.encode() if status else value
        response = 'response' if status else 'value'
        kwargs = {'cmd': 'REPLY', 'msg_uuid': msgid, response: svalue}
        if key is not None:
            kwargs['key'] = key
        tunnel.send(kwargs)
