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

# DEPRECATED

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
ACTOR_REPLICATE = '/actor/{}/replicate'
APPLICATION_PATH = '/application/{}'
APPLICATION_MIGRATE = '/application/{}/migrate'
ACTOR_PORT = '/actor/{}/port/{}'
ACTOR_REPORT = '/actor/{}/report'
SET_PORT_PROPERTY = '/set_port_property'
APPLICATIONS = '/applications'
DEPLOY = '/deploy'
CONNECT = '/connect'
DISCONNECT = '/disconnect'
INDEX_PATH_RPL = '/index/{}?root_prefix_level={}'
INDEX_PATH = '/index/{}'
STORAGE_PATH = '/storage/{}'

CSR_REQUEST = '/certificate_authority/certificate_signing_request'
ENROLLMENT_PASSWORD = '/certificate_authority/certificate_enrollment_password/{}'
AUTHENTICATION = '/authentication'
AUTHENTICATION_USERS_DB = '/authentication/users_db'
AUTHENTICATION_GROUPS_DB = '/authentication/groups_db'

PROXY_PEER_ABOLISH = '/proxy/{}/migrate'


class RequestBase(object):

    def __init__(self, verify=True):
        self.future_responses = []
        self.verify = verify
        self.credentials = None

    def set_credentials(self, credentials):
        if ('user' in credentials) and ('password' in credentials):
            self.credentials=(credentials['user'], credentials['password'])
        else:
            #TODO remove printing of the credentials in the log
            _log.error("Incorrectly formated credentials supplied, credentials={}".format(credentials))
            self.credentials=None

    def check_response(self, response, success=range(200, 207), key=None):
        if isinstance(response, Response):
            if response.status_code in success:
                if response.status_code == "204":
                    return
                if response.headers.get("content-type") == "application/json":
                    try:
                        r = json.loads(response.text)
                        return r if key is None else r[key]
                    except ValueError:
                        _log.error("Content-Type is %s, but failed to decode '{}' as json", response.text)
                        return None
                else:
                    # No content type return the text
                    return response.text
            # When failed raise exception
            raise Exception("%d%s" % (response.status_code, ("\n" + repr(response.text)) if response.text else ""))
        else:
            # FIXME: Don't just assume it's a future
            # We have a async Future just return it
            response._calvin_key = key
            response._calvin_success = success
            self.future_responses.append(response)
            return response

    def _send(self, host, timeout, send_func, path, data=None):
        _log.debug("Sending request %s, %s, %s", send_func, host + path, json.dumps(data))
        if data is None:
            return send_func(host + path, timeout=timeout, auth=self.credentials, verify=self.verify)
            # FIXME: Don't do data=json.dumps(data) since that is done implicitly by requests
        return send_func(host + path, timeout=timeout, data=json.dumps(data), auth=self.credentials, verify=self.verify)

    def _get(self, host, timeout, async, path, headers="", data=None):
        req = session if async else requests
        return self._send(host, timeout, req.get, path, data)

    def _post(self, host, timeout, async, path, data=None):
        req = session if async else requests
        return self._send(host, timeout, req.post, path, data)

    def _put(self, host, timeout, async, path, data=None):
        req = session if async else requests
        return self._send(host, timeout, req.put, path, data)

    def _delete(self, host, timeout, async, path, data=None):
        req = session if async else requests
        return self._send(host, timeout, req.delete, path, data)

    def async_response(self, response):
        try:
            self.future_responses.remove(response)
        except Exception as e:
            _log.warning("Async responce exception %s", e)
            _log.debug("Async responce exception %s", e, exc_info=True)
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


        
def get_runtime(value):
    if isinstance(value, basestring):
        return RT(value)
    else:
        return value


class RT(object):
    
    def __init__(self, control_uri):
        self.control_uri = control_uri


