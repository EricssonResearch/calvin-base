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

import socket
import bluetooth
from errno import EBADFD
from twisted.internet import tcp
from twisted.internet.tcp import *
from twisted.python import log


class BtBaseClient(tcp.Connection):
    addressFamily = 31  # AF_BLUETOOTH

    def createInternetSocket(self):
        s = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        s.setblocking(0)
        tcp.fdesc._setCloseOnExec(s.fileno())
        return s

    def resolveAddress(self):
        self.realAddress = self.addr
        self.doConnect()

    def doConnect(self):
        self.doWrite = self.doConnect
        self.doRead = self.doConnect
        if not hasattr(self, "connector"):
            # this happens when connection failed but doConnect
            # was scheduled via a callLater in self._finishInit
            return

        err = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err:
            self.failIfNotConnected(error.getConnectError((err, strerror(err))))
            return

        # doConnect gets called twice.  The first time we actually need to
        # start the connection attempt.  The second time we don't really
        # want to (SO_ERROR above will have taken care of any errors, and if
        # it reported none, the mere fact that doConnect was called again is
        # sufficient to indicate that the connection has succeeded), but it
        # is not /particularly/ detrimental to do so.  This should get
        # cleaned up some day, though.
        try:
            connectResult = self.socket.connect_ex(self.realAddress)
        except socket.error as se:
            connectResult = se.args[0]
        if connectResult:
            if connectResult == EISCONN or connectResult == EBADFD:
                pass
            # on Windows EINVAL means sometimes that we should keep trying:
            # http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winsock/winsock/connect_2.asp
            elif ((connectResult in (EWOULDBLOCK, EINPROGRESS, EALREADY)) or
                  (connectResult == EINVAL and platformType == "win32")):
                self.startReading()
                self.startWriting()
                return
            else:
                self.failIfNotConnected(error.getConnectError((connectResult, strerror(connectResult))))
                return

        # If I have reached this point without raising or returning, that means
        # that the socket is connected.
        del self.doWrite
        del self.doRead
        # we first stop and then start, to reset any references to the old doRead
        self.stopReading()
        self.stopWriting()
        self._connectDone()

    def doRead(self):
        data = self.socket.recv(self.bufferSize)
        return self.protocol.dataReceived(data)


class BtClient(BtBaseClient, tcp.Client):

    def __init__(self, *args, **kwargs):
        super(BtClient, self).__init__(*args, **kwargs)

    def getPeer(self):
        return self.realAddress

    def getHost(self):
        return self.socket.getsockname()


class BtConnector(tcp.Connector):

    def __init__(self, host, port, factory, timeout, bindAddress, reactor):
        tcp.Connector.__init__(self, host, int(port), factory, timeout, bindAddress, reactor)

    def _makeTransport(self):
        return BtClient(self.host, self.port, self.bindAddress, self, self.reactor)

    def getDestination(self):
        return (self.host, self.port)


class BtServer(tcp.Server):
    """ socket from accept """

    def getHost(self):
        return self.socket.getsockname()

    def getPeer(self):
        return self.client


class BtPort(tcp.Port):
    addressFamily = socket.AF_BLUETOOTH
    transport = BtServer

    def __init__(self, port, factory, backlog=50, interface='', reactor=None):
        super(BtPort, self).__init__(port, factory, backlog, interface, reactor)

    def createInternetSocket(self):
        s = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        s.setblocking(0)
        if platformType == "posix" and sys.platform != "cygwin":
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s

    def _buildAddr(self, (host, port)):
        return (host, port)

    def getHost(self):
        return self.socket.getsockname()

    def doRead(self):
        """Called when my socket is ready for reading.

        This accepts a connection and calls self.protocol() to handle the
        wire-level protocol.
        """
        try:
            if platformType == "posix":
                numAccepts = self.numberAccepts
            else:
                # win32 event loop breaks if we do more than one accept()
                # in an iteration of the event loop.
                numAccepts = 1
            for i in range(numAccepts):
                # we need this so we can deal with a factory's buildProtocol
                # calling our loseConnection
                if self.disconnecting:
                    return
                try:
                    skt, addr = self.socket.accept()
                except socket.error as e:
                    if e.args[0] in (EWOULDBLOCK, EAGAIN):
                        self.numberAccepts = i
                        break
                    elif e.args[0] == EPERM:
                        # Netfilter on Linux may have rejected the
                        # connection, but we get told to try to accept()
                        # anyway.
                        continue
                    elif e.args[0] in (EMFILE, ENOBUFS, ENFILE, ENOMEM, ECONNABORTED):

                        # Linux gives EMFILE when a process is not allowed
                        # to allocate any more file descriptors.  *BSD and
                        # Win32 give (WSA)ENOBUFS.  Linux can also give
                        # ENFILE if the system is out of inodes, or ENOMEM
                        # if there is insufficient memory to allocate a new
                        # dentry.  ECONNABORTED is documented as possible on
                        # both Linux and Windows, but it is not clear
                        # whether there are actually any circumstances under
                        # which it can happen (one might expect it to be
                        # possible if a client sends a FIN or RST after the
                        # server sends a SYN|ACK but before application code
                        # calls accept(2), however at least on Linux this
                        # _seems_ to be short-circuited by syncookies.

                        log.msg("Could not accept new connection (%s)" % (
                            errorcode[e.args[0]],))
                        break
                    raise

                fdesc._setCloseOnExec(skt.fileno())
                protocol = self.factory.buildProtocol(self._buildAddr(addr))
                if protocol is None:
                    skt.close()
                    continue
                s = self.sessionno
                self.sessionno = s+1
                transport = self.transport(skt, protocol, addr, self, s, self.reactor)
                protocol.makeConnection(transport)
            else:
                self.numberAccepts = self.numberAccepts+20
        except:
            pass
