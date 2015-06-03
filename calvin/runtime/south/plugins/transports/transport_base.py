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


class TransportServerBase(object):
    def __init__(self, *args, **kwargs):
        pass

    def start(self, client_callback=None):
        """
            Starts the server.
            client_callback is a function taking a TransportBase
            when a client is connecting.
        """
        pass

    def stop(self):
        """
            Stops server.
        """
        pass


class TransportBase(object):

    def __init__(self, *args, **kwargs):
        pass

    def disconnect(self):
        pass

    def send(self, data):
        pass

    def join(self, uri):
        pass

    # Callbacks
    def onconnection_made(self):
        pass

    def onconnection_lost(self):
        pass

    def on_data(self):
        pass
