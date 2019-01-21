# -*- coding: utf-8 -*-

# Copyright (c) 2019 Ericsson AB
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

from calvin.runtime.north.plugins.storage.storage_base import StorageBase
# from calvin.utilities import calvinlogger
from calvin.requests import calvinresponse
from calvin.runtime.south.async import async
import itertools


# _log = calvinlogger.get_logger(__name__)
# _conf = calvinconfig.get()

    
# Define:
 # LocalRegistry() - Always succeeds; returns nothing        
 # NullRegistryClient() - Does nothing except for start; all methods returns False except for start 
 # RegistryClient() - Does the right thing; all methods returns True; start method raises exception
 # All have the same API methods


# General operations:
## Current pattern:
  # # Always save locally
  # self.localstore[prefix + key] = value
  # if self.started:
  #     self.storage.set(key=prefix + key, value=value, cb=CalvinCB(func=self.set_cb, org_key=key, org_value=value, org_cb=cb))
  # elif cb:
  #     async.DelayedCall(0, cb, key=key, value=calvinresponse.CalvinResponse(True))

## Proposed pattern
  # drop self.started
  # initialize self.localstorage to LocalStorage()
  # initialize self.storage to NullClient()
  # in start_cb:
  #   change self.storage to RegistryClient()
  # in normal operations:
  #   self.localstorage.op(args)
  #   self.storage.op(args, nested_callback) or DelayedCall(callback) # might be a NullClient() returning False
  # alternatively:
  #   self.localstorage.op(args)
  #   self.storage.op(args, nested_callback) # NullClient() unwinds nested_callback and calls callback as DelayedCall

class NullRegistryClient(StorageBase):
    """Implements start only"""
    def __init__(self, storage_type):
        super(NullRegistryClient, self).__init__()
        self.local_mode = storage_type == 'local'

    def start(self, iface='', cb=None, name=None, nodeid=None):
        """
            Starts the service if its nneeded for the storage service
            cb  is the callback called when the srtart is finished
        """
        if self.local_mode:
            # unwind the CalvinCB and call the original cb
            print "LOCAL MODE"
            callback = cb.kwargs.get('org_cb')
        else:
            print "REMOTE MODE"
            callback = cb
        if callback:
            callback(True)
            # async.DelayedCall(0, callback, True)
    
    def _response(self, cb, value):
        callback = cb.kwargs.get('org_cb')
        if callback:
            org_key = cb.kwargs['org_key'] 
            callback(key=org_key, value=value)         
            # async.DelayedCall(0, cb, key=org_key, value=calvinresponse.CalvinResponse(True))        
    
    def set(self, key, value, cb):
        # Storing has been handled by the LocalRegistry,
        # cb is CalvinCallback(func=cb, org_key=key, org_value=value, org_cb=cb)
        # Get org_cb and call that:
        self._response(cb, calvinresponse.CalvinResponse(True))

    def get(self, key, cb):
        # Retrieving the value from LocalRegistry has failed, we can't do anything about that
        # cb is CalvinCallback(func=cb, org_key=key, org_value=value, org_cb=cb)
        # Get org_cb (known to exist) and call that with failure response:
        self._response(cb, calvinresponse.CalvinResponse(calvinresponse.NOT_FOUND))
        
    def delete(self, key, cb):
        # From our point of view, delete always succeeds
        self._response(cb, calvinresponse.CalvinResponse(True))

    

class RegistryClient(StorageBase):
    """Generic client regardless of storage solution"""
    def __init__(self):
        super(RegistryClient, self).__init__()


class LocalRegistry(StorageBase):
    """docstring for LocalRegistry"""
    def __init__(self):
        super(LocalRegistry, self).__init__()
        self.localstore = {}
        self.localstore_sets = {}
    
    def set(self, key, value):
        if key in self.localstore_sets:
            del self.localstore_sets[key]
        self.localstore[key] = value
    
    def get(self, key):
        """Return value if found, raise exception otherwise."""
        return self.localstore[key]
    
    def get_iter(self, key, it, include_key=False):
        """Append value to iterator, raise exception if value not found"""
        value = self.localstore[key]
        it.append((key, value) if include_key else value)
            
    def get_concat(self, key):
        """Return list"""
        try:
            value = self.localstore_sets[key]
            # Return the set that we intended to append since that's all we have until it is synced
            return list(value['+'])
        except:
            return []
        
    def append(self, key, value):
        # Keep local storage for sets updated until confirmed
        if key in self.localstore_sets:
            # Append value items
            self.localstore_sets[key]['+'] |= set(value)
            # Don't remove value items any more
            self.localstore_sets[key]['-'] -= set(value)
        else:
            self.localstore_sets[key] = {'+': set(value), '-': set([])}
    
    def remove(self, key, value):
        if key in self.localstore_sets:
            self.localstore_sets[key]['+'] -= set(value)
            self.localstore_sets[key]['-'] |= set(value)
        else:
            self.localstore_sets[key] = {'+': set([]), '-': set(value)}            
            
    def delete(self, key):
        if key in self.localstore:
            del self.localstore[key]
        if key in self.localstore_sets:
            del self.localstore_sets[key]
            
## Additional methods

    def _get_indices(self, indices):
        # Collect a value set from all key-indexes that include the indexes, always compairing full index levels
        local_values = set(itertools.chain(
            *(v['+'] for k, v in self.localstore_sets.items()
                if all(map(lambda x, y: False if x is None else True if y is None else x==y, k, indices)))))
        return local_values        
        
    def _delete_key(self, key):
        if key in self.localstore:
            del self.localstore[key]
        
    def _set_key_value(self, key, value):
        self.localstore[key] = value
        
    def _update_sets(self, key, op1, op2):    
        if key not in self.localstore_sets:
            return   
        if self.localstore_sets[key][op1]:
            self.localstore_sets[key][op2] = set([])
        else:
            del self.localstore_sets[key]

    def _update_sets_add(self, key):
        self._update_sets(key, '-', '+')    
    
    def _update_sets_remove(self, key):    
        self._update_sets(key, '+', '-')    
            
    def _update_sets_index(self, key, value, op):
        if key not in self.localstore_sets:
            return
        self.localstore_sets[key][op] -= set(value)
        if not self.localstore_sets[key]['-'] and not self.localstore_sets[key]['+']:
            del self.localstore_sets[key]

    def _update_sets_add_index(self, key, value):
        self._update_sets_index(key, value, '+')
    
    def _update_sets_remove_index(self, key, value):
        self._update_sets_index(key, value, '-')
                    
    def _setlist(self, key, op):
        return list(self.localstore_sets[key][op])       
            
    
        
        
        
                

            
            
            
            
        
            
        
         
        
        
