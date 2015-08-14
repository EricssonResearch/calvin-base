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

import pytest
import sys
import os
import random
import time
import json
import uuid
import Queue
import multiprocessing
import traceback
#
from mock import Mock
from twisted.internet import reactor

from calvin.utilities import calvinlogger
from calvin.utilities.calvin_callback import CalvinCB, CalvinCBClass
from calvin.runtime.south.plugins.transports.calvinip import calvinip_transport

_log = calvinlogger.get_logger(__name__)


"""
@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    def fin():
        reactor.callFromThread(reactor.stop)
    request.addfinalizer(fin)
    print "hejsan"
"""

class BaseTHandler(multiprocessing.Process):
    def __init__(self, uri, outqueue, inqueue):
        multiprocessing.Process.__init__(self)
        self._item = None
        self._uri = uri
        self._outqueue = outqueue
        self._inqueue = inqueue
        self._running = False

    def set_ttf(self, ttf):
        self._ttf = ttf

    def _return(self, test=False, variables={}, stack=None):
        if stack is None:
            stack = traceback.format_stack(limit=15)[:-1]
        else:
            stack = []
        self._outqueue.put([test, stack, variables])

    def _stop_reactor(self):
        if self._item:
            # Server not stopped fail
            self._return(False, {'self._item': repr(self._item)})

        self._running = False
        print(reactor, reactor.running)
        if reactor.running:
            reactor.callLater(.1, reactor.stop)

    def _read_thread(self):
        print("%s - Read thread started" % self._name)
        while self._running:
            try:
                cmd = self._inqueue.get(timeout=.1)
            except:
                continue
            func = getattr(self, cmd[0])
            print("Running: %s(%s, %s)" % (func.__name__, cmd[1], cmd[2]))
            reactor.callFromThread(func, *cmd[1], **cmd[2])
        print("%s - Read thread died" % self._name)

    def start(self, timeout=10):
        self._timeout = timeout
        self._running = True
        multiprocessing.Process.start(self)

    def _base_run(self):
        reactor.callLater(self._timeout, self._stop_reactor)
        reactor.callInThread(self._read_thread)
        if not reactor.running:
            reactor.run()

    def run(self):
        self._base_run()

class ServerHandler(BaseTHandler):
    def __init__(self, *args, **kwargs):
        self._name = "ServerHandler"
        BaseTHandler.__init__(self, *args, **kwargs)

    def get_callbacks(self):
        return {'server_started': [CalvinCB(self._server_started)],
                'server_stopped': [CalvinCB(self._server_stopped)],
                'peer_disconnected': [CalvinCB(self._peer_disconnected)],
                'peer_connected': [CalvinCB(self._peer_connected)]}

    def _data_received(self, *args):
        print("server_data_received", args)

    def _peer_connected(self, transport, uri):
        print("server_peer_connected", transport)
        transport.callback_register('join_finished', CalvinCB(self._join_finished))
        transport.callback_register('data_received', CalvinCB(self._data_received))

    def _join_finished(self, transport, _id, uri, is_orginator):
        print("server_join_finshed", transport, _id, uri)
        self._return(transport._coder is not None and _id and uri, {'transport._coder': transport._coder , 'id': _id, 'uri': uri})
        self._return('server_join_finished', {'transport': repr(transport), '_id': _id, 'uri': uri})
        pass

    def _peer_disconnected(self, *args):
        print("server peer disconnected", args)

    def _server_stopped(self, *args):
        print("Server stopped", args)
        self._item = None
        self._outqueue.put(["server_stopped", repr(args)])

        # Die here ?
        self._stop_reactor()

    def _stop_server(self):
        print("_stop_server")
        self._item.stop()
        self._return(not self._item.is_listening())

    def stop(self):
        print("server_stop", self._item)
        if self._item:
            self._stop_server()

        # Timeout
        reactor.callLater(3, self._stop_reactor)

    def _server_started(self, server, port):
        print("Server started", server, port)
        self._item = server

        # put in queue
        self._return(port > 0 and port < 65536, {'port': port})
        self._return('server_started', port)

    def _start_server(self):
        self._ttf.listen(self._uri)

    def run(self):
        print("start server")
        reactor.callLater(0, self._start_server)
        self._base_run()
        print("server finished")

    def _run_command(self, command, *args):
        comand(args)
        reactor.callLater(0, self.start_server)

    def _timeout(self, command, *args):
        self._return(["timeout", comand, args])

