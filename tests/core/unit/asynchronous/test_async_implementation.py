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

from calvin.runtime.south import asynchronous


FRAMEWORKS = ["twistedimpl"]

def test_API():
    assert asynchronous.DelayedCall
    assert asynchronous.run_ioloop
    assert asynchronous.stop_ioloop
    assert asynchronous.call_from_thread
    assert asynchronous.call_in_thread
    assert asynchronous.defer_to_thread
    
    assert asynchronous.GenericFileDescriptor
    assert asynchronous.StdInFileDescriptor
    
    assert asynchronous.TCPServer
    assert asynchronous.HTTPServer
    assert asynchronous.UDPServer
    assert asynchronous.TCPClient
    assert asynchronous.UDPClient

    assert asynchronous.EventSource
    
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
    with pytest.raises(AttributeError):    
        foo = asynchronous.LineProtocol
    with pytest.raises(AttributeError):    
        foo = asynchronous.RawDataProtocol
    with pytest.raises(AttributeError): 
        foo = asynchronous.server_connection
    with pytest.raises(AttributeError):    
        foo = asynchronous.filedescriptor
    with pytest.raises(AttributeError):
        foo = asynchronous.threads.call_multiple_in_thread
    with pytest.raises(AttributeError):
        foo = asynchronous.threads           
    with pytest.raises(AttributeError):
        foo = asynchronous.client_connection
    with pytest.raises(AttributeError):
        foo = asynchronous.sse_event_source
    with pytest.raises(AttributeError):
        foo = asynchronous.TCPServerProtocolFactory
    with pytest.raises(AttributeError):
        foo = asynchronous.UDPServerProtocol
    with pytest.raises(AttributeError):
        foo = asynchronous.TCPClientProtocolFactory    
    with pytest.raises(AttributeError):
        foo = asynchronous.UDPClientProtocolFactory
            
            

