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
from requests import Response
import json
try:
    from requests_futures.sessions import FuturesSession
    session = FuturesSession(max_workers=10)
except:
    session = None

future_responses = []

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

#default timeout
TIMEOUT=5

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


class RT():
    def __init__(self, control_uri):
        self.control_uri = control_uri

def get_RT(value):
    if isinstance(value, basestring):
        return RT(value)
    else:
        return value

def check_response(response, success=range(200, 207), key=None):
    if isinstance(response, Response):
        if response.status_code in success:
            try:
                r = json.loads(response.text)
                return r if key is None else r[key]
            except:
                return None
        # When failed raise exception
        raise Exception("%d" % response.status_code)
    else:
        # We have a async Future just return it
        response._calvin_key = key
        response._calvin_success = success
        future_responses.append(response)
        return response

def async_response(response):
    try:
        future_responses.remove(response)
    except:
        pass
    r = response.result()
    return check_response(r, response._calvin_success, response._calvin_key)

def async_block():
    fr = future_responses[:]
    exceptions = []
    for r in fr:
        try:
            async_response(r)
        except Exception as e:
            exceptions.append(e)
    if exceptions:
        raise Exception(max(exceptions))

def get_node_id(rt, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    r = req.get(rt.control_uri + '/id', timeout=timeout)
    return check_response(r, key="id")


def get_node(rt, node_id, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    r = req.get(rt.control_uri + '/node/' + node_id, timeout=timeout)
    return check_response(r)


def quit(rt, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    r = req.delete(rt.control_uri + '/node', timeout=timeout)
    return check_response(r)


def get_nodes(rt, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    return check_response(req.get(rt.control_uri + '/nodes', timeout=timeout))


def peer_setup(rt, *peers, **kwargs):
    rt = get_RT(rt)
    timeout = kwargs.get('timeout', TIMEOUT)
    async = kwargs.get('async', False)
    if not isinstance(peers[0], type("")):
        peers = peers[0]
    if async:
        req = session
    else:
        req = requests
    r = req.post(
        rt.control_uri + '/peer_setup', data=json.dumps({'peers': peers}), timeout=timeout)
    return check_response(r)


def new_actor(rt, actor_type, actor_name, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    data = {'actor_type': actor_type, 'args': {
        'name': actor_name}, 'deploy_args': None}
    if async:
        req = session
    else:
        req = requests
    r = req.post(rt.control_uri + '/actor', data=json.dumps(data), timeout=timeout)
    result = check_response(r, key='actor_id')
    return result


def new_actor_wargs(rt, actor_type, actor_name, args=None, deploy_args=None, timeout=TIMEOUT, async=False, **kwargs):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    if args is None:
        kwargs['name'] = actor_name
        r = req.post(rt.control_uri + '/actor', data=json.dumps(
            {'actor_type': actor_type, 'deploy_args': deploy_args, 'args': kwargs}))
    else:
        r = req.post(rt.control_uri + '/actor', data=json.dumps(
            {'actor_type': actor_type, 'deploy_args': deploy_args, 'args': args}), timeout=timeout)
    result = check_response(r, key='actor_id')
    return result


def get_actor(rt, actor_id, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    r = req.get(rt.control_uri + '/actor/' + actor_id, timeout=timeout)
    return check_response(r)


def get_actors(rt, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    r = req.get(rt.control_uri + '/actors', timeout=timeout)
    return check_response(r)


def delete_actor(rt, actor_id, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    r = req.delete(rt.control_uri + '/actor/' + actor_id, timeout=timeout)
    return check_response(r)


def connect(rt, actor_id, port_name, peer_node_id, peer_actor_id, peer_port_name, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    data = {'actor_id': actor_id, 'port_name': port_name, 'port_dir': 'in', 'peer_node_id': peer_node_id,
            'peer_actor_id': peer_actor_id, 'peer_port_name': peer_port_name, 'peer_port_dir': 'out'}
    if async:
        req = session
    else:
        req = requests
    r = req.post(rt.control_uri + '/connect', data=json.dumps(data), timeout=timeout)
    return check_response(r)


def disconnect(rt, actor_id=None, port_name=None, port_dir=None, port_id=None, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    data = {'actor_id': actor_id, 'port_name': port_name,
            'port_dir': port_dir, 'port_id': port_id}
    if async:
        req = session
    else:
        req = requests
    r = req.post(rt.control_uri + '/disconnect', json.dumps(data), timeout=timeout)
    return check_response(r)


def disable(rt, actor_id, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    r = req.post(rt.control_uri + '/actor/' + actor_id + '/disable', timeout=timeout)
    return check_response(r)


def migrate(rt, actor_id, dst_id, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    data = {'peer_node_id': dst_id}
    if async:
        req = session
    else:
        req = requests
    r = req.post(
        rt.control_uri + '/actor/' + actor_id + "/migrate", data=json.dumps(data), timeout=timeout)
    return check_response(r)

def add_requirements(rt, application_id, reqs, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    data = {'reqs': reqs}
    if async:
        req = session
    else:
        req = requests
    r = req.post(
        rt.control_uri + '/application/' + application_id + "/migrate", data=json.dumps(data), timeout=timeout)
    return check_response(r)


def get_port(rt, actor_id, port_id, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    r = req.get(
        rt.control_uri + "/actor/" + actor_id + '/port/' + port_id, timeout=timeout)
    return check_response(r)


def set_port_property(rt, actor_id, port_type, port_name, port_property, value, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    data = {'actor_id': actor_id, 'port_type': port_type, 'port_name':
            port_name, 'port_property': port_property, 'value': value}
    if async:
        req = session
    else:
        req = requests
    r = req.post(
        rt.control_uri + '/set_port_property', data=json.dumps(data), timeout=timeout)
    return check_response(r)


def report(rt, actor_id, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    r = req.get(rt.control_uri + '/actor/' + actor_id + '/report', timeout=timeout)
    return check_response(r)


def get_applications(rt, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    r = req.get(rt.control_uri + '/applications', timeout=timeout)
    return check_response(r)


def get_application(rt, application_id, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    r = req.get(rt.control_uri + '/application/' + application_id, timeout=timeout)
    return check_response(r)


def delete_application(rt, application_id, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    r = req.delete(rt.control_uri + '/application/' + application_id, timeout=timeout)
    return check_response(r)

def deploy_application(rt, name, script, check=True, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    data = {"name": name, "script": script, "check": check}
    if async:
        req = session
    else:
        req = requests
    r = req.post(rt.control_uri + "/deploy", data=json.dumps(data), timeout=timeout)
    return check_response(r)


def add_index(rt, index, value, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    data = {'value': value}
    if async:
        req = session
    else:
        req = requests
    r = req.post(rt.control_uri + '/index/' + index, data=json.dumps(data), timeout=timeout)
    return check_response(r)


def remove_index(rt, index, value, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    data = {'value': value}
    if async:
        req = session
    else:
        req = requests
    r = req.delete(rt.control_uri + '/index/' + index, data=json.dumps(data), timeout=timeout)
    return check_response(r)


def get_index(rt, index, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    r = req.get(rt.control_uri + '/index/' + index, timeout=timeout)
    return check_response(r)

def get_storage(rt, key, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    if async:
        req = session
    else:
        req = requests
    r = req.get(rt.control_uri + '/storage/' + key, timeout=timeout)
    return check_response(r)

def set_storage(rt, key, value, timeout=TIMEOUT, async=False):
    rt = get_RT(rt)
    data = {'value': value}
    if async:
        req = session
    else:
        req = requests
    r = req.post(rt.control_uri + '/storage/' + key, data=json.dumps(data), timeout=timeout)
    return check_response(r)
