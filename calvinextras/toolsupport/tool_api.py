import requests

from calvinservices.csparser import visualize

class StoreProxy(object):
    """docstring for StoreProxy"""
    def __init__(self, uri):
        super(StoreProxy, self).__init__()
        self.base_request = "{}/actors".format(uri)
    
    def get_metadata(self, actor_type):
        parts = actor_type.strip().split('.')
        if len(parts) != 2:
            return {}
        req_str = '{}/{}/{}'.format(self.base_request, *parts)
        r = requests.get(req_str)
        if r.status_code != 200:
            # raise("BAD STORE")
            metadata = {}
        else:    
            res = r.json()
            metadata = res['properties']
        return metadata


class ToolSupport(object):
    """docstring for ToolSupport"""
    def __init__(self, actorstore_uri=None):
        super(ToolSupport, self).__init__()
        if actorstore_uri:
            self.store = StoreProxy(actorstore_uri)
        else:
            from calvinservices.actorstore import store
            self.store = store.Store()
            
    def visualize_script(self, script):
        dot = visualize.visualize_script(self.store.get_metadata, script)
        return dot
    
    def visualize_deployment(self, script):
        dot = visualize_deployment(self.store.get_metadata, script)
        return dot
        
    def visualize_deployment(self, script, component_name):
        dot = visualize_component(self.store.get_metadata, script, component_name)
        return dot
        