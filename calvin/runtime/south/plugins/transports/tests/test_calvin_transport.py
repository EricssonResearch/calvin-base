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

def slay(plist):
    import signal
    for p in plist:
        if p.is_alive():
            p.terminate()
            p.join(timeout=.2)
            if p.is_alive():
                print "Warning: process %s still alive slay!!" % p._name
                os.kill(p.pid, signal.SIGKILL)
    time.sleep(.1)
    if len(multiprocessing.active_children()) > 1:
        print "Error: children is still alive", multiprocessing.active_children()
        for a in multiprocessing.active_children():
            a.terminate()

class BaseTHandler(multiprocessing.Process):
    def __init__(self, uri, outqueue, inqueue, timeout=5):
        multiprocessing.Process.__init__(self)
        self._timeout = timeout
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

    def _stop_reactor(self, timeout=False):
        if timeout:
            self.__timeout()
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

    def start(self):
        self._running = True
        self.daemon = True
        multiprocessing.Process.start(self)

    def __timeout(self, command=None, *args):
        print("Timeout in", self)
        self._return("timeout", {command: args})

    def _base_run(self):
        # make it work with twisted py.test plugin also
        reactor._started = False
        print "timeout %s", self._timeout
        reactor.callLater(self._timeout, self._stop_reactor, timeout=True)
        reactor.callInThread(self._read_thread)
        reactor.run()

    def run(self):
        self._base_run()

class TransportTestServerHandler(BaseTHandler):
    def __init__(self, *args, **kwargs):
        self._name = "TestServerHandler"
        BaseTHandler.__init__(self, *args, **kwargs)
        self._tp = None

    def get_callbacks(self):
        return {'server_started': [CalvinCB(self._server_started)],
                'server_stopped': [CalvinCB(self._server_stopped)],
                'join_failed': [CalvinCB(self._join_failed)],
                'peer_disconnected': [CalvinCB(self._peer_disconnected)],
                'peer_connected': [CalvinCB(self._peer_connected)]}

    def _data_received(self, *args):
        print("server_data_received", args)

    def _peer_connected(self, transport, uri):
        print("server_peer_connected", transport)
        transport.callback_register('join_finished', CalvinCB(self._join_finished))
        transport.callback_register('data_received', CalvinCB(self._data_received))

    def _join_failed(self, transport, _id, uri, is_orginator, reason):
        _log.debug("Server join failed on uri %s, reason %s", uri, reason)
        self._return('server_join_failed', {'transport': repr(transport), 'uri': uri, 'reason': reason})

    def _join_finished(self, transport, _id, uri, is_orginator):
        print("server_join_finished", transport, _id, uri)
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
        reactor.callLater(1, self._stop_reactor)

    def _server_started(self, server, port):
        print("Server started", server, port)
        self._item = server

        # put in queue
        self._return(port > 0 and port < 65536, {'port': port})
        self._return('server_started', port)

    def _start_server(self):
        self._tp = self._ttf.listen(self._uri)

    def run(self):
        print("start server")
        reactor.callLater(0, self._start_server)
        self._base_run()
        print("server finished")

    def _run_command(self, command, *args):
        comand(args)
        reactor.callLater(0, self.start_server)