class ClientHandler(BaseTHandler):
    def __init__(self, *args, **kwargs):
        self._name = "ServerHandler"
        self._port = None
        self._stop = False
        BaseTHandler.__init__(self, *args, **kwargs)

    def set_ttf(self, ttf):
        self._ttf = ttf

    def set_port(self, port):
        print("set_port", port)
        self._port = port

    def get_callbacks(self):
        return {'peer_disconnected': [CalvinCB(self._peer_disconnected)],
                'peer_connected': [CalvinCB(self._peer_connected)]}

    def _data_received(self, data):
        print("client_data_received", data)
        self._return('client_data_received', {'data': data})

    def _peer_connected(self, transport, uri):
        print("client_peer_connected", transport)
        transport.callback_register('join_finished', CalvinCB(self._join_finished))
        transport.callback_register('data_received', CalvinCB(self._data_received))
        self._return('client_connected', {'transport': repr(transport), 'uri': uri})
        self._item = transport

    def _join_finished(self, transport, _id, uri, is_orginator):
        print("client_join_finshed", transport, _id, uri)
        self._return(transport._coder is not None and _id and uri, {'transport._coder': transport._coder , 'id': _id, 'uri': uri})
        self._return('client_join_finished', {'transport': repr(transport), '_id': _id, 'uri': uri})

    def _peer_disconnected(self, transport, uri, reason):
        print("client_peer_disconnected", transport, uri, reason)
        #self._return(not self._item.is_connected(), variables={'is_connected': self._item.is_connected()})
        self._return('client_disconnected', {'transport': repr(transport), 'reason': reason, 'uri': uri})
        # If we have stop stop everything
        if self._stop:
            self._item = None
            self._stop_reactor()

    def _stop_client(self):
        print("_stop_client(disconnect)")
        self._stop = True
        self._item.disconnect()

    def stop(self):
        print("client_stop", self._item)
        if self._item:
            self._stop_client()

        # Timeout
        reactor.callLater(1, self._stop_reactor)

    def run(self):
        print("start client")
        self._uri  =  "%s:%s" % (self._uri, self._port)
        reactor.callLater(0, self._ttf.join, self._uri)
        self._base_run()
        print("client finished")

# @pytest.mark.interactive
class TestTransportServer(object):
    _mmanager = multiprocessing.Manager()
    def test_start_stop(self, monkeypatch):

        shqs = [self._mmanager.Queue(), self._mmanager.Queue()]
        sh = ServerHandler("calvinip://localhost", shqs[0], shqs[1])

        ttf = calvinip_transport.CalvinTransportFactory(str(uuid.uuid4()), sh.get_callbacks())

        sh.set_ttf(ttf)
        sh.start()

        error = None

        try:
            while sh.is_alive():
                try:
                    mess = shqs[0].get(timeout=.3)
                    #print(mess)
                except:
                    continue

                if mess[0] == 'timeout':
                    print(mess[1])
                    raise Exception("Timeout: %s" % "\n".join(mess[1][11:]))
                elif mess[0] == 'server_started':
                    shqs[1].put(['stop', [], {}])
                elif mess[0] == 'server_stopped':
                    break
                else:
                    #print mess
                    if not mess[0]:
                        for a in mess[1]:
                            print a,
                        for k,v in mess[2].items():
                            print "%s = %s" % (k, repr(v))
                        raise Exception("\n".join(mess[1][11:]))
        except Exception as e:
            error = e

        shqs[1].put(['stop', [], {}])
        sh.join(timeout=.2)

        if sh.is_alive():
            sh.terminate()

        if error:
            pytest.fail(error)

    def test_callbacks(self, monkeypatch):
        #self.test_start_stop(monkeypatch)
        pass

    def test_peer_connected(self, monkeypatch):
        pass

# @pytest.mark.interactive
@pytest.mark.slow
class TestTransportClient(object):
    test_nodes = 2
    _mmanager = multiprocessing.Manager()

    def test_connect(self, monkeypatch):
        queues = []
        shqs = [self._mmanager.Queue(), self._mmanager.Queue()]
        chqs = [self._mmanager.Queue(), self._mmanager.Queue()]
        sh = ServerHandler("calvinip://127.0.0.1", shqs[0], shqs[1])
        ch = ClientHandler("calvinip://127.0.0.1", chqs[0], chqs[1])

        ttfs = calvinip_transport.CalvinTransportFactory(str(uuid.uuid4()), sh.get_callbacks())
        ttfc = calvinip_transport.CalvinTransportFactory(str(uuid.uuid4()), ch.get_callbacks())

        sh.set_ttf(ttfs)
        ch.set_ttf(ttfc)

        sh.start()
        #ch.start()

        queues = [shqs, chqs]
        cstop = sstop = False
        stop = False
        error = None

        try:
            while not stop:
                for q in queues:
                    try:
                        mess = q[0].get(timeout=.1)
                        #print(mess[0])
                    except:
                        continue

                    if mess[0] == 'timeout':
                        print(mess[1])
                        # TODO: terminate
                        raise Exception("Timeout: %s" % "\n".join(mess[1][11:]))
                    elif mess[0] == 'server_stopped':
                        print "Hej hej"
                        sstop = True
                        stop = (sstop and cstop)
                    elif mess[0] == 'server_started':
                        ch.set_port(mess[2])
                        ch.start()
                    elif mess[0] == 'client_disconnected':
                        cstop = True
                        stop = (sstop and cstop)
                    elif mess[0] == 'client_join_finished':
                        stop = True
                    else:
                        #print mess
                        if not mess[0]:
                            for a in mess[1][11:-1]:
                                print a,
                            for k,v in mess[2].items():
                                print "%s = %s" % (k, repr(v))
                            raise Exception("\n".join(mess[1][11:]))
        except Exception as e:
            error = e

        for tq in queues:
            print(repr(tq))
            tq[1].put(['stop', [], {}])

        print sh.join(timeout=.5)
        print ch.join(timeout=.5)

        if sh.is_alive():
            sh.terminate()
        if ch.is_alive():
            ch.terminate()

        if error:
            pytest.fail(error)

    def test_data(self, monkeypatch):
        pass

    def test_callback(self, monkeypatch):
        pass
