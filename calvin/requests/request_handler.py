
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
                    return None
            # When failed raise exception
            raise Exception("%d" % response.status_code)
        else:
            # We have a async Future just return it
            response._calvin_key = key
            response._calvin_success = success
            self.future_responses.append(response)
            return response

    def get_node_id(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.get(rt.control_uri + '/id', timeout=timeout)
        return self.check_response(r, key="id")

    def get_node(self, rt, node_id, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.get(rt.control_uri + '/node/' + node_id, timeout=timeout)
        return self.check_response(r)

    def quit(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.delete(rt.control_uri + '/node', timeout=timeout)
        return self.check_response(r)

    def get_nodes(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        return self.check_response(req.get(rt.control_uri + '/nodes', timeout=timeout))

    def peer_setup(self, rt, *peers, **kwargs):
        rt = get_runtime(rt)
        timeout = kwargs.get('timeout', DEFAULT_TIMEOUT)
        async = kwargs.get('async', False)
        if not isinstance(peers[0], type("")):
            peers = peers[0]
        req = session if async else requests
        r = req.post(
            rt.control_uri + '/peer_setup', data=json.dumps({'peers': peers}), timeout=timeout)
        return self.check_response(r)

    def new_actor(self, rt, actor_type, actor_name, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        data = {'actor_type': actor_type, 'args': {
            'name': actor_name}, 'deploy_args': None}
        req = session if async else requests
        r = req.post(rt.control_uri + '/actor', data=json.dumps(data), timeout=timeout)
        result = self.check_response(r, key='actor_id')
        return result

    def new_actor_wargs(self, rt, actor_type, actor_name, args=None, deploy_args=None, timeout=DEFAULT_TIMEOUT, async=False, **kwargs):
        rt = get_runtime(rt)
        req = session if async else requests
        if args is None:
            kwargs['name'] = actor_name
            r = req.post(rt.control_uri + '/actor', data=json.dumps(
                {'actor_type': actor_type, 'deploy_args': deploy_args, 'args': kwargs}))
        else:
            r = req.post(rt.control_uri + '/actor', data=json.dumps(
                {'actor_type': actor_type, 'deploy_args': deploy_args, 'args': args}), timeout=timeout)
        result = self.check_response(r, key='actor_id')
        return result

    def get_actor(self, rt, actor_id, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.get(rt.control_uri + '/actor/' + actor_id, timeout=timeout)
        return self.check_response(r)

    def get_actors(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.get(rt.control_uri + '/actors', timeout=timeout)
        return self.check_response(r)

    def delete_actor(self, rt, actor_id, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.delete(rt.control_uri + '/actor/' + actor_id, timeout=timeout)
        return self.check_response(r)

    def connect(self, rt, actor_id, port_name, peer_node_id, peer_actor_id, peer_port_name, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        data = {'actor_id': actor_id, 'port_name': port_name, 'port_dir': 'in', 'peer_node_id': peer_node_id,
                'peer_actor_id': peer_actor_id, 'peer_port_name': peer_port_name, 'peer_port_dir': 'out'}
        req = session if async else requests
        r = req.post(rt.control_uri + '/connect', data=json.dumps(data), timeout=timeout)
        return self.check_response(r)

    def disconnect(self, rt, actor_id=None, port_name=None, port_dir=None, port_id=None, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        data = {'actor_id': actor_id, 'port_name': port_name,
                'port_dir': port_dir, 'port_id': port_id}
        req = session if async else requests
        r = req.post(rt.control_uri + '/disconnect', json.dumps(data), timeout=timeout)
        return self.check_response(r)

    def disable(self, rt, actor_id, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.post(rt.control_uri + '/actor/' + actor_id + '/disable', timeout=timeout)
        return self.check_response(r)

    def migrate(self, rt, actor_id, dst_id, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        data = {'peer_node_id': dst_id}
        req = session if async else requests
        r = req.post(
            rt.control_uri + '/actor/' + actor_id + "/migrate", data=json.dumps(data), timeout=timeout)
        return self.check_response(r)

    def add_requirements(self, rt, application_id, reqs, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        data = {'reqs': reqs}
        req = session if async else requests
        r = req.post(
            rt.control_uri + '/application/' + application_id + "/migrate", data=json.dumps(data), timeout=timeout)
        return self.check_response(r)

    def get_port(self, rt, actor_id, port_id, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.get(
            rt.control_uri + "/actor/" + actor_id + '/port/' + port_id, timeout=timeout)
        return self.check_response(r)

    def set_port_property(self, rt, actor_id, port_type, port_name, port_property, value, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        data = {'actor_id': actor_id, 'port_type': port_type, 'port_name':
                port_name, 'port_property': port_property, 'value': value}
        req = session if async else requests
        r = req.post(
            rt.control_uri + '/set_port_property', data=json.dumps(data), timeout=timeout)
        return self.check_response(r)

    def report(self, rt, actor_id, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.get(rt.control_uri + '/actor/' + actor_id + '/report', timeout=timeout)
        return self.check_response(r)

    def get_applications(self, rt, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.get(rt.control_uri + '/applications', timeout=timeout)
        return self.check_response(r)

    def get_application(self, rt, application_id, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.get(rt.control_uri + '/application/' + application_id, timeout=timeout)
        return self.check_response(r)

    def delete_application(self, rt, application_id, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.delete(rt.control_uri + '/application/' + application_id, timeout=timeout)
        return self.check_response(r)

    def deploy_application(self, rt, name, script, check=True, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        data = {"name": name, "script": script, "check": check}
        req = session if async else requests
        r = req.post(rt.control_uri + "/deploy", data=json.dumps(data), timeout=timeout)
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
        rt = get_runtime(rt)
        data = {'value': value}
        req = session if async else requests
        r = req.post(rt.control_uri + '/index/' + index, data=json.dumps(data), timeout=timeout)
        return self.check_response(r)

    def remove_index(self, rt, index, value, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        data = {'value': value}
        req = session if async else requests
        r = req.delete(rt.control_uri + '/index/' + index, data=json.dumps(data), timeout=timeout)
        return self.check_response(r)

    def get_index(self, rt, index, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.get(rt.control_uri + '/index/' + index, timeout=timeout)
        return self.check_response(r)

    def get_storage(self, rt, key, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        req = session if async else requests
        r = req.get(rt.control_uri + '/storage/' + key, timeout=timeout)
        return self.check_response(r)

    def set_storage(self, rt, key, value, timeout=DEFAULT_TIMEOUT, async=False):
        rt = get_runtime(rt)
        data = {'value': value}
        req = session if async else requests
        r = req.post(rt.control_uri + '/storage/' + key, data=json.dumps(data), timeout=timeout)
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
