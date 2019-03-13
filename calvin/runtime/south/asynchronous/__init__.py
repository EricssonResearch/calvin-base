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
    # Very much used
    from .twistedimpl.asynchronous import DelayedCall
    # north.scheduler
    from .twistedimpl.asynchronous import run_ioloop
    from .twistedimpl.asynchronous import stop_ioloop
    # In various actors
    from .twistedimpl.asynchronous import call_from_thread
    from .twistedimpl.asynchronous import call_in_thread

    # CalvinControl, CalvinControlTunnel, TCPServer
    from .twistedimpl.server_connection import ServerProtocolFactory
    # calvinsys.network.UDPListener
    from .twistedimpl.server_connection import UDPServerProtocol

    # Used to get filedescriptor.FDStdIn in calvinsys.io.filehandler.Stdin.py
    from .twistedimpl.filedescriptor import StdInFileDescriptor
    # calvinsys.io.filehandler
    from .twistedimpl.filedescriptor import GenericFileDescriptor

    # Very much used
    from .twistedimpl.threads import defer_to_thread

    # No need to expose?
    from .twistedimpl import client_connection
    # Used in calvinsys.network.SocketClient.py
    from .twistedimpl.client_connection import TCPClientProtocolFactory
    from .twistedimpl.client_connection import UDPClientProtocolFactory

    # No need to expose?
    from .twistedimpl import sse_event_source 
    # Used in calvinsys.ui.uicalvinsys.py
    from .twistedimpl.sse_event_source import EventSource
else:
    raise AssertionError("Unknown asynchronous implementation: '{}'".format(async_impl))

__all__ = []
