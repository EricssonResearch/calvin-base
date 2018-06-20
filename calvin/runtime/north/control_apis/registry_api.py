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
import re
from calvin.requests import calvinresponse
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinlogger import get_logger
from routes import register, handler
from authentication import authentication_decorator
from calvin.utilities.attribute_resolver import format_index_string

_log = get_logger(__name__)

@handler(method="POST", path="/index/{path}")
@authentication_decorator
def handle_post_index(self, handle, connection, match, data, hdr):
    """
    POST /index/{key}
    Store value under index key
    Body:
    {
        "value": <string>,
        "root_prefix_level": <int>  # optional
    }
    Response status code: OK or INTERNAL_ERROR
    Response: none
    """
    kwargs = {}
    if 'root_prefix_level' in data:
        kwargs['root_prefix_level'] = int(data['root_prefix_level'])
    self.node.storage.add_index(
        match.group(1), data['value'], cb=CalvinCB(self.index_cb, handle, connection), **kwargs)

@handler(method="DELETE", path="/index/{path}")
@authentication_decorator
def handle_delete_index(self, handle, connection, match, data, hdr):
    """
    DELETE /index/{key}
    Remove value from index key
    Body:
    {
        "value": <string>
        "root_prefix_level": <int>  # optional
    }
    Response status code: OK or INTERNAL_ERROR
    Response: none
    """
    kwargs = {}
    if 'root_prefix_level' in data:
        kwargs['root_prefix_level'] = int(data['root_prefix_level'])
    self.node.storage.remove_index(
        match.group(1), data['value'], cb=CalvinCB(self.index_cb, handle, connection), **kwargs)


# Can't be access controlled, as it is needed to find authorization server
@handler(method="GET", path="/index/{path}", optional=[r"\?root_prefix_level=(\d+)"])
def handle_get_index(self, handle, connection, match, data, hdr):
    """
    GET /index/{key}?root_prefix_level={level}
    Fetch values under index key
    Response status code: OK or NOT_FOUND
    Response: {"result": <list of strings>}
    """
    kwargs = {}
    if match.group(3) is not None:
        kwargs['root_prefix_level'] = int(match.group(3))
    self.node.storage.get_index(
        match.group(1), cb=CalvinCB(self.get_index_cb, handle, connection), **kwargs)


@register
def index_cb(self, handle, connection, *args, **kwargs):
    """ Index operation response
    """
    _log.debug("index cb (in control) %s, %s" % (args, kwargs))
    if 'value' in kwargs:
        value = kwargs['value']
    else:
        value = None
    self.send_response(handle, connection, None,
                       status=calvinresponse.INTERNAL_ERROR if value is None else calvinresponse.OK)


@register
def get_index_cb(self, handle, connection, value, *args, **kwargs):
    """ Index operation response
    """
    _log.debug("get index cb (in control) %s" % (value))
    self.send_response(handle, connection, None if value is None else json.dumps({'result': value}),
                       status=calvinresponse.NOT_FOUND if value is None else calvinresponse.OK)


@handler(method="POST", path="/storage/{path}")
@authentication_decorator
def handle_post_storage(self, handle, connection, match, data, hdr):
    """
    POST /storage/{prefix-key}
    Store value under prefix-key
    Body:
    {
        "value": <string>
    }
    Response status code: OK or INTERNAL_ERROR
    Response: none
    """
    self.node.storage.set("", match.group(1), data['value'], cb=CalvinCB(self.index_cb, handle, connection))

@handler(method="GET", path="/storage/{path}")
@authentication_decorator
def handle_get_storage(self, handle, connection, match, data, hdr):
    """
    GET /storage/{prefix-key}
    Fetch value under prefix-key
    Response status code: OK or NOT_FOUND
    Response: {"result": <value>}
    """
    self.node.storage.get("", match.group(1), cb=CalvinCB(self.get_storage_cb, handle=handle, connection=connection))


@register
def get_storage_cb(self, key, value, handle, connection):
    missing = calvinresponse.isfailresponse(value)
    self.send_response(handle, connection, None if missing else json.dumps({'result': value}),
                       status=calvinresponse.NOT_FOUND if missing else calvinresponse.OK)


@handler(method="GET", path="/dumpstorage")
@authentication_decorator
def handle_dump_storage(self, handle, connection, match, data, hdr):
    """
    GET /dumpstorage
    Dump storage to temporary file in /tmp when available
    Response status code: OK
    Response: none
    """
    name = self.node.storage.dump()
    self.send_response(handle, connection, json.dumps(name), status=calvinresponse.OK)


#
# FIXME: These probably belongs in this API but I'm not completely sure
#
@register
def handle_post_node_attribute_indexed_public_cb(self, key, value, handle, connection, attributes):
    try:
        indexed_public = []
        for attr in attributes.items():
            indexed_string = format_index_string(attr)
            indexed_public.append(indexed_string)
            self.node.storage.add_index(indexed_string, key)
        value['attributes']['indexed_public'] = indexed_public
        self.node.storage.set(prefix="node-", key=key, value=value,
            cb=CalvinCB(self.index_cb, handle, connection))
    except Exception as e:
        _log.error("Failed to update node %s", e)
        self.send_response(handle, connection, None, status=calvinresponse.INTERNAL_ERROR)