class TransportTestClientHandler(BaseTHandler):
    def __init__(self, *args, **kwargs):
        self._name = "TestClientHandler"
        self._port = None
        self._stop = False
        self._tp = None
        BaseTHandler.__init__(self, *args, **kwargs)

    def set_ttf(self, ttf):
        self._ttf = ttf

    def set_port(self, port):
        print("set_port", port)
        self._port = port

    def get_callbacks(self):
        return {'peer_disconnected': [CalvinCB(self._peer_disconnected)],
                'peer_connection_failed': [CalvinCB(self._connection_failed)],
                'join_failed': [CalvinCB(self._join_failed)],
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

    def _connection_failed(self, tp_link, uri, reason):
        _log.debug("Client connection failed on uri %s, reason %s", uri, reason)
        self._return('client_connection_failed', {'link': repr(tp_link), 'uri': uri, 'reason': reason})

    def _join_failed(self, transport, _id, uri, is_orginator, reason):
        _log.debug("Client join failed on uri %s, reason %s", uri, reason)
        self._return('client_join_failed', {'transport': repr(transport), 'uri': uri, 'reason': reason})

    def _join_finished(self, transport, _id, uri, is_orginator):
        print("client_join_finished", transport, _id, uri)
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

    def _join(self):
         self._tp = self._ttf.join(self._uri)

    def run(self):
        print("start client")
        self._uri  =  "%s:%s" % (self._uri, self._port)
        reactor.callLater(0, self._join)
        self._base_run()
        print("client finished")

class ConnectionFailed(Exception):
    pass

class ServerJoinFailed(Exception):
    pass

class ClientJoinFailed(Exception):
    pass

# @pytest.mark.interactive
class TestTransportServer(object):

    @pytest.mark.essential
    def test_start_stop(self, monkeypatch):
        _mmanager = multiprocessing.Manager()
        shqs = [_mmanager.Queue(), _mmanager.Queue()]
        sh = TransportTestServerHandler("calvinip://localhost", shqs[0], shqs[1], timeout=2)

        ttf_uuid = str(uuid.uuid4())
        ttf = calvinip_transport.CalvinTransportFactory(ttf_uuid, ttf_uuid, sh.get_callbacks())

        sh.set_ttf(ttf)
        sh.start()

        error = None

        try:
            while sh.is_alive():
                try:
                    mess = shqs[0].get(timeout=.3)
                    # print(mess)
                except:
                    continue

                if mess[0] == 'timeout':
                    print(mess[1])
                    raise Exception("Timeout: %s" % "\n".join(mess[1][11:]))
                elif mess[0] == 'server_started':
                    pass
                    shqs[1].put(['stop', [], {}])
                elif mess[0] == 'server_stopped':
                    break
                else:
                    # print mess
                    if not mess[0]:
                        for a in mess[1]:
                            print a,
                        for k,v in mess[2].items():
                            print "%s = %s" % (k, repr(v))
                        raise Exception("\n".join(mess[1][11:]))
        except Exception as e:
            import traceback
            traceback.print_exc()
            error = e

        shqs[1].put(['stop', [], {}])
        sh.join(timeout=.2)

        slay([sh])

        if error:
            pytest.fail(error)

    def test_callbacks(self, monkeypatch):
        #self.test_start_stop(monkeypatch)
        pass

    def test_peer_connected(self, monkeypatch):
        pass

class TestTransportClient(object):
    test_nodes = 2

    @pytest.mark.essential
    def test_connect(self, monkeypatch):
        queues = []
        _mmanager = multiprocessing.Manager()
        shqs = [_mmanager.Queue(), _mmanager.Queue()]
        chqs = [_mmanager.Queue(), _mmanager.Queue()]
        sh = TransportTestServerHandler("calvinip://127.0.0.1", shqs[0], shqs[1], timeout=2)
        ch = TransportTestClientHandler("calvinip://127.0.0.1", chqs[0], chqs[1], timeout=2)


        ttfs_uuid = str(uuid.uuid4())
        ttfs = calvinip_transport.CalvinTransportFactory(ttfs_uuid, ttfs_uuid, sh.get_callbacks())
        ttfc_uuid = str(uuid.uuid4())
        ttfc = calvinip_transport.CalvinTransportFactory(ttfc_uuid, ttfc_uuid, ch.get_callbacks())

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
                        if mess[2]['reason'] != "OK":
                            raise Exception("Did not disconnect cleanly")
                        cstop = True
                        stop = (sstop and cstop)
                    elif mess[0] == 'client_join_finished':
                        stop = True
                    elif mess[0] == 'client_join_failed':
                        raise ClientJoinFailed(str(mess[2]))
                    elif mess[0] == 'server_join_failed':
                        raise ServerJoinFailed(str(mess[2]))
                    elif mess[0] == 'client_connection_failed':
                        raise ConnectionFailed(str(mess[1:]))
                    else:
                        # print mess
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

        time.sleep(.2)

        slay([sh, ch])

        if error:
            pytest.fail(error)

    def test_connect_client_join_fail(self, monkeypatch):
        _mmanager = multiprocessing.Manager()
        queues = []
        shqs = [_mmanager.Queue(), _mmanager.Queue()]
        chqs = [_mmanager.Queue(), _mmanager.Queue()]
        sh = TransportTestServerHandler("calvinip://127.0.0.1", shqs[0], shqs[1])
        ch = TransportTestClientHandler("calvinip://127.0.0.1", chqs[0], chqs[1])

        ttfs_uuid = str(uuid.uuid4())
        ttfs = calvinip_transport.CalvinTransportFactory(ttfs_uuid, ttfs_uuid, sh.get_callbacks())
        ttfc_uuid = str(uuid.uuid4())
        ttfc = calvinip_transport.CalvinTransportFactory(ttfc_uuid, ttfc_uuid, ch.get_callbacks())

        sh.set_ttf(ttfs)
        ch.set_ttf(ttfc)

        monkeypatch.setattr(ttfc, "_client_validator", lambda x: False)

        sh.start()

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
                    elif mess[0] == 'client_join_failed':
                        raise ClientJoinFailed(str(mess[2]))
                    elif mess[0] == 'server_join_failed':
                        raise ServerJoinFailed(str(mess[2]))
                    elif mess[0] == 'client_connection_failed':
                        raise ConnectionFailed(str(mess[2]))
                    else:
                        # print mess
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

        slay([sh, ch])

        if error:
            with pytest.raises(ClientJoinFailed):
                import traceback
                traceback.print_exc(error)
                raise error
        else:
            pytest.fail("No exception")



    def test_connect_server_join_fail(self, monkeypatch):
        _mmanager = multiprocessing.Manager()
        queues = []
        shqs = [_mmanager.Queue(), _mmanager.Queue()]
        chqs = [_mmanager.Queue(), _mmanager.Queue()]
        sh = TransportTestServerHandler("calvinip://127.0.0.1", shqs[0], shqs[1])
        ch = TransportTestClientHandler("calvinip://127.0.0.1", chqs[0], chqs[1])

        ttfs_uuid = str(uuid.uuid4())
        ttfs = calvinip_transport.CalvinTransportFactory(ttfs_uuid, ttfs_uuid, sh.get_callbacks())
        ttfc_uuid = str(uuid.uuid4())
        ttfc = calvinip_transport.CalvinTransportFactory(ttfc_uuid, ttfc_uuid, ch.get_callbacks())

        sh.set_ttf(ttfs)
        ch.set_ttf(ttfc)

        monkeypatch.setattr(ttfs, "_client_validator", lambda x: False)

        sh.start()

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
                    elif mess[0] == 'client_join_failed':
                        raise ClientJoinFailed(str(mess[2]))
                    elif mess[0] == 'server_join_failed':
                        raise ServerJoinFailed(str(mess[2]))
                    elif mess[0] == 'client_connection_failed':
                        raise ConnectionFailed(str(mess[2]))
                    else:
                        # print mess
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

        slay([sh, ch])

        if error:
            with pytest.raises(ServerJoinFailed):
                import traceback
                traceback.print_exc(error)
                raise error
        else:
            pytest.fail("No exception")



    def test_connect_fail(self, monkeypatch):
        _mmanager = multiprocessing.Manager()
        queues = []
        shqs = [_mmanager.Queue(), _mmanager.Queue()]
        chqs = [_mmanager.Queue(), _mmanager.Queue()]
        sh = TransportTestServerHandler("calvinip://127.0.0.1", shqs[0], shqs[1])
        ch = TransportTestClientHandler("calvinip://127.0.0.1", chqs[0], chqs[1])

        ttfs_uuid = str(uuid.uuid4())
        ttfs = calvinip_transport.CalvinTransportFactory(ttfs_uuid, ttfs_uuid, sh.get_callbacks())
        ttfc_uuid = str(uuid.uuid4())
        ttfc = calvinip_transport.CalvinTransportFactory(ttfc_uuid, ttfc_uuid, ch.get_callbacks())

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
                        ch.set_port(str(int(mess[2])+1))
                        ch.start()
                    elif mess[0] == 'client_disconnected':
                        cstop = True
                        stop = (sstop and cstop)
                    elif mess[0] == 'client_join_finished':
                        stop = True
                    elif mess[0] == 'client_join_failed':
                        raise ClientJoinFailed(str(mess[2]))
                    elif mess[0] == 'server_join_failed':
                        raise ServerJoinFailed(str(mess[2]))
                    elif mess[0] == 'client_connection_failed':
                        raise ConnectionFailed(str(mess[2]))
                    else:
                        # print mess
                        if not mess[0]:
                            for a in mess[1][11:-1]:
                                print a,
                            for k,v in mess[2].items():
                                print "%s = %s" % (k, repr(v))
                            raise Exception("\n".join(mess[1][11:]))
        except Exception as e:
            error = e

        for tq in queues:
            print "hej", repr(tq)
            tq[1].put(['stop', [], {}])

        print sh, ch
        slay([sh, ch])

        if error:
            with pytest.raises(ConnectionFailed):
                import traceback
                traceback.print_exc(error)
                raise error
        else:
            pytest.fail("No exception")

    def test_data(self, monkeypatch):
        pass

    def test_callback(self, monkeypatch):
        pass
