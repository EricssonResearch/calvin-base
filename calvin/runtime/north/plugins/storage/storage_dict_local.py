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

from calvin.runtime.south.async import async
from calvin.requests import calvinresponse
import itertools

class StorageLocal(object):
    """
        This is used for tests without full runtimes, does not work
        for full runtimes!

        All functions in this class should be async and never block

        All functions takes a callback parameter:
            cb:  The callback function/object thats callaed when request is done

        The callback is as follows:
            start/stop:
                status: True or False
            set:
                key: The key set
                status: True or False
            get:
                key: The key
                value: The returned value
            append:
                key: The key
                status: True or False
            bootstrap:
                status: List of True and/or false:s

    """
    def __init__(self, node=None):
        self._data = {}

    def _dummy_cb(self, *args, **kwargs):
        pass

    def start(self, iface='', network='', bootstrap=[], cb=None, name=None, nodeid=None):
        """
            Starts the service if its nneeded for the storage service
            cb  is the callback called when the srtart is finished
        """
        cb = cb or self._dummy_cb
        async.DelayedCall(0, cb, True)

    def set(self, key, value, cb=None):
        """
            Set a key, value pair in the storage
        """
        cb = cb or self._dummy_cb
        self._data[key] = value
        async.DelayedCall(0, cb, key, calvinresponse.CalvinResponse(True))

    def get(self, key, cb=None):
        """
            Gets a value from the storage
        """
        cb = cb or self._dummy_cb
        if key in self._data:
            async.DelayedCall(0, cb, key, self._data[key])
        else:
            async.DelayedCall(0, cb, key, calvinresponse.CalvinResponse(calvinresponse.NOT_FOUND))

    def delete(self, key, cb=None):
        cb = cb or self._dummy_cb
        del self._data[key]
        async.DelayedCall(0, cb, key, calvinresponse.CalvinResponse(True))

    def get_concat(self, key, cb=None):
        """
            Gets a value from the storage
        """
        cb = cb or self._dummy_cb
        if key in self._data and isinstance(self._data[key], set):
            async.DelayedCall(0, cb, key, list(self._data[key]))
        else:
            async.DelayedCall(0, cb, key, calvinresponse.CalvinResponse(calvinresponse.NOT_FOUND))

    def append(self, key, value, cb=None):
        cb = cb or self._dummy_cb
        if key in self._data and isinstance(self._data[key], set):
            self._data[key] |= set(value)
            async.DelayedCall(0, cb, key, calvinresponse.CalvinResponse(True))
            return
        self._data[key] = set(value)
        async.DelayedCall(0, cb, key, calvinresponse.CalvinResponse(True))

    def remove(self, key, value, cb=None):
        cb = cb or self._dummy_cb
        if key in self._data and isinstance(self._data[key], set):
            self._data[key] -= set(value)
            async.DelayedCall(0, cb, key, calvinresponse.CalvinResponse(True))
            return
        del self._data[key]
        async.DelayedCall(0, cb, key, calvinresponse.CalvinResponse(True))

    def add_index(self, prefix, indexes, value, cb=None):
        cb = cb or self._dummy_cb
        indexes = [prefix] + indexes
        key = tuple(indexes)
        if key in self._data and isinstance(self._data[key], set):
            self._data[key] |= set(value)
            async.DelayedCall(0, cb, calvinresponse.CalvinResponse(True))
            return
        self._data[key] = set(value)
        async.DelayedCall(0, cb, calvinresponse.CalvinResponse(True))

    def remove_index(self, prefix, indexes, value, cb=None):
        cb = cb or self._dummy_cb
        indexes = [prefix] + indexes
        key = tuple(indexes)
        if key in self._data and isinstance(self._data[key], set):
            self._data[key] -= set(value)
            async.DelayedCall(0, cb, calvinresponse.CalvinResponse(True))
            return
        del self._data[key]
        async.DelayedCall(0, cb, calvinresponse.CalvinResponse(True))

    def get_index(self, prefix, index, cb=None):
        cb = cb or self._dummy_cb
        index = [prefix] + index
        # Collect a value set from all key-indexes that include the indexes, always compairing full index levels
        values = set(itertools.chain(
            *(v for k, v in self._data.items()
                if all(map(lambda x, y: False if x is None else True if y is None else x==y, k, index)))))
        async.DelayedCall(0, cb, list(values))

    def bootstrap(self, addrs, cb=None):
        cb = cb or self._dummy_cb
        async.DelayedCall(0, cb, True)

    def stop(self, cb=None):
        cb = cb or self._dummy_cb
        async.DelayedCall(0, cb, True)
