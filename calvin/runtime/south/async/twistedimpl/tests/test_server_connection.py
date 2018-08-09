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

from calvin.runtime.south.async import async
from calvin.runtime.south.async import server_connection
from calvin.runtime.south.async import threads
from calvin.utilities.calvinlogger import get_logger

import pytest
import socket

_log = get_logger(__name__)


def data_available(conn):
    first_print = True
    while conn.data_available is False:
        if first_print:
            print "waiting for conn.data_available ... ",
            first_print = False
    print ""
    return True


def connection_made(factory):
    first_print = True
    while not factory.connections:
        if first_print:
            print "waiting for connection ... ",
            first_print = False
    print ""
    return True


def hundred_connection_made(factory):
    first_print = True
    while not len(factory.connections) == 100:
        if first_print:
            print "waiting for 100 connection ... ",
            first_print = False
    print ""
    return True


def no_more_connections(factory):
    first_print = True
    while factory.connections:
        if first_print:
            print "waiting for connections to close ... ",
            first_print = False
    print ""
    return True


def print_header(string):
    _log.info("\n\n### %s ###", string)


# Stub
class Scheduler_stub(object):
    def trigger_loop(self, actor_ids=None):
        """ Trigger the loop_once """
        async.DelayedCall(0, self.trigger_loop)
        return

class TestServer(object):

    @pytest.mark.essential
    @pytest.inlineCallbacks
    def test_default_line_mode(self):
        print_header("TEST_DEFAULT_LINE_MODE")
        print_header("Setup")
        scheduler = Scheduler_stub()
        self.factory = server_connection.ServerProtocolFactory(scheduler.trigger_loop)
        self.factory.start('localhost', 8123)
        self.conn = None
        self.client_socket = None

        print_header("Test_Connection")
        ##################################################################
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        assert not self.factory.connections
        assert not self.factory.pending_connections

        yield threads.defer_to_thread(self.client_socket.connect, ('localhost', 8123))
        yield threads.defer_to_thread(connection_made, self.factory)
        assert self.factory.pending_connections

        _, self.conn = self.factory.accept()

        ####################################################################
        ####################################################################

        print_header("Test_Line_Received")
        ####################################################################
        assert self.conn.data_available is False
        yield threads.defer_to_thread(self.client_socket.send, "sending string \r\n")
        yield threads.defer_to_thread(data_available, self.conn)
        assert self.conn.data_get() == "sending string "

        print_header("Teardown")
        self.factory.stop()
        yield threads.defer_to_thread(no_more_connections, self.factory)

    @pytest.mark.essential
    @pytest.inlineCallbacks
    def test_args_in_line_mode(self):
        print_header("TEST_ARGS_IN_LINE_MODE")
        print_header("Setup")
        scheduler = Scheduler_stub()
        self.factory = server_connection.ServerProtocolFactory(scheduler.trigger_loop, delimiter='end', max_length=3)
        self.factory.start('localhost', 8123)
        self.conn = None
        self.client_socket = None

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        yield threads.defer_to_thread(self.client_socket.connect, ('localhost', 8123))
        yield threads.defer_to_thread(connection_made, self.factory)

        _, self.conn = self.factory.accept()

        print_header("Test_Short_Line_Received")
        ####################################################################
        yield threads.defer_to_thread(self.client_socket.send, "123end")
        yield threads.defer_to_thread(data_available, self.conn)

        assert self.conn.data_get() == "123"

        print_header("Test_Long_Line_Received")
        ####################################################################
        yield threads.defer_to_thread(self.client_socket.send, "1234end")
        yield threads.defer_to_thread(data_available, self.conn)

        assert self.conn.data_get() == "1234"

        print_header("Teardown")
        self.factory.stop()
        yield threads.defer_to_thread(no_more_connections, self.factory)

    @pytest.mark.essential
    @pytest.inlineCallbacks
    def test_raw_mode(self):
        print_header("TEST_RAW_MODE")
        print_header("Setup")
        scheduler = Scheduler_stub()
        self.factory = server_connection.ServerProtocolFactory(scheduler.trigger_loop, mode='raw', max_length=10)
        self.factory.start('localhost', 8123)
        self.conn = None
        self.client_socket = None

        print_header("Test_Connection")
        ##################################################################
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        yield threads.defer_to_thread(self.client_socket.connect, ('localhost', 8123))
        yield threads.defer_to_thread(connection_made, self.factory)
        assert self.factory.pending_connections

        _, self.conn = self.factory.accept()
        assert not self.factory.pending_connections

        print_header("Test_Data_Received")
        ####################################################################
        assert self.conn.data_available is False
        yield threads.defer_to_thread(self.client_socket.send, "abcdefghijklmnopqrstuvxyz123456789")
        yield threads.defer_to_thread(data_available, self.conn)
        assert self.conn.data_get() == "abcdefghij"
        assert self.conn.data_get() == "klmnopqrst"
        assert self.conn.data_get() == "uvxyz12345"
        assert self.conn.data_get() == "6789"

        print_header("Teardown")
        self.factory.stop()
        yield threads.defer_to_thread(no_more_connections, self.factory)

    @pytest.mark.slow
    @pytest.inlineCallbacks
    def test_many_clients(self):
        print_header("TEST_MANY_CLIENTS")
        print_header("Setup")
        scheduler = Scheduler_stub()
        self.factory = server_connection.ServerProtocolFactory(scheduler.trigger_loop, mode='raw', max_length=10)
        self.factory.start('localhost', 8123)
        self.conn = None
        self.client_socket = None

        print_header("Test_Connection")
        ##################################################################
        clients = []
        for i in range(100):
            clients.append(socket.socket(socket.AF_INET, socket.SOCK_STREAM))

        for c in clients:
            yield threads.defer_to_thread(c.connect, ('localhost', 8123))

        yield threads.defer_to_thread(hundred_connection_made, self.factory)

        assert len(self.factory.pending_connections) == 100

        for i in range(100):
            _, self.conn = self.factory.accept()

        assert not self.factory.pending_connections
