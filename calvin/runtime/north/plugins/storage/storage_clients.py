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

import itertools
import re

from storage_base import StorageBase
from calvin.requests import calvinresponse
from calvin.requests.request_handler import RequestBase
from calvin.runtime.south.async import async
from proxy_client import ProxyRegistryClient

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

def registry(kind, node, host):
    all_kinds = {
        'debug': DebugRegistryClient,
        'rest': RESTRegistryClient,
        'proxy': ProxyRegistryClient,
    }
    class_ = all_kinds.get(kind.lower())
    if not class_:
        raise ValueError("Unknown registry type '{}', must be one of: {}".format(kind, ",".join(all_kinds.keys())))
    print "Instantiating {}({}, {})".format(class_.__name__, node, host)   
    return class_(node, host)        
                

class RESTRegistryClient(StorageBase):
    '''arg: host = "http://localhost:4998"'''
    from requests_futures.sessions import FuturesSession
    session = FuturesSession(max_workers=10)
    
    def __init__(self, node, host):
        # UNUSED: node
        super(RESTRegistryClient, self).__init__()
        self.host = "http://localhost:4998"
        self.futures = []

    def barrier(self):
        from concurrent.futures import wait
        wait(self.futures, timeout=5)
    
    def _request(self, op, path, data=None, cb=None):
        uri = self.host + path
        if op == 'post':
            f = self.session.post(uri, json=data)
        elif op == 'get':
            f = self.session.get(uri)
        elif op == 'delete':
            f = self.session.delete(uri)
        else:
            raise ValueError("Operation must be one of 'get', 'post', or 'delete'")
        self.futures.append(f)
        if cb:
            f.add_done_callback(cb)
        
    def _post(self, path, data, cb):
        self._request('post', path, data, cb)
        
    def _get(self, path, cb):
        self._request('get', path, cb=cb)
    
    def _delete(self, path, cb):
        self._request('delete', path, cb=cb)
    
    def start(self, cb):
        cb.args_append(True)
        cb()
        
    def set(self, key, value, cb):
        # cb is CalvinCallback(func=cb, org_key=key, org_value=value, org_cb=cb)
        def _response_cb(f):
            resp = f.result()
            cb(key=key, value=calvinresponse.CalvinResponse(resp.status_code))
        path = '/storage/'+key
        data = {'value':value} 
        self._post(path, data, _response_cb)
        
    def get(self, key, cb):
        def _response_cb(f):
            resp = f.result()
            value = resp.json() if resp.status_code == 200 else calvinresponse.CalvinResponse(resp.status_code)
            cb(key=key, value=value)
        path = '/storage/'+key
        self._get(path, _response_cb)
                
    def delete(self, key, cb):
        def _response_cb(f):
            resp = f.result()
            cb(key=key, value=calvinresponse.CalvinResponse(resp.status_code))
        path = '/storage/'+key
        self._delete(path, _response_cb)
        
    
    def add_index(self, indexes, value, cb):
        if not isinstance(indexes, (list, set, tuple)):
            raise TypeError("Argument 'indexes' is not list, set, or tuple")
        path = '/add_index/'
        data = {
            'indexes': indexes,
            'value': value,
        } 
        def _response_cb(f):
            resp = f.result()
            cb(value=calvinresponse.CalvinResponse(resp.status_code))
        self._post(path, data, _response_cb)
        
            
    def remove_index(self, indexes, value, cb):
        if not isinstance(indexes, (list, set, tuple)):
            raise TypeError("Argument 'indexes' is not list, set, or tuple")
        path = '/remove_index/'
        data = {
            'indexes': indexes,
            'value': value,
        } 
        def _response_cb(f):
            resp = f.result()
            cb(value=calvinresponse.CalvinResponse(resp.status_code))
        self._post(path, data, _response_cb)
            

    def get_index(self, indexes, cb):
        if not isinstance(indexes, (list, set, tuple)):
            raise TypeError("Argument 'indexes' is not list, set, or tuple")
        path = '/get_index/'
        data = {
            'indexes': indexes,
        } 
        def _response_cb(f):
            resp = f.result()
            value = resp.json() if resp.status_code == 200 else calvinresponse.CalvinResponse(resp.status_code)
            cb(value=value)
        self._post(path, data, _response_cb)
            

