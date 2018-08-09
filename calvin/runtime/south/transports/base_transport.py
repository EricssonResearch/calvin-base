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
from calvin.runtime.north.plugins.coders.messages import message_coder_factory

from calvin.utilities import calvinlogger
from urlparse import urlparse

_log = calvinlogger.get_logger(__name__)

class URI(object):
    def __init__(self, uri):
        self.uri = uri
        scheme_del = uri.index("://")
        port_del = uri.rindex(":")
        self.scheme = uri[0:scheme_del]
        self.hostname = uri[scheme_del + 3:port_del]

        if self.scheme == "calvinfcm":
            # calvinfcm may have : in the device token.
            address = uri[scheme_del+3:]
            port_del = address.index(':')
            self.hostname = address[:port_del]
            self.port = address[port_del+1:]
        elif scheme_del != port_del:
            self.port = int(uri[port_del + 1:len(uri)])
        else:
            self.port = None

    def geturl(self):
        return self.uri

def split_uri(uri):
    return URI(uri)


class BaseTransport(CalvinCBClass):
    """
        Document callbacks also

    """
    def __init__(self, local_id, remote_uri, callbacks):
        """docstring for __init__"""
        super(BaseTransport, self).__init__(callbacks=callbacks)
        # Override the setting of these in subclass
        self._coder = None                     # Active coder set for transport
        self._rtt = 2000                       # round trip time on ms
        self._timeout = self._rtt * 2          # Time out for connect and replys
        self._uri = split_uri(remote_uri)      # get a URI object
        self._rt_id = local_id
        self._remote_rt_id = None

    def connect(self, timeout=2):
        """
            Connectes the transport, will callback when done
        """
        raise NotImplementedError()

    def disconnect(self, timeout=2):
        """
            Disconenctes the transport, will callback when done
        """
        raise NotImplementedError()

    def is_connected(self):
        """
            Returns if the transport is connected

        """
        raise NotImplementedError()

    def get_uri(self):
        """
            Returns the uri for this transport
        """
        return self._uri.geturl()

    def get_rtt(self):
        """
            Return the aproximate rtt for the transport
        """
        return self._rtt

    def get_coder(self):
        """
            Return the current coder used or none if none set
        """
        return self._coder

    def get_coders_prio(self):
        """
            Return priority list of coders for this runtime
        """
        return message_coder_factory.get_prio_list()

    def get_coders(self):
        """
            Return the filtered coders on this transport
                can be a subset of the total in the system.
        """
        coders = {}
        for coder in message_coder_factory.get_prio_list():
            coders[coder] = message_coder_factory.get(coder)
        return coders

    def send(self, payload, timeout=None):
        """
            Send data with a payload to the transport with a timepout
        """
        raise NotImplementedError()


class BaseServer(CalvinCBClass):
    def __init__(self, rt_id, listen_uri, callbacks):
        super(BaseServer, self).__init__(callbacks=callbacks)
        self._rt_id = rt_id
        self._listen_uri = split_uri(listen_uri)      # get a urlparse object

    def start(self):
        """

        """
        raise NotImplementedError()

    def stop(self):
        """

        """
        raise NotImplementedError()

    def is_listening(self):
        """

        """
        raise NotImplementedError()


class BaseTransportFactory(CalvinCBClass):
    def __init__(self, rt_id, callbacks):
        super(BaseTransportFactory, self).__init__(callbacks=callbacks)
        self._rt_id = rt_id

    def join(self, uri):
        """

        """
        raise NotImplementedError()

    def listen(self, uri):
        """

        """
        raise NotImplementedError()

    def stop_listening(self, uri):
        """

        """
        raise NotImplementedError()

def register(_id, node_name, callbacks, schemas, formats):
    return {}