@handler(method="POST", path="/node/{node_id}/attributes/indexed_public")
@authentication_decorator
def handle_post_node_attribute_indexed_public(self, handle, connection, match, data, hdr):
    """
    POST /node/{node-id}/attributes/indexed_public
    Set indexed_public attributes on node with node-id
    Body:
    {
        "node_name": {"organization": <organization>, "organizationalUnit": <organizationalUnit>, "purpose": <purpose>, "group": <group>, "name": <name>},
        "owner": {"organization": <organization>, "organizationalUnit": <organizationalUnit>, "role": <role>, "personOrGroup": <personOrGroup>},
        "address": {"country": <country>, "stateOrProvince": <stateOrProvince>, "locality": <locality>, "street": <street>, "streetNumber": <streetNumber>, "building": <building>, "floor": <floor>, "room": <room>}
    }
    Response status code: OK, UNAUTHORIZED or INTERNAL_ERROR
    """
    try:
        if match.group(1) == self.node.id:
            if self.node.runtime_credentials is None or self.node.runtime_credentials.domain is None:
                self.node.storage.remove_node_index(self.node)
                self.node.attributes.set_indexed_public(data)
                self.node_name = self.node.attributes.get_node_name_as_str()
                self.node.storage.add_node(self.node, CalvinCB(self.index_cb, handle, connection))
            else:
                self.send_response(handle, connection, None, status=calvinresponse.UNAUTHORIZED)
        else:
            self.node.storage.get_node(match.group(1), CalvinCB(
                func=self.handle_post_node_attribute_indexed_public_cb, handle=handle, connection=connection, attributes=data))
    except Exception as e:
        _log.error("Failed to update node %s", e)
        self.send_response(handle, connection, None, status=calvinresponse.INTERNAL_ERROR)


@register
def storage_cb(self, key, value, handle, connection):
    missing = calvinresponse.isfailresponse(value)
    self.send_response(handle, connection, None if missing else json.dumps(value),
                       status=calvinresponse.NOT_FOUND if missing else calvinresponse.OK)

@handler(method="GET", path="/node/{node_id}")
@authentication_decorator
def handle_get_node(self, handle, connection, match, data, hdr):
    """
    GET /node/{node-id}
    Get information on node node-id
    Response status code: OK or NOT_FOUND
    Response:
    {
        "attributes": {...},
        "control_uri": "http(s)://<address>:<controlport>",
        "uri": "calvinip://<address>:<port>"
    }
    """
    self.node.storage.get_node(match.group(1), CalvinCB(
        func=self.storage_cb, handle=handle, connection=connection))


@handler(method="GET", path="/application/{application_id}")
@authentication_decorator
def handle_get_application(self, handle, connection, match, data, hdr):
    """
    GET /application/{application-id}
    Get information on application application-id
    Response status code: OK or NOT_FOUND
    Response:
    {

         "origin_node_id": <node id>,
         "actors": <list of actor ids>
         "name": <name or id of this application>
    }
    """
    self.node.storage.get_application(match.group(1), CalvinCB(
        func=self.storage_cb, handle=handle, connection=connection))


@handler(method="GET", path="/actor/{actor_id}")
@authentication_decorator
def handle_get_actor(self, handle, connection, match, data, hdr):
    """
    GET /actor/{actor-id}
    Get information on actor
    Response status code: OK or NOT_FOUND
    Response:
    {

        "inports": list inports
        "node_id": <node-id>,
        "type": <actor type>,
        "name": <actor name>,
        "outports": list of outports
    }
    """
    self.node.storage.get_actor(match.group(1), CalvinCB(
        func=self.storage_cb, handle=handle, connection=connection))

# @authentication_decorator # Disabled in original code
@handler(method="GET", path="/actor/{actor_id}/port/{port_id}")
def handle_get_port(self, handle, connection, match, data, hdr):
    """
        GET /actor/{actor-id}/port/{port-id}
        Get information on port {port-id} of actor {actor-id}
        Response status code: OK or NOT_FOUND
    """
    self.node.storage.get_port(match.group(2), CalvinCB(
        func=self.storage_cb, handle=handle, connection=connection))

@handler(method="POST", path="/node/resource/", optional=["mem_avail", "cpu_avail", "memAvail", "cpuAvail"])
@authentication_decorator
def handle_resource_avail(self, handle, connection, match, data, hdr):
    """
    POST /node/resource/{mem_avail|cpu_avail}
    Updates {mem|cpu]} availability in the local node
    Body:
    {
        "value": <{RAM|CPU} avail (0,25,50,75,100)>
    }

    Note: memAvail, cpuAvail versions are deprecated. Use lowercase
    Response status code: OK, NOT_FOUND, INTERNAL_ERROR
    Response: none
    """
    if match.group(1) in ['mem_avail', "memAvail"]:
        self.node.mem_monitor.set_avail(data['value'], CalvinCB(self.index_cb, handle, connection))
    elif match.group(1) in ['cpu_avail', "cpuAvail"]:
        self.node.cpu_monitor.set_avail(data['value'], CalvinCB(self.index_cb, handle, connection))
    else:
        self.send_response(handle, connection, None, status=calvinresponse.NOT_FOUND)