class RequestHandler(RequestBase):
    """docstring for RequestHandler"""
    def __init__(self, verify=True):
        super(RequestHandler, self).__init__(verify)        

    # FIXME: Shouldn't this be part of the RequestBase class?
    def __getattr__(self, name):
        if name.startswith("async_"):
            func = name[6:]
            return partial(getattr(self, func), async=True)
        else:
            raise AttributeError("Unknown request handler attribute %s" % name)
            
    def _send(self, rt, timeout, send_func, path, data=None):
        rt = get_runtime(rt)
        return RequestBase._send(self, rt.control_uri, timeout, send_func, path, data)    

    # cscontrol, nodecontrol
    def get_node_id(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, NODE_ID)
        return self.check_response(r, key="id")

    # cscontrol, nodecontrol
    def get_node(self, rt, node_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, NODE_PATH.format(node_id))
        return self.check_response(r)

    # cscontrol
    def quit(self, rt, method=None, timeout=DEFAULT_TIMEOUT, async=False):
        if method is None:
            r = self._delete(rt, timeout, async, NODE)
        else:
            r = self._delete(rt, timeout, async, NODE_PATH.format(method))
        return self.check_response(r)

    # cscontrol
    def get_nodes(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, NODES)
        return self.check_response(r)

    # cscontrol
    def peer_setup(self, rt, *peers, **kwargs):
        timeout = kwargs.get('timeout', DEFAULT_TIMEOUT)
        async = kwargs.get('async', False)

        if not isinstance(peers[0], type("")):
            peers = peers[0]
        data = {'peers': peers}

        r = self._post(rt, timeout, async, PEER_SETUP, data)
        return self.check_response(r)

    def get_actor(self, rt, actor_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, ACTOR_PATH.format(actor_id))
        return self.check_response(r)

    def get_actors(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, ACTORS)
        return self.check_response(r)

    # cscontrol
    def migrate(self, rt, actor_id, dst_id, timeout=DEFAULT_TIMEOUT, async=False):
        data = {'peer_node_id': dst_id}
        path = ACTOR_MIGRATE.format(actor_id)
        r = self._post(rt, timeout, async, path, data)
        return self.check_response(r)

    # cscontrol
    def replicate(self, rt, replication_id=None, dst_id=None, dereplicate=False, exhaust=False, requirements=None, timeout=DEFAULT_TIMEOUT, async=False):
        data = {}
        if dst_id:
            data['peer_node_id'] = dst_id
        if dereplicate:
            data['dereplicate'] = dereplicate
        if exhaust:
            data['exhaust'] = exhaust
        if requirements is not None:
            data['requirements'] = requirements
        if not data:
            data = None
        path = ACTOR_REPLICATE.format(replication_id)
        r = self._post(rt, timeout, async, path, data)
        return self.check_response(r)

    # cscontrol
    def migrate_use_req(self, rt, actor_id, requirements, extend=False, move=False, timeout=DEFAULT_TIMEOUT,
                        async=False):
        data = {'requirements': requirements, 'extend': extend, 'move': move}
        path = ACTOR_MIGRATE.format(actor_id)
        r = self._post(rt, timeout, async, path, data)
        return self.check_response(r)

    # cscontrol
    def migrate_app_use_req(self, rt, application_id, deploy_info=None, move=False, timeout=DEFAULT_TIMEOUT,
                            async=False):
        data = {'deploy_info': deploy_info, "move": move}
        path = APPLICATION_MIGRATE.format(application_id)
        r = self._post(rt, timeout, async, path, data)
        return self.check_response(r)

    # kappa
    def report(self, rt, actor_id, kwargs=None, timeout=DEFAULT_TIMEOUT, async=False):
        path = ACTOR_REPORT.format(actor_id)
        if kwargs:
            r = self._post(rt, timeout, async, path, kwargs)
        else:
            r = self._get(rt, timeout, async, path)
        return self.check_response(r)

    # cscontrol
    def get_applications(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, APPLICATIONS)
        return self.check_response(r)

    # cscontrol
    def get_application(self, rt, application_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, APPLICATION_PATH.format(application_id))
        return self.check_response(r)

    # cscontrol
    def delete_application(self, rt, application_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._delete(rt, timeout, async, APPLICATION_PATH.format(application_id))
        return self.check_response(r)

    # cscontrol
    def deploy(self, rt, deployable, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._post(rt, timeout, False, DEPLOY, data=deployable)
        return self.check_response(r)

    # cscontrol, utilities.security, utilities.runtime_credentials
    def get_index(self, rt, index, root_prefix_level=None, timeout=DEFAULT_TIMEOUT, async=False):
        if root_prefix_level is None:
            r = self._get(rt, timeout, async, INDEX_PATH.format(index))
        else:
            r = self._get(rt, timeout, async, INDEX_PATH_RPL.format(index, root_prefix_level))
        return self.check_response(r)

    # csruntime
    def sign_csr_request(self, rt, csr, timeout=DEFAULT_TIMEOUT, async=False):
        data = {'csr': csr}
        r = self._post(rt, timeout, async, CSR_REQUEST, data=data['csr'])
        return self.check_response(r)

    # csmanage
    def get_enrollment_password(self, rt, node_name, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, ENROLLMENT_PASSWORD.format(node_name))
        result = self.check_response(r)
        if 'enrollment_password' in result:
            return result['enrollment_password']
        else:
            _log.error("Failed to fetch enrollment password")
            return None

    # DEPRECATED: In tests only
    def abolish_proxy_peer(self, rt, peer_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._delete(rt, timeout, async, PROXY_PEER_ABOLISH.format(peer_id))
        return self.check_response(r)
