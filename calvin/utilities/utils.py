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

import os
import requests
import json


def get_local_ip():
    import socket
    return [(s.connect(('8.8.8.8', 80)), s.getsockname()[0], s.close())
            for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)


def ensure_path(d):
    if not os.path.exists(d):
        os.makedirs(d)


def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)


def uniq_list(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def get_node_id(rt):
    r = requests.get(rt.control_uri + '/id')
    return json.loads(r.text)["id"]


def get_node(rt, node_id):
    r = requests.get(rt.control_uri + '/node/' + node_id)
    return json.loads(r.text)


def quit(rt):
    r = requests.delete(rt.control_uri + '/node')
    return json.loads(r.text)


def get_nodes(rt):
    return json.loads(requests.get(rt.control_uri + '/nodes').text)


def peer_setup(rt, *peers):
    if not isinstance(peers[0], type("")):
        peers = peers[0]
    r = requests.post(
        rt.control_uri + '/peer_setup', data=json.dumps({'peers': peers}))
    return json.loads(r.text)


def new_actor(rt, actor_type, actor_name):
    data = {'actor_type': actor_type, 'args': {
        'name': actor_name}, 'deploy_args': None}
    r = requests.post(rt.control_uri + '/actor', data=json.dumps(data))
    result = json.loads(r.text)['actor_id']
    return result


def new_actor_wargs(rt, actor_type, actor_name, args=None, deploy_args=None, **kwargs):
    if args is None:
        kwargs['name'] = actor_name
        r = requests.post(rt.control_uri + '/actor', data=json.dumps(
            {'actor_type': actor_type, 'deploy_args': deploy_args, 'args': kwargs}))
    else:
        r = requests.post(rt.control_uri + '/actor', data=json.dumps(
            {'actor_type': actor_type, 'deploy_args': deploy_args, 'args': args}))
    result = json.loads(r.text)['actor_id']
    return result


def get_actor(rt, actor_id):
    r = requests.get(rt.control_uri + '/actor/' + actor_id)
    return json.loads(r.text)


def get_actors(rt):
    r = requests.get(rt.control_uri + '/actors')
    return json.loads(r.text)


def delete_actor(rt, actor_id):
    r = requests.delete(rt.control_uri + '/actor/' + actor_id)
    return json.loads(r.text)


def connect(rt, actor_id, port_name, peer_node_id, peer_actor_id, peer_port_name):
    data = {'actor_id': actor_id, 'port_name': port_name, 'port_dir': 'in', 'peer_node_id': peer_node_id,
            'peer_actor_id': peer_actor_id, 'peer_port_name': peer_port_name, 'peer_port_dir': 'out'}
    r = requests.post(rt.control_uri + '/connect', data=json.dumps(data))
    return json.loads(r.text)


def disconnect(rt, actor_id=None, port_name=None, port_dir=None, port_id=None):
    data = {'actor_id': actor_id, 'port_name': port_name,
            'port_dir': port_dir, 'port_id': port_id}
    r = requests.post(rt.control_uri + '/disconnect', json.dumps(data))
    return json.loads(r.text)


def disable(rt, actor_id):
    r = requests.post(rt.control_uri + '/actor/' + actor_id + '/disable')
    return json.loads(r.text)


def migrate(rt, actor_id, dst_id):
    data = {'peer_node_id': dst_id}
    r = requests.post(
        rt.control_uri + '/actor/' + actor_id + "/migrate", data=json.dumps(data))
    return json.loads(r.text)


def get_port(rt, actor_id, port_id):
    r = requests.get(
        rt.control_uri + "/actor/" + actor_id + '/port/' + port_id)
    return json.loads(r.text)


def set_port_property(rt, actor_id, port_type, port_name, port_property, value):
    data = {'actor_id': actor_id, 'port_type': port_type, 'port_name':
            port_name, 'port_property': port_property, 'value': value}
    r = requests.post(
        rt.control_uri + '/set_port_property', data=json.dumps(data))
    return json.loads(r.text)


def report(rt, actor_id):
    r = requests.get(rt.control_uri + '/actor/' + actor_id + '/report')
    return json.loads(r.text)


def get_applications(rt):
    r = requests.get(rt.control_uri + '/applications')
    return json.loads(r.text)


def get_application(rt, application_id):
    r = requests.get(rt.control_uri + '/application/' + application_id)
    return json.loads(r.text)


def delete_application(rt, application_id):
    r = requests.delete(rt.control_uri + '/application/' + application_id)
    return json.loads(r.text)
