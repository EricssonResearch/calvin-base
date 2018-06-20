# -*- coding: utf-8 -*-

# Copyright (c) 2018 Ericsson AB
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

import json
import time
from calvin.requests import calvinresponse
from calvin.utilities import calvinuuid
from routes import register, handler
from authentication import authentication_decorator

LOG_ACTOR_FIRING = 0
LOG_ACTION_RESULT = 1
LOG_ACTOR_NEW = 2
LOG_ACTOR_DESTROY = 3
LOG_ACTOR_MIGRATE = 4
LOG_APPLICATION_NEW = 5
LOG_APPLICATION_DESTROY = 6
LOG_LINK_CONNECTED = 7
LOG_LINK_DISCONNECTED = 8
LOG_ACTOR_REPLICATE = 9
LOG_ACTOR_DEREPLICATE = 10
LOG_LOG_MESSAGE = 11


class Logger(object):

    """ Log object
    """

    def __init__(self, actors, events):
        self.handle = None
        self.connection = None
        self.actors = actors
        self.events = events

    def set_connection(self, handle, connection):
        self.handle = handle
        self.connection = connection

#
# Override a number of stub methods with real implementations
#
@register
def log_actor_firing(self, actor_id, action_method, tokens_produced, tokens_consumed, production):
    """ Trace actor firing
    """
    disconnected = []
    for user_id, logger in self.loggers.iteritems():
        if not logger.events or LOG_ACTOR_FIRING in logger.events:
            if not logger.actors or actor_id in logger.actors:
                data = {}
                data['timestamp'] = time.time()
                data['node_id'] = self.node.id
                data['type'] = 'actor_fire'
                data['actor_id'] = actor_id
                data['action_method'] = action_method
                data['produced'] = tokens_produced
                data['consumed'] = tokens_consumed
                if LOG_ACTION_RESULT in logger.events:
                    data['action_result'] = production
                if logger.connection is not None:
                    if not logger.connection.connection_lost:
                        logger.connection.send("data: %s\n\n" % json.dumps(data))
                    else:
                        disconnected.append(user_id)
                elif self.tunnel_client is not None and logger.handle is not None:
                    msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                    self.tunnel_client.send(msg)
    for user_id in disconnected:
        del self.loggers[user_id]

@register
def log_actor_new(self, actor_id, actor_name, actor_type, is_shadow):
    """ Trace actor new
    """
    disconnected = []
    for user_id, logger in self.loggers.iteritems():
        if not logger.events or LOG_ACTOR_NEW in logger.events:
            if not logger.actors or actor_id in logger.actors:
                data = {}
                data['timestamp'] = time.time()
                data['node_id'] = self.node.id
                data['type'] = 'actor_new'
                data['actor_id'] = actor_id
                data['actor_name'] = actor_name
                data['actor_type'] = actor_type
                data['is_shadow'] = is_shadow
                if logger.connection is not None:
                    if not logger.connection.connection_lost:
                        logger.connection.send("data: %s\n\n" % json.dumps(data))
                    else:
                        disconnected.append(user_id)
                elif self.tunnel_client is not None and logger.handle is not None:
                    msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                    self.tunnel_client.send(msg)
    for user_id in disconnected:
        del self.loggers[user_id]

@register
def log_actor_destroy(self, actor_id):
    """ Trace actor destroy
    """
    disconnected = []
    for user_id, logger in self.loggers.iteritems():
        if not logger.events or LOG_ACTOR_DESTROY in logger.events:
            if not logger.actors or actor_id in logger.actors:
                data = {}
                data['timestamp'] = time.time()
                data['node_id'] = self.node.id
                data['type'] = 'actor_destroy'
                data['actor_id'] = actor_id
                if logger.connection is not None:
                    if not logger.connection.connection_lost:
                        logger.connection.send("data: %s\n\n" % json.dumps(data))
                    else:
                        disconnected.append(user_id)
                elif self.tunnel_client is not None and logger.handle is not None:
                    msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                    self.tunnel_client.send(msg)
    for user_id in disconnected:
        del self.loggers[user_id]

@register
def log_actor_migrate(self, actor_id, dest_node_id):
    """ Trace actor migrate
    """
    disconnected = []
    for user_id, logger in self.loggers.iteritems():
        if not logger.events or LOG_ACTOR_MIGRATE in logger.events:
            if not logger.actors or actor_id in logger.actors:
                data = {}
                data['timestamp'] = time.time()
                data['node_id'] = self.node.id
                data['type'] = 'actor_migrate'
                data['actor_id'] = actor_id
                data['dest_node_id'] = dest_node_id
                if logger.connection is not None:
                    if not logger.connection.connection_lost:
                        logger.connection.send("data: %s\n\n" % json.dumps(data))
                    else:
                        disconnected.append(user_id)
                elif self.tunnel_client is not None and logger.handle is not None:
                    msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                    self.tunnel_client.send(msg)
    for user_id in disconnected:
        del self.loggers[user_id]

