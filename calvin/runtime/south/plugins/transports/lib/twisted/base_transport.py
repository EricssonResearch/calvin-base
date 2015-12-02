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

from calvin.utilities.calvin_callback import CalvinCBClass
from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)


class CalvinServerBase(CalvinCBClass):
    """
        BaseServerClass for implementing calvinip servers in diffrent frameworks

        Callbacks in the API
            self._callback_execute('server_started', port)
                Called when the server have started listening on the port
                    port is an integer port number of the lisening server
            self._callback_execute('server_stopped')
                Called when the server have stopped listening on the port
            self._callback_execute('client_connected', uri, proto)
                Called when a client is connected
                    uri is the uri that the client connected has example "calvinip://127.0.0.1:78445"
                    proto is the protocol to be sent to the CalvinTransportBase, can be none

    """

    def __init__(self, iface='', port=0, callbacks=None, *args, **kwargs):
        """
        iface   The interface to listen on defaults to all
        port    The port to listen on defaults to system generated
                This port should be returned in the server_started callback
        callbacks   The callbacks subscribed on this class
        """
        super(CalvinServerBase, self).__init__(callbacks, callback_valid_names=['server_started',
                                                                                'server_stopped',
                                                                                'client_connected'])

    def start(self):
        """
            Called when the server transport is started
        """
        raise NotImplementedError()

    def stop(self):
        """
            Called when the server transport is stopped
        """
        raise NotImplementedError()

    def is_listening(self):
        """
            returns if the server is listening
        """
        raise NotImplementedError()


class CalvinTransportBase(CalvinCBClass):
    """
        BaseTransport for implementing calvinip transports in diffrent frameworks

        self._callback_execute('connected')
            Called when the client is connected
        self._callback_execute('disconnected', reason)
            Called when the clinent disconnects
                reason the a string desribing the reason for disconnecting
                    (normal, error, ..)
        self._callback_execute('data', data)
            Called when we have raw data in the transport.
            Always an entire package

    """

    def __init__(self, host, port, callbacks=None, proto=None, *args, **kwargs):
        """
            host        The host address of the client
            port        The port to connect to, 0 means system allocated
            callback    callbacks is a set of callbacks that the client wants
            proto       Can be sent in here if its a connecting client from a server instance

        """
        super(CalvinTransportBase, self).__init__(callbacks, callback_valid_names=['connected', 'disconnected', 'data'])

    def is_connected(self):
        """
            returns True if the transport is connected
        """
        raise NotImplementedError()

    def disconnect(self):
        """
            Used for disconnecting the client
        """
        raise NotImplementedError()

    def send(self, data):
        """
            Used for sending data to the client
                data    Is raw data one package
        """
        raise NotImplementedError()

    def join(self):
        """
            Called when the client should connect
        """
        raise NotImplementedError()
