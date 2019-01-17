import requests
import json
from calvin.actorstore.docobject import DocFormatter

class DocumentationStore(object):
    """docstring for DocumentationStore"""
    def __init__(self, host="127.0.0.1", port=4999):
        super(DocumentationStore, self).__init__()
        self.host = host
        self.port = port
        self.base_request = "http://{}:{}/actors".format(host, port)
    
    def _retrieve_metadata(self, what):
        ns, name = self._format_what(what)
        if ns or name:
            req_str = '{}/{}/{}'.format(self.base_request, ns, name)
        else:
            req_str = '{}/'.format(self.base_request)
        r = requests.get(req_str)
        if r.status_code != 200:
            # raise("BAD STORE")
            metadata = {}
        else:    
            res = r.json()
            metadata = res['properties']
        return metadata
        
    def _format_what(self, what):
        what = what or ''
        parts = what.split('.') + ['', '']
        return parts[0:2]
    
    def documentation(self):
        pass
    
    def help_raw(self, what):
        return json.dumps(self._retrieve_metadata(what))
        
    def help(self, what, compact, formatting):
        metadata = self._retrieve_metadata(what)
        df = DocFormatter(outputformat=formatting, compact=compact)
        return df.format(metadata)        
