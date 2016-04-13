# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 Ericsson AB
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
import requests
import inspect

from functools import partial
from requests import Response

try:
    from requests_futures.sessions import FuturesSession
    session = FuturesSession(max_workers=10)
except:
    session = None

from calvin.utilities.calvinlogger import get_logger

DEFAULT_TIMEOUT = 5

_log = get_logger(__name__)

# PATHS
NODE_PATH = '/node/{}'
NODE = '/node'
NODES = '/nodes'
NODE_ID = '/id'
PEER_SETUP = '/peer_setup'
ACTOR = '/actor'
ACTOR_PATH = '/actor/{}'
ACTORS = '/actors'
ACTOR_DISABLE = '/actor/{}/disable'
ACTOR_MIGRATE = '/actor/{}/migrate'
APPLICATION_PATH = '/application/{}'
APPLICATION_MIGRATE = '/application/{}/migrate'
ACTOR_PORT = '/actor/{}/{}'
ACTOR_REPORT = '/actor/{}/report'
SET_PORT_PROPERTY = '/set_port_property'
APPLICATIONS = '/applications'
DEPLOY = '/deploy'
CONNECT = '/connect'
DISCONNECT = '/disconnect'
INDEX_PATH = '/index/{}'
STORAGE_PATH = '/storage/{}'
METER = '/meter'
METER_PATH = '/meter/{}'
METER_PATH_TIMED = '/meter/{}/timed'
METER_PATH_AGGREGATED = '/meter/{}/aggregated'
METER_PATH_METAINFO = '/meter/{}/metainfo'


def get_runtime(value):
    if isinstance(value, basestring):
        return RT(value)
    else:
        return value


class RT(object):
    def __init__(self, control_uri):
        self.control_uri = control_uri