@register
def log_actor_replicate(self, actor_id, replica_actor_id, replication_id, dest_node_id):
    """ Trace actor replication
    """
    disconnected = []
    for user_id, logger in self.loggers.iteritems():
        if not logger.events or LOG_ACTOR_REPLICATE in logger.events:
            if not logger.actors or actor_id in logger.actors:
                data = {}
                data['timestamp'] = time.time()
                data['node_id'] = self.node.id
                data['type'] = 'actor_replicate'
                data['actor_id'] = actor_id
                data['dest_node_id'] = dest_node_id
                data['replication_id'] = replication_id
                data['replica_actor_id'] = replica_actor_id
                if logger.connection is not None:
                    if not logger.connection.connection_lost:
                        logger.connection.send("data: %s\n\n" % json.dumps(data))
                    else:
                        disconnected.append(user_id)
                elif self.tunnel_client is not None and logger.handle is not None:
                    msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                    self.tunnel_client.send(msg)
    for user_id in disconnected:
        del self.loggers[user_id]

@register
def log_actor_dereplicate(self, actor_id, replica_actor_id, replication_id):
    """ Trace actor dereplication
    """
    disconnected = []
    for user_id, logger in self.loggers.iteritems():
        if not logger.events or LOG_ACTOR_DEREPLICATE in logger.events:
            if not logger.actors or actor_id in logger.actors:
                data = {}
                data['timestamp'] = time.time()
                data['node_id'] = self.node.id
                data['type'] = 'actor_dereplicate'
                data['actor_id'] = actor_id
                data['replication_id'] = replication_id
                data['replica_actor_id'] = replica_actor_id
                if logger.connection is not None:
                    if not logger.connection.connection_lost:
                        logger.connection.send("data: %s\n\n" % json.dumps(data))
                    else:
                        disconnected.append(user_id)
                elif self.tunnel_client is not None and logger.handle is not None:
                    msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                    self.tunnel_client.send(msg)
    for user_id in disconnected:
        del self.loggers[user_id]

@register
def log_application_new(self, application_id, application_name):
    """ Trace application new
    """
    disconnected = []
    for user_id, logger in self.loggers.iteritems():
        if not logger.events or LOG_APPLICATION_NEW in logger.events:
            data = {}
            data['timestamp'] = time.time()
            data['node_id'] = self.node.id
            data['type'] = 'application_new'
            data['application_id'] = application_id
            data['application_name'] = application_name
            if logger.connection is not None:
                if not logger.connection.connection_lost:
                    logger.connection.send("data: %s\n\n" % json.dumps(data))
                else:
                    disconnected.append(user_id)
            elif self.tunnel_client is not None and logger.handle is not None:
                msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                self.tunnel_client.send(msg)
    for user_id in disconnected:
        del self.loggers[user_id]

@register
def log_application_destroy(self, application_id):
    """ Trace application destroy
    """
    disconnected = []
    for user_id, logger in self.loggers.iteritems():
        if not logger.events or LOG_APPLICATION_DESTROY in logger.events:
            data = {}
            data['timestamp'] = time.time()
            data['node_id'] = self.node.id
            data['type'] = 'application_destroy'
            data['application_id'] = application_id
            if logger.connection is not None:
                if not logger.connection.connection_lost:
                    logger.connection.send("data: %s\n\n" % json.dumps(data))
                else:
                    disconnected.append(user_id)
            elif self.tunnel_client is not None and logger.handle is not None:
                msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                self.tunnel_client.send(msg)
    for user_id in disconnected:
        del self.loggers[user_id]

@register
def log_link_connected(self, peer_id, uri):
    """ Trace node connect
    """
    disconnected = []
    for user_id, logger in self.loggers.iteritems():
        if not logger.events or LOG_LINK_CONNECTED in logger.events:
            data = {}
            data['timestamp'] = time.time()
            data['node_id'] = self.node.id
            data['type'] = 'link_connected'
            data['peer_id'] = peer_id
            data['uri'] = uri
            if logger.connection is not None:
                if not logger.connection.connection_lost:
                    logger.connection.send("data: %s\n\n" % json.dumps(data))
                else:
                    disconnected.append(user_id)
            elif self.tunnel_client is not None and logger.handle is not None:
                msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                self.tunnel_client.send(msg)
    for user_id in disconnected:
        del self.loggers[user_id]

@register
def log_link_disconnected(self, peer_id):
    """ Trace node connect
    """
    disconnected = []
    for user_id, logger in self.loggers.iteritems():
        if not logger.events or LOG_LINK_DISCONNECTED in logger.events:
            data = {}
            data['timestamp'] = time.time()
            data['node_id'] = self.node.id
            data['type'] = 'link_disconnected'
            data['peer_id'] = peer_id
            if logger.connection is not None:
                if not logger.connection.connection_lost:
                    logger.connection.send("data: %s\n\n" % json.dumps(data))
                else:
                    disconnected.append(user_id)
            elif self.tunnel_client is not None and logger.handle is not None:
                msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                self.tunnel_client.send(msg)
    for user_id in disconnected:
        del self.loggers[user_id]

