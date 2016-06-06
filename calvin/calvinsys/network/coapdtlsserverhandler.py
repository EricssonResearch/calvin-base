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

from calvin.runtime.south.plugins.async.twistedimpl.coapdtls_server import CoAPServer

from calvin.utilities.calvinlogger import get_logger

import threading

_log = get_logger(__name__)

class Server(object):
    def __init__(self):
        super(Server, self).__init__()
    
    def start(self, host, port):
        self._server = CoAPServer(host, port)
	serverthread = threading.Thread(target=self._server.start)
	serverthread.daemon = True
	serverthread.start()

    def stop(self):
        self._server.stop()

    def get_data(self):
        return self._server.get_data()

    def data_available(self):
        return self._server.data_available()

def register(node, actor):
    return Server()