class RequestHandler(object):
    def __init__(self):
        self.future_responses = []

    def check_response(self, response, success=range(200, 207), key=None):
        if isinstance(response, Response):
            if response.status_code in success:
                try:
                    r = json.loads(response.text)
                    return r if key is None else r[key]
                except:
                    _log.debug("Failed to parse response '{}' as json".format(response.text))
                    return None
            # When failed raise exception
            raise Exception("%d%s" % (response.status_code, ("\n" + response.text) if response.text else ""))
        else:
            # We have a async Future just return it
            response._calvin_key = key
            response._calvin_success = success
            self.future_responses.append(response)
            return response

    def _send(self, rt, timeout, send_func, path, data=None):
        rt = get_runtime(rt)
        if data is not None:
            return send_func(rt.control_uri + path, timeout=timeout, data=json.dumps(data))
        else:
            return send_func(rt.control_uri + path, timeout=timeout)

    def _get(self, rt, timeout, async, path):
        req = session if async else requests
        return self._send(rt, timeout, req.get, path)

    def _post(self, rt, timeout, async, path, data=None):
        req = session if async else requests
        return self._send(rt, timeout, req.post, path, data)

    def _delete(self, rt, timeout, async, path, data=None):
        req = session if async else requests
        return self._send(rt, timeout, req.delete, path, data)

    def get_node_id(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, NODE_ID)
        return self.check_response(r, key="id")

    def get_node(self, rt, node_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, NODE_PATH.format(node_id))
        return self.check_response(r)

    def quit(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._delete(rt, timeout, async, NODE)
        return self.check_response(r)

    def get_nodes(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, NODES)
        return self.check_response(r)

    def peer_setup(self, rt, *peers, **kwargs):
        timeout = kwargs.get('timeout', DEFAULT_TIMEOUT)
        async = kwargs.get('async', False)

        if not isinstance(peers[0], type("")):
            peers = peers[0]
        data = {'peers': peers}

        r = self._post(rt, timeout, async, PEER_SETUP, data)
        return self.check_response(r)

    def new_actor(self, rt, actor_type, actor_name, credentials=None, timeout=DEFAULT_TIMEOUT, async=False):
        data = {
            'actor_type': actor_type,
            'args': {'name': actor_name},
            'deploy_args': {'credentials': credentials} if credentials else None
        }

        r = self._post(rt, timeout, async, ACTOR, data)
        return self.check_response(r, key='actor_id')

    def new_actor_wargs(self, rt, actor_type, actor_name, args=None, deploy_args=None, timeout=DEFAULT_TIMEOUT,
                        async=False, **kwargs):
        data = {'actor_type': actor_type, 'deploy_args': deploy_args}

        if args is None:
            kwargs['name'] = actor_name
            data['args'] = kwargs
        else:
            data['args'] = args

        r = self._post(rt, timeout, async, ACTOR, data)
        return self.check_response(r, key='actor_id')

    def get_actor(self, rt, actor_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, ACTOR_PATH.format(actor_id))
        return self.check_response(r)

    def get_actors(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, ACTORS)
        return self.check_response(r)

    def delete_actor(self, rt, actor_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._delete(rt, timeout, async, ACTOR_PATH.format(actor_id))
        return self.check_response(r)

    def connect(self, rt, actor_id, port_name, peer_node_id, peer_actor_id, peer_port_name, timeout=DEFAULT_TIMEOUT,
                async=False):
        data = {
            'actor_id': actor_id,
            'port_name': port_name,
            'port_dir': 'in',
            'peer_node_id': peer_node_id,
            'peer_actor_id': peer_actor_id,
            'peer_port_name': peer_port_name,
            'peer_port_dir': 'out'
        }
        r = self._post(rt, timeout, async, CONNECT, data)
        return self.check_response(r)

    def disconnect(self, rt, actor_id=None, port_name=None, port_dir=None, port_id=None, timeout=DEFAULT_TIMEOUT,
                   async=False):
        data = {
            'actor_id': actor_id,
            'port_name': port_name,
            'port_dir': port_dir,
            'port_id': port_id
        }
        r = self._post(rt, timeout, async, DISCONNECT, data)
        return self.check_response(r)

    def disable(self, rt, actor_id, timeout=DEFAULT_TIMEOUT, async=False):
        path = ACTOR_DISABLE.format(actor_id)
        r = self._post(rt, timeout, async, path)
        return self.check_response(r)

    def migrate(self, rt, actor_id, dst_id, timeout=DEFAULT_TIMEOUT, async=False):
        data = {'peer_node_id': dst_id}
        path = ACTOR_MIGRATE.format(actor_id)
        r = self._post(rt, timeout, async, path, data)
        return self.check_response(r)

    def migrate_use_req(self, rt, actor_id, requirements, extend=False, move=False, timeout=DEFAULT_TIMEOUT,
                        async=False):
        data = {'requirements': requirements, 'extend': extend, 'move': move}
        path = ACTOR_MIGRATE.format(actor_id)
        r = self._post(rt, timeout, async, path, data)
        return self.check_response(r)


    def migrate_app_use_req(self, rt, application_id, deploy_info=None, move=False, timeout=DEFAULT_TIMEOUT,
                            async=False):
        data = {'deploy_info': deploy_info, "move": move}
        path = APPLICATION_MIGRATE.format(application_id)
        r = self._post(rt, timeout, async, path, data)
        return self.check_response(r)

    def get_port(self, rt, actor_id, port_id, timeout=DEFAULT_TIMEOUT, async=False):
        path = ACTOR_PORT.format(actor_id, port_id)
        r = self._get(rt, timeout, async, path)
        return self.check_response(r)

    def set_port_property(self, rt, actor_id, port_type, port_name, port_property, value, timeout=DEFAULT_TIMEOUT,
                          async=False):
        data = {
            'actor_id': actor_id,
            'port_type': port_type,
            'port_name': port_name,
            'port_property': port_property,
            'value': value
        }
        r = self._post(rt, timeout, async, SET_PORT_PROPERTY, data)
        return self.check_response(r)

    def report(self, rt, actor_id, timeout=DEFAULT_TIMEOUT, async=False):
        path = ACTOR_REPORT.format(actor_id)
        r = self._get(rt, timeout, async, path)
        return self.check_response(r)

    def get_applications(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, APPLICATIONS)
        return self.check_response(r)

    def get_application(self, rt, application_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, APPLICATION_PATH.format(application_id))
        return self.check_response(r)

    def delete_application(self, rt, application_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._delete(rt, timeout, async, APPLICATION_PATH.format(application_id))
        return self.check_response(r)

    def deploy_application(self, rt, name, script, deploy_info=None, credentials=None, content=None,
                           check=True, timeout=DEFAULT_TIMEOUT, async=False):
        data = {
            "name": name,
            "script": script,
            "sec_credentials": credentials,
            "deploy_info": deploy_info,
            "check": check
        }
        if content and 'sign' in content:
            data["sec_sign"] = {}
            for cert_hash, signature in content['sign'].iteritems():
                data["sec_sign"][cert_hash] = signature.encode('hex_codec')
        r = self._post(rt, timeout, async, DEPLOY, data)
        return self.check_response(r)

    def deploy_app_info(self, rt, name, app_info, deploy_info=None, credentials=None, check=True,
                        timeout=DEFAULT_TIMEOUT, async=False):
        data = {
            "name": name,
            "app_info": app_info,
            "sec_credentials": credentials,
            "deploy_info": deploy_info,
            "check": check
        }
        r = self._post(rt, timeout, async, DEPLOY, data=data)
        return self.check_response(r)

    def register_metering(self, rt, user_id=None, timeout=DEFAULT_TIMEOUT, async=False):
        data = {'user_id': user_id} if user_id else None
        r = self._post(rt, timeout, async, METER, data=data)
        return self.check_response(r)

    def unregister_metering(self, rt, user_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._delete(rt, timeout, async, METER_PATH.format(user_id))
        return self.check_response(r)

    def get_timed_metering(self, rt, user_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, METER_PATH_TIMED.format(user_id))
        return self.check_response(r)

    def get_aggregated_metering(self, rt, user_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, METER_PATH_AGGREGATED.format(user_id))
        return self.check_response(r)

    def get_actorinfo_metering(self, rt, user_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, METER_PATH_METAINFO.format(user_id))
        return self.check_response(r)

    def add_index(self, rt, index, value, timeout=DEFAULT_TIMEOUT, async=False):
        data = {'value': value}
        path = INDEX_PATH.format(index)
        r = self._post(rt, timeout, async, path, data)
        return self.check_response(r)

    def remove_index(self, rt, index, value, timeout=DEFAULT_TIMEOUT, async=False):
        data = {'value': value}
        path = INDEX_PATH.format(index)
        r = self._delete(rt, timeout, async, path, data)
        return self.check_response(r)

    def get_index(self, rt, index, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, INDEX_PATH.format(index))
        return self.check_response(r)

    def get_storage(self, rt, key, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, STORAGE_PATH.format(key))
        return self.check_response(r)

    def set_storage(self, rt, key, value, timeout=DEFAULT_TIMEOUT, async=False):
        data = {'value': value}
        path = STORAGE_PATH.format(key)
        r = self._post(rt, timeout, async, path, data)
        return self.check_response(r)

    def async_response(self, response):
        try:
            self.future_responses.remove(response)
        except:
            pass
        r = response.result()
        return self.check_response(r, response._calvin_success, response._calvin_key)

    def async_barrier(self):
        fr = self.future_responses[:]
        exceptions = []
        for r in fr:
            try:
                self.async_response(r)
            except Exception as e:
                exceptions.append(e)
        if exceptions:
            raise Exception(max(exceptions))


# Generate async_* versions of all functions in RequestHandler with async argument set to True
for func_name, func in inspect.getmembers(RequestHandler, predicate=inspect.ismethod):
    if ((hasattr(func, '__code__') and 'async' in func.__code__.co_varnames and
            func.__name__ not in ['_get', '_post', '_delete'])
            or func.__name__ == 'peer_setup'):
        setattr(RequestHandler, 'async_' + func_name, partial(func, async=True))
