
import json
import requests

from requests import Response
try:
    from requests_futures.sessions import FuturesSession
    session = FuturesSession(max_workers=10)
except:
    session = None

from calvin.utilities.calvinlogger import get_logger
from calvin.runtime import get_runtime

DEFAULT_TIMEOUT = 5

_log = get_logger(__name__)


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
            raise Exception("%d" % response.status_code)
        else:
            # We have a async Future just return it
            response._calvin_key = key
            response._calvin_success = success
            self.future_responses.append(response)
            return response

    def _send(self, rt, timeout, send_func, path, data=None):
        rt = get_runtime(rt)
        if data:
            return send_func(rt.control_uri + path, timeout=timeout, data=json.dumps(data))
        else:
            return send_func(rt.control_uri + path, timeout=timeout)

    def _get(self, rt, timeout, async, path):
        req = session if async else requests
        return self._send(rt, timeout, req.get, path)

    def _post(self, rt, timeout, async, path, data={}):
        req = session if async else requests
        return self._send(rt, timeout, req.post, path, data)

    def _delete(self, rt, timeout, async, path):
        req = session if async else requests
        return self._send(rt, timeout, req.delete, path)

    def get_node_id(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, '/id')
        return self.check_response(r, key="id")

    def get_node(self, rt, node_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, '/node/{}'.format(node_id))
        return self.check_response(r)

    def quit(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._delete(rt, timeout, async, '/node')
        return self.check_response(r)

    def get_nodes(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, '/nodes')
        return self.check_response(r)

    def peer_setup(self, rt, *peers, **kwargs):
        timeout = kwargs.get('timeout', DEFAULT_TIMEOUT)
        async = kwargs.get('async', False)

        if not isinstance(peers[0], type("")):
            peers = peers[0]
        data = {'peers': peers}

        r = self._post(rt, timeout, async, '/peer_setup', data)
        return self.check_response(r)

    def new_actor(self, rt, actor_type, actor_name, timeout=DEFAULT_TIMEOUT, async=False):
        data = {
            'actor_type': actor_type,
            'args': {'name': actor_name},
            'deploy_args': None
        }

        r = self._post(rt, timeout, async, '/actor', data)
        return self.check_response(r, key='actor_id')

    def new_actor_wargs(self, rt, actor_type, actor_name, args=None, deploy_args=None, timeout=DEFAULT_TIMEOUT,
                        async=False, **kwargs):
        data = {'actor_type': actor_type, 'deploy_args': deploy_args}

        if args is None:
            kwargs['name'] = actor_name
            data['args'] = kwargs
        else:
            data['args'] = args

        r = self._post(rt, timeout, async, '/actor', data)
        return self.check_response(r, key='actor_id')

    def get_actor(self, rt, actor_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, '/actor/{}'.format(actor_id))
        return self.check_response(r)

    def get_actors(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, '/actors')
        return self.check_response(r)

    def delete_actor(self, rt, actor_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._delete(rt, timeout, async, '/actor/{}'.format(actor_id))
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
        r = self._post(rt, timeout, async, '/connect', data)
        return self.check_response(r)

    def disconnect(self, rt, actor_id=None, port_name=None, port_dir=None, port_id=None, timeout=DEFAULT_TIMEOUT,
                   async=False):
        data = {
            'actor_id': actor_id,
            'port_name': port_name,
            'port_dir': port_dir,
            'port_id': port_id
        }
        r = self._post(rt, timeout, async, '/disconnect', data)
        return self.check_response(r)

    def disable(self, rt, actor_id, timeout=DEFAULT_TIMEOUT, async=False):
        path = '/actor/{}/disable'.format(actor_id)
        r = self._post(rt, timeout, async, path)
        return self.check_response(r)

    def migrate(self, rt, actor_id, dst_id, timeout=DEFAULT_TIMEOUT, async=False):
        data = {'peer_node_id': dst_id}
        path = '/actor/{}/migrate'.format(actor_id)
        r = self._post(rt, timeout, async, path, data)
        return self.check_response(r)

    def add_requirements(self, rt, application_id, reqs, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        data = {'reqs': reqs}
        r = self._post(rt, timeout, async, '/application/{}'.format(application_id), data)
        return self.check_response(r)

    def get_port(self, rt, actor_id, port_id, timeout=DEFAULT_TIMEOUT, async=False):
        path = '/actor/{}/{}'.format(actor_id, port_id)
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
        r = self._post(rt, timeout, async, '/set_port_property', data)
        return self.check_response(r)

    def report(self, rt, actor_id, timeout=DEFAULT_TIMEOUT, async=False):
        path = '/actor/{}/report'.format(actor_id)
        r = self._get(rt, timeout, async, path)
        return self.check_response(r)

    def get_applications(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, '/applications')
        return self.check_response(r)

    def get_application(self, rt, application_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, '/application/{}'.format(application_id))
        return self.check_response(r)

    def delete_application(self, rt, application_id, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._delete(rt, timeout, async, '/application/{}'.format(application_id))
        return self.check_response(r)

    def deploy_application(self, rt, name, script, check=True, timeout=DEFAULT_TIMEOUT, async=False):
        data = {"name": name, "script": script, "check": check}
        r = self._post(rt, timeout, async, '/deploy', data)
        return self.check_response(r)

    def deploy_app_info(self, rt, name, app_info, deploy_info=None, check=True, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        data = {"name": name, "app_info": app_info, 'deploy_info': deploy_info, "check": check}
        req = session if async else requests
        r = req.post(rt.control_uri + "/deploy", data=json.dumps(data), timeout=timeout)
        return self.check_response(r)

    def register_metering(self, rt, user_id=None, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        data = {'user_id': user_id} if user_id else None
        req = session if async else requests
        r = req.post(rt.control_uri + '/meter', data=json.dumps(data), timeout=timeout)
        return self.check_response(r)

    def unregister_metering(self, rt, user_id, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.delete(rt.control_uri + '/meter/' + user_id, data=json.dumps(None), timeout=timeout)
        return self.check_response(r)

    def get_timed_metering(self, rt, user_id, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.get(rt.control_uri + '/meter/' + user_id + '/timed', timeout=timeout)
        return self.check_response(r)

    def get_aggregated_metering(self, rt, user_id, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.get(rt.control_uri + '/meter/' + user_id + '/aggregated', timeout=timeout)
        return self.check_response(r)

    def get_actorinfo_metering(self, rt, user_id, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.get(rt.control_uri + '/meter/' + user_id + '/metainfo', timeout=timeout)
        return self.check_response(r)

    def add_index(self, rt, index, value, timeout=DEFAULT_TIMEOUT, async=False):
        data = {'value': value}
        r = self._post(rt, timeout, async, '/index/{}'.format(index), data)
        return self.check_response(r)

    def remove_index(self, rt, index, value, timeout=DEFAULT_TIMEOUT, async=False):
        data = {'value': value}
        r = self._delete(rt, timeout, async, '/index/{}'.format(index), data)
        return self.check_response(r)

    def get_index(self, rt, index, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, '/index/{}'.format(index))
        return self.check_response(r)

    def get_storage(self, rt, key, timeout=DEFAULT_TIMEOUT, async=False):
        r = self._get(rt, timeout, async, '/storage/{}'.format(key))
        return self.check_response(r)

    def set_storage(self, rt, key, value, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        data = {'value': value}
        r = self._post(rt, timeout, async, '/storage/{}'.format(key), data)
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
