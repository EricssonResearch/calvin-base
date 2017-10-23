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



class StorageBase(object):
    """
        Base class for implementing storage plugins.
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
        pass

    def start(self, iface='', network='', bootstrap=[], cb=None):
        """
            Starts the service if its nneeded for the storage service
            cb  is the callback called when the srtart is finished
        """
        raise NotImplementedError()

    def set(self, key, value, cb=None):
        """
            Set a key, value pair in the storage
        """
        raise NotImplementedError()

    def get(self, key, cb=None):
        """
            Gets a value from the storage
        """
        raise NotImplementedError()

    def delete(self, key, cb=None):
        """
            Delete a value from the storage
        """
        raise NotImplementedError()

    def get_concat(self, key, cb=None):
        """
            Gets a value from the storage
        """
        raise NotImplementedError()

    def append(self, key, value, cb=None):
        raise NotImplementedError()

    def remove(self, key, value, cb=None):
        raise NotImplementedError()

    def add_index(self, prefix, indexes, value, cb=None):
        raise NotImplementedError()

    def remove_index(self, prefix, indexes, value, cb=None):
        raise NotImplementedError()

    def get_index(self, prefix, index, cb=None):
        raise NotImplementedError()

    def bootstrap(self, addrs, cb=None):
        raise NotImplementedError()

    def stop(self, cb=None):
        raise NotImplementedError()
