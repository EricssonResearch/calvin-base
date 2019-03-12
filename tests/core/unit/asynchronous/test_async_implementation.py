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

"""
    Tests for async frameworks
"""

import pytest

import calvin.runtime.south.asynchronous as asynchronous


FRAMEWORKS = ["twistedimpl"]

def test_API():
    assert asynchronous.DelayedCall
    assert asynchronous.run_ioloop
    assert asynchronous.stop_ioloop
    assert asynchronous.filedescriptor
    assert asynchronous.FD
    assert asynchronous.threads
    assert asynchronous.threads.defer_to_thread
    assert asynchronous.threads.call_multiple_in_thread
    assert asynchronous.server_connection
    assert asynchronous.ServerProtocolFactory
    assert asynchronous.LineProtocol
    assert asynchronous.server_connection.RawDataProtocol
    assert asynchronous.sse_event_source
    assert asynchronous.sse_event_source.EventSource
    assert asynchronous.client_connection
    assert asynchronous.client_connection.UDPClientProtocolFactory
    assert asynchronous.client_connection.TCPClientProtocolFactory    

def test_removed_API():
    with pytest.raises(AttributeError):
        foo = asynchronous.http_client
    with pytest.raises(AttributeError):
        foo = asynchronous.HTTPClient  
    with pytest.raises(AttributeError):
        foo =  asynchronous.pipe
    with pytest.raises(AttributeError):    
        foo =  asynchronous.pipe.Pipe
    with pytest.raises(AttributeError):    
        foo = asynchronous.defer
    with pytest.raises(AttributeError):    
        foo = asynchronous.defer.Deferred
    with pytest.raises(AttributeError):    
        foo = asynchronous.defer.DeferredList
    with pytest.raises(AttributeError):    
        foo = asynchronous.defer.inline_callbacks
    with pytest.raises(AttributeError):    
        foo = asynchronous.defer.maybe_deferred
           
         
    
# def test_deprecated_API():
#     with pytest.deprecated_call():
#         foo = asynchronous.HTTPClient
#     # with pytest.warns(DeprecationWarning):
#     #     foo = asynchronous.HTTPClient
    