class NullRegistryClient(StorageBase):
    """args: - """
    def __init__(self, node=None, host=None):
        # UNUSED: node, host
        super(NullRegistryClient, self).__init__()
        # self.local_mode = storage_type == 'local'

    def barrier(self):
        pass
    
    def start(self, cb):
        # Don't trigger flush
        cb.kwargs['org_key'] = 'placeholder'
        self._response(cb, True)
                
    # def start(self, iface='', name=None, nodeid=None, cb=None):
    #     """
    #         Starts the service if its nneeded for the storage service
    #         cb  is the callback called when the srtart is finished
    #     """
    #     if self.local_mode:
    #         # unwind the CalvinCB and call the original cb
    #         print "LOCAL MODE"
    #         callback = cb.kwargs.get('org_cb')
    #     else:
    #         print "REMOTE MODE"
    #         callback = cb
    #     if callback:
    #         callback(True)
    #         # async.DelayedCall(0, callback, True)
    
    def _response(self, cb, value):
        callback = cb.kwargs.get('org_cb')
        if callback:
            org_key = cb.kwargs['org_key'] 
            callback(key=org_key, value=calvinresponse.CalvinResponse(value))
            # FIXME: Should this be used instead?         
            # async.DelayedCall(0, callback, key=org_key, value=calvinresponse.CalvinResponse(value))        
    
    #
    # Remaining methods will only pass on the callback on behalf of the preceeding LocalStorage operation
    #
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
        
    def add_index(self, indexes, value, cb):
        # From our point of view, add_index always succeeds
        self._response(cb, True)
           
    def remove_index(self, indexes, value, cb):
        # From our point of view, add_index always succeeds
        self._response(cb, True)
    
    def get_index(self, indexes, cb):
        # The result is actually in the callback cb, as is the original callback
        # Strangely, this callback has a different behaviour than the rest...
        callback = cb.kwargs.get('org_cb')
        if callback:
            value = list(cb.kwargs['local_values']) 
            callback(value=value)
        

class LocalRegistry(StorageBase):
    """args: -"""
    def __init__(self, node=None, host=None):
        # UNUSED: node, host 
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
        self.localstore[key] = value
    
    def get(self, key):
        """Return value if found, raise exception otherwise."""
        return self.localstore[key]

    def delete(self, key):
        if key in self.localstore:
            del self.localstore[key]

    def add_index(self, indexes, value):
        if not isinstance(indexes, (list, set, tuple)):
            raise TypeError("Argument 'indexes' is not list, set, or tuple")
        # For local cache storage make the indexes the key
        key = tuple(indexes)
        # Make sure we send in a list as value
        value = list(value) if isinstance(value, (list, set, tuple)) else [value]
        self._append(key, value)
        
    def remove_index(self, indexes, value):
        if not isinstance(indexes, (list, set, tuple)):
            raise TypeError("Argument 'indexes' is not list, set, or tuple")
        # For local cache storage make the indexes the key
        key = tuple(indexes)
        # Make sure we send in a list as value
        value = list(value) if isinstance(value, (list, set, tuple)) else [value]
        self._remove(key, value)

    def get_index(self, indexes):
        if not isinstance(indexes, (list, set, tuple)):
            raise TypeError("Argument 'indexes' is not list, set, or tuple")
        key = tuple(indexes)    
        # Collect a value set from all key-indexes that include the indexes, always compairing full index levels
        local_values = set(itertools.chain(
            *(v['+'] for k, v in self.localstore_sets.items()
                if all(map(lambda x, y: False if x is None else True if y is None else x==y, k, key)))))
        return local_values       
            
## Additional methods
        
    def _append(self, key, value):
        if not isinstance(value, (list, set, tuple)):
            raise TypeError("Argument 'value' is not list, set, or tuple")
        # Keep local storage for sets updated until confirmed
        if key in self.localstore_sets:
            # Append value items
            self.localstore_sets[key]['+'] |= set(value)
            self.localstore_sets[key]['-'] -= set(value)
        else:
            self.localstore_sets[key] = {'+': set(value), '-': set([])}

    def _remove(self, key, value):
        if not isinstance(value, (list, set, tuple)):
            raise TypeError("Argument 'value' is not list, set, or tuple")
        if key in self.localstore_sets:
            self.localstore_sets[key]['+'] -= set(value)
            self.localstore_sets[key]['-'] |= set(value)
        else:
            self.localstore_sets[key] = {'+': set([]), '-': set(value)}

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
            
    
class DebugRegistryClient(LocalRegistry):
    """
    LocalRegistry with callbacks to emulate remote clients
    """
    
    def _response(self, cb, value):
        cb(value=calvinresponse.CalvinResponse(value))
        # FIXME: Should this be used instead?
        # async.DelayedCall(0, callback, key=org_key, value=calvinresponse.CalvinResponse(value))

    def start(self, cb):
        self._response(cb, True)

    def set(self, key, value, cb):
        super(DebugRegistryClient, self).set(key, value)
        self._response(cb, True)

    def get(self, key, cb):
        retval = super(DebugRegistryClient, self).get(key)
        self._response(cb, retval)

    def delete(self, key, cb):
        super(DebugRegistryClient, self).delete(key)
        self._response(cb, True)
        
    def add_index(self, indexes, value, cb):
        super(DebugRegistryClient, self).add_index(indexes, value)
        self._response(cb, True)
        
    def remove_index(self, indexes, value, cb):
        super(DebugRegistryClient, self).remove_index(indexes, value)
        self._response(cb, True)

    def get_index(self, indexes, cb):
        retval = super(DebugRegistryClient, self).get_index(indexes)
        self._response(cb, retval)
        
         
        
        
