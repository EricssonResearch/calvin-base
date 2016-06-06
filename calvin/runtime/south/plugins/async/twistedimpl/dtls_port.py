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

from twisted.internet import abstract, udp, base, reactor

import ssl
import socket
from dtls import do_patch
from dtls.sslconnection import SSLConnection
from twisted.python import log

from os import path

import time
import threading

from calvin.utilities.calvinlogger import get_logger
_log = get_logger(__name__)

from twisted.python.runtime import platformType
if platformType == 'win32':
    from errno import WSAEWOULDBLOCK
    from errno import WSAEINTR, WSAEMSGSIZE, WSAETIMEDOUT
    from errno import WSAECONNREFUSED, WSAECONNRESET, WSAENETRESET
    from errno import WSAEINPROGRESS
    from errno import WSAENOPROTOOPT as ENOPROTOOPT

    # Classify read and write errors
    _sockErrReadIgnore = [WSAEINTR, WSAEWOULDBLOCK, WSAEMSGSIZE, WSAEINPROGRESS]
    _sockErrReadRefuse = [WSAECONNREFUSED, WSAECONNRESET, WSAENETRESET,
                          WSAETIMEDOUT]

    # POSIX-compatible write errors
    EMSGSIZE = WSAEMSGSIZE
    ECONNREFUSED = WSAECONNREFUSED
    EAGAIN = WSAEWOULDBLOCK
    EINTR = WSAEINTR
else:
    from errno import EWOULDBLOCK, EINTR, EMSGSIZE, ECONNREFUSED, EAGAIN
    from errno import ENOPROTOOPT
    _sockErrReadIgnore = [EAGAIN, EINTR, EWOULDBLOCK]
    _sockErrReadRefuse = [ECONNREFUSED]

class DTLSClientPort(udp.Port):
    """
    Extension of twisted UDP port.
    Can only be connected to one destination. 
    Executed DTLS handshake with this destination and all further data
    will be encrypted.
    """

    def __init__(self, port, proto, interface='', maxPacketSize=8192, reactor=None, address=None):
	udp.Port.__init__(self, port, proto, interface, maxPacketSize, reactor)
	self._connectedAddr = address
        self.startListening()

    def createInternetSocket(self):
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	do_patch()
	sslsocket = ssl.wrap_socket(s)
	sslsocket.connect(self._connectedAddr)
	return sslsocket

    def _bindSocket(self):
        self.socket = self.createInternetSocket()
	self._realPortNumber = self.socket.getsockname()[1]
	self.connected = 1
        self.fileno = self.socket.fileno

    def write(self, datagram, addr=None):
	return super(DTLSClientPort, self).write(datagram)

    def doRead(self):
        """
        Called when my socket is ready for reading.
        """
        read = 0
        while read < self.maxThroughput:
            try:
                data = self.socket.recv(self.maxPacketSize)
            except socket.error as se:
                no = se.args[0]
                if no in _sockErrReadIgnore:
                    return
                if no in _sockErrReadRefuse:
                    if self._connectedAddr:
                        self.protocol.connectionRefused()
                    return
		if no == 2:
		    _log.error("OpenSSLError SSL_ERROR_WANT_READ. Ignore if Calvin environment is closing.")
		    return
                raise
		
            else:
                read += len(data)
                try:
                    #_log.info("client received: %s" % data)
                    self.protocol.datagramReceived(data, self._connectedAddr)
		    return
                except:
                    log.err()

class TransportWrapper():
    def __init__(self, conn):
	self._conn=conn
    
    def write(self, msg, remote):
	self._conn.write(msg)

class DTLSServerPort(udp.Port):
    """
    Extension of twisted UDP port.
    Can only be connected to one destination. 
    Executes DTLS handshake with this destination and all further data
    will be encrypted.
    Does not use a socket, like udp.Port, but a SSLConnection.
    """

    def __init__(self, port, proto, interface='', maxPacketSize=8192, reactor=None, connection=None):
	udp.Port.__init__(self, port, proto, interface, maxPacketSize, reactor)
        self.protocol = proto
        self.port = port
        self.interface = interface
        self.maxPacketSize = maxPacketSize
        self._conn = connection
        
        self.fileno = self._conn.get_socket(False).fileno
        self.protocol.makeConnection(self) 
	self.connected = 1
        self.startReading()

    def write(self, datagram, addr=None):
	return self._conn.write(datagram)

    def doRead(self):
        """
        Called when my socket is ready for reading.
        """
        data = self._conn.read()
        self.protocol.datagramReceived(data, self._conn.get_socket(True).getpeername())
	
    def connectionLost(self, reason=None):
        """
        Cleans up my connection.
        """
        self._realPortNumber = None
        self.protocol.doStop()
        
	# Try to close the connection the nice way. If any errors are raised,
	# eg. the client dropped the connection, connection will simply be closed.
	try:
	    self._conn.shutdown().close()
            del self._conn
	except socket.error as se:
	    _log.error("Error occurred while closing server connection. Server connection will be dropped.")
	    del self._conn
	
        del self.fileno
        if hasattr(self, "d"):
            self.d.callback(None)
            del self.d