@register
def log_log_message(self, message):
    """ Log message that is displayed at listener
    """
    disconnected = []
    for user_id, logger in self.loggers.iteritems():
        if not logger.events or LOG_LOG_MESSAGE in logger.events:
            data = {}
            data['timestamp'] = time.time()
            data['node_id'] = self.node.id
            data['type'] = 'log_message'
            data['msg'] = message
            if logger.connection is not None:
                if not logger.connection.connection_lost:
                    logger.connection.send("data: %s\n\n" % json.dumps(data))
                else:
                    disconnected.append(user_id)
            elif self.tunnel_client is not None and logger.handle is not None:
                msg = {"cmd": "logevent", "msgid": logger.handle, "header": None, "data": "data: %s\n\n" % json.dumps(data)}
                self.tunnel_client.send(msg)
    for user_id in disconnected:
        del self.loggers[user_id]


@handler(method="POST", path="/log")
@authentication_decorator
def handle_post_log(self, handle, connection, match, data, hdr):
    """
    POST /log
    Register for log events and set actor and event filter.
    Body:
    {
        'user_id': <user_id>     # Optional user id
        'actors': [<actor-id>],  # Actors to log, empty list for all
        'events': [<event_type>] # Event types to log: actor_firing, action_result,
                                                       actor_new, actor_destroy, actor_migrate,
                                                       application_new, application_destroy
    }
    Response status code: OK or BAD_REQUEST
    Response:
    {
        'user_id': <user_id>,
        'epoch_year': <the year the epoch starts at Jan 1 00:00, e.g. 1970>
    }
    """
    status = calvinresponse.OK
    actors = []
    events = []

    if data and 'user_id' in data:
        user_id = data['user_id']
    else:
        user_id = calvinuuid.uuid("TRACE")

    if user_id not in self.loggers:
        if 'actors' in data and data['actors']:
            actors = data['actors']
        if 'events' in data:
            events = []
            for event in data['events']:
                if event == 'actor_firing':
                    events.append(LOG_ACTOR_FIRING)
                elif event == 'action_result':
                    events.append(LOG_ACTION_RESULT)
                elif event == 'actor_new':
                    events.append(LOG_ACTOR_NEW)
                elif event == 'actor_destroy':
                    events.append(LOG_ACTOR_DESTROY)
                elif event == 'actor_migrate':
                    events.append(LOG_ACTOR_MIGRATE)
                elif event == 'actor_replicate':
                    events.append(LOG_ACTOR_REPLICATE)
                elif event == 'actor_dereplicate':
                    events.append(LOG_ACTOR_DEREPLICATE)
                elif event == 'application_new':
                    events.append(LOG_APPLICATION_NEW)
                elif event == 'application_destroy':
                    events.append(LOG_APPLICATION_DESTROY)
                elif event == 'link_connected':
                    events.append(LOG_LINK_CONNECTED)
                elif event == 'link_disconnected':
                    events.append(LOG_LINK_DISCONNECTED)
                elif event == 'log_message':
                    events.append(LOG_LOG_MESSAGE)
                else:
                    status = calvinresponse.BAD_REQUEST
                    break
        if status == calvinresponse.OK:
            self.loggers[user_id] = Logger(actors=actors, events=events)
    else:
        status = calvinresponse.BAD_REQUEST

    self.send_response(handle, connection,
                       json.dumps({'user_id': user_id, 'epoch_year': time.gmtime(0).tm_year})
                       if status == calvinresponse.OK else None,
                       status=status)


@handler(method="DELETE", path="/log/{trace_id}")
@authentication_decorator
def handle_delete_log(self, handle, connection, match, data, hdr):
    """
    DELETE /log/{user-id}
    Unregister for trace
    data
    Response status code: OK or NOT_FOUND
    """
    if match.group(1) in self.loggers:
        del self.loggers[match.group(1)]
        status = calvinresponse.OK
    else:
        status = calvinresponse.NOT_FOUND
    self.send_response(handle, connection, None, status=status)

@handler(method="GET", path="/log/{trace_id}")
@authentication_decorator
def handle_get_log(self, handle, connection, match, data, hdr):
    """
    GET /log/{user-id}
    Get streamed log
    events
    Response status code: OK or NOT_FOUND
    Content-Type: text/event-stream
    data:
    {
        'timestamp': <timestamp>,
        'node_id': <node_id>,
        'type': <event_type>, # event types: actor_fire, actor_new, actor_destroy, actor_migrate, application_new, application_destroy
        'actor_id',           # included in: actor_fire, actor_new, actor_destroy, actor_migrate
        'actor_name',         # included in: actor_new
        'actor_is_shadow'     # included in: actor_new
        'action_method',      # included in: actor_fire
        'consumed',           # included in: actor_fire
        'produced'            # included in: actor_fire
        'action_result'       # included in: actor_fire
        'actor_type',         # included in: actor_new
        'dest_node_id',       # included in: actor_migrate
        'application_name',   # included in: application_new
        'application_id'      # included in: application, application_destroy
    }
    """
    if match.group(1) in self.loggers:
        self.loggers[match.group(1)].set_connection(handle, connection)
        self.send_streamheader(handle, connection)
    else:
        self.send_response(handle, connection, None, calvinresponse.NOT_FOUND)
