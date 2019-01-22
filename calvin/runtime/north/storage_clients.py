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
import re


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

# FIXME: How and when and by whom is this used? Where does it belong?
def index_strings(index, root_prefix_level):
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
            callback(key=org_key, value=calvinresponse.CalvinResponse(value))
            # FIXME: Should this be used instead?         
            # async.DelayedCall(0, callback, key=org_key, value=calvinresponse.CalvinResponse(value))        
    
    def set(self, key, value, cb):
        # Storing has been handled by the LocalRegistry,
        # cb is CalvinCallback(func=cb, org_key=key, org_value=value, org_cb=cb)
        # Get org_cb and call that:
        self._response(cb, True)

    def get(self, key, cb):
        # Retrieving the value from LocalRegistry has failed, we can't do anything about that
        # cb is CalvinCallback(func=cb, org_key=key, org_value=value, org_cb=cb)
        # Get org_cb (known to exist) and call that with failure response:
        self._response(cb, calvinresponse.NOT_FOUND)
        
    def delete(self, key, cb):
        # From our point of view, delete always succeeds
        self._response(cb, True)

    def append(self, key, value, cb):
        # From our point of view, append always succeeds
        self._response(cb, True)
        
    def remove(self, key, value, cb):
        # From our point of view, remove always succeeds
        self._response(cb, True)
        
    def add_index(self, prefix, indexes, value, cb):
        # From our point of view, add_index always succeeds
        self._response(cb, True)
           
    def remove_index(self, prefix, indexes, value, cb):
        # From our point of view, add_index always succeeds
        self._response(cb, True)

    def get_concat(self, key, cb):
        # The result is actually in the callback cb, as is the original callback
        # Strangely, this callback has a different behaviour than the rest...
        callback = cb.kwargs.get('org_cb')
        if callback:
            value = cb.kwargs.get('local_list')
            org_key = cb.kwargs['org_key']
            callback(key=org_key, value=value)
            # async.DelayedCall(0, cb, key=key, value=local_list)
    
    def get_index(self, prefix, indexes, cb):
        # The result is actually in the callback cb, as is the original callback
        # Strangely, this callback has a different behaviour than the rest...
        callback = cb.kwargs.get('org_cb')
        if callback:
            value = list(cb.kwargs['local_values']) 
            callback(value=value)
        
    

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
    
    def dump(self):
        data = [ 
            {str(k): v for k, v in self.localstore.items()},
            {str(k): list(v['+']) for k, v in self.localstore_sets.items()}
        ]
        return data   
            
    def set(self, key, value):
        if key in self.localstore_sets:
            del self.localstore_sets[key]
        self.localstore[key] = value
    
    def get(self, key):
        """Return value if found, raise exception otherwise."""
        return self.localstore[key]
    
    # # FIXME: This might not be required to implement here, see Storage.get_iter
    # def get_iter(self, key, it, include_key=False):
    #     """Append value to iterator, raise exception if value not found"""
    #     value = self.localstore[key]
    #     it.append((key, value) if include_key else value)
            
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

    def add_index(self, indexes, value):
        # For local cache storage make the indexes the key
        key = tuple(indexes)
        # Make sure we send in a list as value
        value = list(value) if isinstance(value, (list, set, tuple)) else [value]
        self.append(key, value)
        
    def remove_index(self, indexes, value):
        # For local cache storage make the indexes the key
        key = tuple(indexes)
        # Make sure we send in a list as value
        value = list(value) if isinstance(value, (list, set, tuple)) else [value]
        self.remove(key, value)   

    def get_index(self, indexes):
        # Collect a value set from all key-indexes that include the indexes, always compairing full index levels
        local_values = set(itertools.chain(
            *(v['+'] for k, v in self.localstore_sets.items()
                if all(map(lambda x, y: False if x is None else True if y is None else x==y, k, indexes)))))
        return local_values       
            
## Additional methods
        
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
            
    
        
        
        
                

            
            
            
            
        
            
        
         
        
        
