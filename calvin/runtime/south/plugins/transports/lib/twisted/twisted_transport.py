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

from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities import calvinlogger
from calvin.utilities import calvinuuid
from calvin.runtime.south.plugins.transports import base_transport

_log = calvinlogger.get_logger(__name__)

_join_request_reply = {'cmd': 'JOIN_REPLY', 'id': None, 'sid': None, 'serializer': None}
_join_request = {'cmd': 'JOIN_REQUEST', 'id': None, 'sid': None, 'serializers': []}


class CalvinTransport(base_transport.BaseTransport):
    def __init__(self, rt_id, remote_uri, callbacks, transport, proto=None):
        """docstring for __init__"""
        super(CalvinTransport, self).__init__(rt_id, remote_uri, callbacks=callbacks)

        self._rt_id = rt_id
        self._remote_rt_id = None
        self._coder = None
        self._transport = transport(self._uri.hostname, self._uri.port, callbacks, proto=proto)
        self._rtt = 2000  # Init rt in ms

        # TODO: This should be incoming param
        self._verify_client = lambda x: True

        self._incoming = proto is not None
        if self._incoming:
            # TODO: Set timeout
            # Incomming connection timeout if no join
            self._transport.callback_register("disconnected", CalvinCB(self._disconnected))
            self._transport.callback_register("data", CalvinCB(self._data_received))

    def connect(self, timeout=10):
        if self._transport.is_connected():
            raise Exception("Transport already connected")

        self._transport.callback_register("connected", CalvinCB(self._send_join))
        self._transport.callback_register("disconnected", CalvinCB(self._disconnected))
        self._transport.callback_register("data", CalvinCB(self._data_received))
        # TODO: set timeout
        self._transport.join()

    def disconnect(self, timeout=10):
        # TODO: Set timepout
        if self._transport.is_connected():
            self._transport.disconnect()

    def is_connected(self):
        return self._transport.is_connected()

    def send(self, payload, timeout=None, coder=None):
        tcoder = coder or self._coder
        try:
            _log.debug('send_message %s => %s "%s"' % (self._rt_id, self._remote_rt_id, payload))
            self._callback_execute('send_message', self, payload)
            # Send
            raw_payload = tcoder.encode(payload)

#            _log.debug('raw_send_message %s => %s "%s"' % (self._rt_id, self._remote_rt_id, raw_payload))
            self._callback_execute('raw_send_message', self, raw_payload)
            self._transport.send(raw_payload)
            # TODO: Set timeout of send
            return True
        except:
            _log.exception("Send message failed!!")
            _log.error("Payload = '%s'" % repr(payload))
        return False

    def _get_join_coder(self):
        return self.get_coders()['json']

    def _get_msg_uuid(self):
        return calvinuuid.uuid("MSGID")

    def _send_join(self):
        self._callback_execute('peer_connected', self, self.get_uri())
        msg = _join_request
        msg['id'] = self._rt_id
        msg['sid'] = self._get_msg_uuid()
        msg['serializers'] = self.get_coders().keys()
        self.send(msg, coder=self._get_join_coder())

    def _send_join_reply(self, _id, serializer, sid):
        msg = _join_request_reply
        msg['id'] = self._rt_id
        msg['sid'] = sid
        msg['serializer'] = serializer
        self.send(msg, coder=self._get_join_coder())

    def _handle_join(self, data):
        try:
            data_obj = self._get_join_coder().decode(data)
            coder_name = None
            # Verify package
            if 'cmd' not in data_obj or data_obj['cmd'] != 'JOIN_REQUEST' or \
               'serializers' not in data_obj or 'id' not in data_obj or 'sid' not in data_obj:
                raise Exception('Not a valid package "%s"' % data_obj)

            sid = data_obj['sid']

            for coder in self.get_coders():
                if coder in data_obj['serializers']:
                    self._coder = self.get_coders()[coder]
                    coder_name = coder
                    break

            # Verify remote
            valid = self._verify_client(data_obj)
            # TODO: Callback or use join_finished
            if valid:
                self._remote_rt_id = data_obj['id']

        except:
            _log.exception("_handle_join: Failed!!")
            # TODO: disconnect ?
            return

        self._send_join_reply(not valid or self._rt_id, coder_name, sid)
        self._joined(False)

    def _joined(self, is_orginator):
        self._callback_execute('join_finished', self, self._remote_rt_id, self.get_uri(), is_orginator)

    def _handle_join_reply(self, data):
        try:
            data_obj = self.get_coders()['json'].decode(data)

            # Verify package and set local data
            if 'cmd' not in data_obj or data_obj['cmd'] != 'request_reply' or \
               'serializer' not in data_obj or 'id' not in data_obj or 'sid' not in data_obj:
                pass

            if data_obj['serializer'] in self.get_coders():
                self._coder = self.get_coders()[data_obj['serializer']]

            if data_obj['id'] is not None:
                # Request denied
                self._remote_rt_id = data_obj['id']
        except:
            _log.exception("_handle_join: Failed!!")
            # TODO: disconnect ?
            return

        self._joined(True)

    def _disconnected(self, reason):
        # TODO: unify reason
        self._callback_execute('peer_disconnected', self, self._remote_rt_id, reason)

    def _data_received(self, data):
        self._callback_execute('raw_data_received', self, data)
        if self._remote_rt_id is None:
            if self._incoming:
                self._handle_join(data)
            else:
                # We have not joined yet
                self._handle_join_reply(data)
            return

        # TODO: How to error this
        data_obj = None
        # decode
        try:
            data_obj = self._coder.decode(data)
        except:
            _log.exception("Message decode failed")
        self._callback_execute('data_received', self, data_obj)


class CalvinServer(base_transport.BaseServer):
    def __init__(self, rt_id, listen_uri, callbacks, server_transport, client_transport):
        super(CalvinServer, self).__init__(rt_id, listen_uri, callbacks=callbacks)
        self._rt_id = rt_id

        self._port = None
        self._peers = {}
        self._callbacks = callbacks

        # TODO: Get iface from addr and lookup host
        iface = ''

        self._transport = server_transport(iface=iface, port=self._listen_uri.port or 0)
        self._client_transport = client_transport

    def _started(self, port):
        self._port = port
        self._callback_execute('server_started', self, self._port)

    def _stopped(self):
        self._port = None
        self._callback_execute('server_stopped', self)
        # TODO: remove this ?
        # self._transport.callback_register('peer_connected', CalvinCB(self._peer_connected))

    def _client_connected(self, uri, protocol):
        """
            Callback when the client connects still needs a join to be finnshed
            before we can callback upper layers
        """
        tp = CalvinTransport(self._rt_id, uri, self._callbacks,
                             self._client_transport, proto=protocol)

        self._callback_execute('peer_connected', tp, tp.get_uri())

        self._peers[uri] = tp

    def start(self):
        # These should come from us
        self._transport.callback_register('server_started', CalvinCB(self._started))
        self._transport.callback_register('server_stopped', CalvinCB(self._stopped))
        self._transport.callback_register('client_connected', CalvinCB(self._client_connected))

        # Start the server
        self._port = self._transport.start()

    def stop(self):
        return self._transport.stop()

    def is_listening(self):
        return self._transport.is_listening()
