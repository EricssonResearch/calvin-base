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
        Abstraction for the diffrent frameworks that can be used by the system.

"""

# FIXME: Here we actually need to be able to switch between twisted and asyncio,
#        at least while testing until the asyncio version is feature complete. 

from calvin.common import calvinconfig

_conf = calvinconfig.get()
async_impl = _conf.get('GLOBAL', 'framework')


if async_impl == 'twisted':
    from .twistedimpl import asynchronous
    from .twistedimpl.asynchronous import DelayedCall
    from .twistedimpl.asynchronous import run_ioloop
    from .twistedimpl.asynchronous import stop_ioloop

    from .twistedimpl import server_connection
    from .twistedimpl.server_connection import ServerProtocolFactory
    from .twistedimpl.server_connection import LineProtocol
    from .twistedimpl.server_connection import RawDataProtocol

    from .twistedimpl import filedescriptor
    from .twistedimpl.filedescriptor import FD

    from .twistedimpl import pipe
    from .twistedimpl.pipe import Pipe

    from .twistedimpl import defer
    from .twistedimpl import threads

    from .twistedimpl import client_connection
    from .twistedimpl.client_connection import TCPClientProtocolFactory
    from .twistedimpl.client_connection import UDPClientProtocolFactory

    from .twistedimpl.http_client import HTTPClient

    from .twistedimpl import sse_event_source 
    from .twistedimpl.sse_event_source import EventSource
else:
    pass

__all__ = []
