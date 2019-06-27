import json

import requests

# PATHS
NODE_PATH = '/node/{}'
NODE = '/node'
NODES = '/nodes'
NODE_ID = '/id'
ACTOR = '/actor'
ACTOR_PATH = '/actor/{}'
ACTORS = '/actors'
ACTOR_MIGRATE = '/actor/{}/migrate'
APPLICATION_PATH = '/application/{}'
APPLICATION_MIGRATE = '/application/{}/migrate'
ACTOR_PORT = '/actor/{}/port/{}'
ACTOR_REPORT = '/actor/{}/report'
APPLICATIONS = '/applications'
DEPLOY = '/deploy'
INDEX_PATH_RPL = '/index/{}?root_prefix_level={}'
INDEX_PATH = '/index/{}'
STORAGE_PATH = '/storage/{}'

ConnectionError = requests.exceptions.ConnectionError

class ControlAPI(object):
    """docstring for ControlAPI"""
    def __init__(self):
        super(ControlAPI, self).__init__()
    
    # cscontrol
    # N.B. This queries the RUNTIME at host_uri
    def get_node_id(self, host_uri):
        response = requests.get(host_uri + NODE_ID)
        return response.status_code, response.json()

    # cscontrol
    def deploy(self, host_uri, deployable):
        response = requests.post(host_uri + DEPLOY, json=deployable)
        return response.status_code, response.json()

    # cscontrol
    # N.B. This queries the RUNTIME at host_uri, and may thus fail
    def migrate_actor(self, host_uri, actor_id, reqs):
        response = requests.post(host_uri + ACTOR_MIGRATE.format(actor_id), json=reqs)
        return response.status_code, None

    # cscontrol
    def get_node(self, host_uri, node_id):
        response = requests.get(host_uri + NODE_PATH.format(node_id))
        return response.status_code, response.json()

    # cscontrol
    def get_nodes(self, host_uri):
        response = requests.get(host_uri + NODES)
        return response.status_code, response.json()
        
    # # cscontrol
    def quit(self, host_uri, method=None):
        if method is None:
            response = requests.delete(host_uri + NODE)
        else:
            response = requests.delete(host_uri + NODE_PATH.format(method))
        return response.status_code, None
    
    def get_actor(self, host_uri, actor_id):
        response = requests.get(host_uri + ACTOR_PATH.format(actor_id))
        return response.status_code, response.json()

    # N.B. This queries the RUNTIME at host_uri, and may thus fail, use get_actor to find out where the actor resides
    def get_actor_report(self, host_uri, actor_id):
        response = requests.get(host_uri + ACTOR_REPORT.format(actor_id))
        return response.status_code, response.json()

    # N.B. This queries the RUNTIME at host_uri, and may thus fail, use get_actor to find out where the actor resides
    def get_actors(self, host_uri):
        response = requests.get(host_uri + ACTORS)
        return response.status_code, response.json()

    # cscontrol
    # N.B. This queries the RUNTIME at host_uri
    def get_applications(self, host_uri):
        response = requests.get(host_uri + APPLICATIONS)
        return response.status_code, response.json()

    # cscontrol
    def get_application(self, host_uri, application_id):
        response = requests.get(host_uri + APPLICATION_PATH.format(application_id))
        return response.status_code, response.json()

    # cscontrol
    def delete_application(self, host_uri, application_id):
        response = requests.delete(host_uri + APPLICATION_PATH.format(application_id))
        # FIXME: Make control api at least return consistent type, if not value
        return response.status_code, None

    def migrate_application(self, host_uri, app_id, reqs):
        response = requests.post(host_uri + APPLICATION_MIGRATE.format(app_id), json=reqs)
        return response.status_code, None
        
    def index(self, host_uri, path, root_level):
        response = requests.get(host_uri + INDEX_PATH_RPL.format(path, root_level))
        return response.status_code, response.json()
