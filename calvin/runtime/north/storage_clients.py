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

class LocalRegistry(StorageBase):
    """docstring for LocalRegistry"""
    def __init__(self):
        super(LocalRegistry, self).__init__()
        self.localstore = {}
        self.localstore_sets = {}
    
    def set(self, key, value, cb=None):
        if key in self.localstore_sets:
            del self.localstore_sets[key]
        self.localstore[key] = value
    
    def get(self, key, cb):
        """Return true if found, false otherwise. Pass value in callback."""
        try:
            value = self.localstore[key]
            async.DelayedCall(0, cb, key=key, value=value)
            return True
        except:
            return False
    
    def get_iter(self, key, it, include_key=False):
        """Return true if found, false otherwise. Append value to it."""
        try:
            value = self.localstore[key]
            it.append((key, value) if include_key else value)
            return True
        except:
            return False
            
    def get_concat(self, key, cb=None):
        """Return list"""
        try:
            value = self.localstore_sets[key]
            # Return the set that we intended to append since that's all we have until it is synced
            return list(value['+'])
        except:
            return []
        
    def append(self, key, value, cb=None):
        # Keep local storage for sets updated until confirmed
        if key in self.localstore_sets:
            # Append value items
            self.localstore_sets[key]['+'] |= set(value)
            # Don't remove value items any more
            self.localstore_sets[key]['-'] -= set(value)
        else:
            self.localstore_sets[key] = {'+': set(value), '-': set([])}
    
    def remove(self, key, value, cb=None):
        if key in self.localstore_sets:
            # Don't append value items any more
            self.localstore_sets[key]['+'] -= set(value)
            # Remove value items
            self.localstore_sets[key]['-'] |= set(value)
        else:
            self.localstore_sets[key] = {'+': set([]), '-': set(value)}
            
    def delete(self, key, cb=None):
        if key in self.localstore:
            del self.localstore[key]
        if key in self.localstore_sets:
            del self.localstore_sets[key]
            
    def get_indices(self, indices):
        # Collect a value set from all key-indexes that include the indexes, always compairing full index levels
        local_values = set(itertools.chain(
            *(v['+'] for k, v in self.localstore_sets.items()
                if all(map(lambda x, y: False if x is None else True if y is None else x==y, k, indices)))))
        return local_values        
        
            
    
        
        
        
                

            
            
            
            
        
            
        
         
        
        
class NullRegistryClient(StorageBase):
    """Implements start only"""
    def __init__(self):
        super(NullRegistryClient, self).__init__()
                
class RegistryClient(StorageBase):
    """Generic client regardless of storage solution"""
    def __init__(self):
        super(RegistryClient, self).__init__()
