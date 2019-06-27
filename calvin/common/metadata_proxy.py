import json
import hashlib

import requests

from calvinservices.actorstore import store
from calvinservices.csparser.parser import calvin_parse
from calvinservices.csparser.visitor import query
from calvinservices.csparser import astnode

def class_factory(src, metadata, actor_type):
    co = compile(src, actor_type, 'exec')
    import calvin.actor.actor as caa
    import calvin.common.calvinlogger as clog
    import calvin.runtime.north.calvin_token as ctok
    import copy as ccopy
    namespace = {
        'Actor': caa.Actor,
        'manage': caa.manage,
        'condition': caa.condition,
        'stateguard': caa.stateguard,
        'calvinsys': caa.calvinsys,
        'calvinlib': caa.calvinlib,
        'get_logger': clog.get_logger,
        'get_actor_logger': clog.get_actor_logger,
        'calvinlogger': clog,
        'EOSToken': ctok.EOSToken,
        'ExceptionToken': ctok.ExceptionToken,
        'deepcopy': ccopy.deepcopy,
    }
    exec(co, namespace)
    _, name = actor_type.split('.')
    actor_class = namespace[name]
    # append metadata
    actor_class.requires = metadata['requires']
    actor_class.inport_properties = {}  # {p: pp for p, pp in inports}
    actor_class.outport_properties = {}  # {p: pp for p, pp in outports}
    for port in metadata["ports"]:
        target = actor_class.inport_properties if port['direction'] == "in" else actor_class.outport_properties
        target[port['name']] = port.get('properties', {})
    return actor_class

#
# Disconnect actor lookup from runtime configuration
#

class LocalStore(store.Store):

    def get_metadata(self, actor_type):
        metadata = super().get_metadata(actor_type)
        return metadata if isinstance(metadata, dict) else None

    def get_source(self, actor_type):
        return self.get_src(actor_type)


class RemoteStore(object):
    """docstring for ActorLookup"""
    def __init__(self, actorstore_uri):
        super(RemoteStore, self).__init__()
        self.actorstore_uri = actorstore_uri
        self.cache = {}

    def _get_info(self, actor_type):
        # actor_type is '', 'ns', or 'ns.name'
        actor_type = actor_type.strip()
        parts = actor_type.split('.') + ['', '']
        ns, name, *_ = parts
        req = '{}/actors/{}/{}'.format(self.actorstore_uri, ns, name)
        r = requests.get(req.rstrip('/'))
        return r.json() if r.status_code == 200 else {'properties': None, 'src': None}

    def get_metadata(self, actor_type):
        if actor_type in self.cache:
            return self.cache[actor_type]
        res = self._get_info(actor_type)
        metadata = res['properties']
        self.cache[actor_type] = metadata
        return metadata

    def get_source(self, actor_type):
        res = self._get_info(actor_type)
        return res['src']

class NoStore(object):

    def get_metadata(self, actor_type):
        return None

    def get_source(self, actor_type):
        return None


class MetadataBuilder(object):
    """docstring for ConstructMetadata"""
    def __init__(self, auxiliary):
        super(MetadataBuilder, self).__init__()
        if isinstance(auxiliary, str):
            ast, it = calvin_parse(auxiliary)
            auxiliary = ast if it.error_count == 0 else None
        if isinstance(auxiliary, (astnode.BaseNode, type(None))):
            self.ast = auxiliary # None or AST
        else:
            self.ast = None


    def dummy_metadata(self, actor_type):
        actor_type = actor_type.strip()
        if '.' in actor_type:
            # treat it as an actor:
            ns, name = actor_type.split('.', maxsplit=1)
            md = {
                'type': 'actor',
                'ns': ns,
                'name': name,
                'args': [],
                'ports': [],
                'requires': [],
                'is_known': False,
                'documentation': ['Unknown actor'],
            }
        elif actor_type and actor_type[0] in "ABCDEFGHIJKLMNOPQRSTUVXYZ":
            # treat it as (local) component
            md = {
                'type': 'component',
                'ns': '',
                'name': actor_type,
                'args': [],
                'ports': [],
                'requires': [],
                'is_known': False,
                'documentation': ['Unknown component'],
            }
        else:
            # treat it as module
            md = {
                'type': 'module',
                'name': actor_type if actor_type else '/',
                'items': [],
                'is_known': False,
                'documentation': ['Unknown module'],
            }
        return md


    def get_metadata(self, actor_type):
        if not self.ast:
            return self.dummy_metadata(actor_type)
        # Check local components:
        comps = query(self.ast, kind=astnode.Component, attributes={'name':actor_type})
        if comps:
            comp = comps[0]
            md = {
                'is_known': True,
                'name': comp.name,
                'type': 'component',
                'ports': [{'direction': 'out', 'name': name} for name in comp.outports] +
                         [{'direction': 'in', 'name': name} for name in comp.inports],
                'args': [{'mandatory': True, 'name':name} for name in comp.arg_names],
                'definition': comp.children[0]
            }
            return md
        # Look for an assignment to actor_type, and find ports and arguments
        # For now, fallback to dummy metadata
        return self.dummy_metadata(actor_type)


class ActorMetadataProxy(object):
    """
    Return ActorMetadataProxy object.

    If 'config' is a URI, use that to connect to remote actor store
    If 'config' as 'local', instantiate a local Store object accessing files on disk.
    If 'config' is None, construct metadata from 'source_text' (blind operation)
    Metadata will also be constructed from 'source_text' if actor is not found.
    If 'source_text' is not supplied, metadata will still be generated but it will
    only contain the assumed actor_type.
    """
    def __init__(self, config=None):
        super(ActorMetadataProxy, self).__init__()
        self.store = NoStore()
        if config == 'local':
            self.store = LocalStore()
        elif isinstance(config, str) and config.startswith('http'):
            self.store = RemoteStore(config)

    def get_metadata(self, actor_type, auxiliary=None):
        md = self.store.get_metadata(actor_type)
        if md is None:
            self.mdbuilder = MetadataBuilder(auxiliary)
            # Construct metadata as best as we can...
            md = self.mdbuilder.get_metadata(actor_type)
        return md

    def get_source(self, actor_type):
        return self.store.get_source(actor_type)

    def signature(self, metadata):
        signature = {
            'actor_type': str("{ns}.{name}".format(**metadata)),
            'inports': sorted([str(port['name']) for port in metadata['ports'] if port['direction'] == 'in']),
            'outports': sorted([str(port['name']) for port in metadata['ports'] if port['direction'] == 'out'])
        }
        data = json.dumps(signature, separators=(',', ':'), sort_keys=True)
        return hashlib.sha256(data.encode('utf-8')).hexdigest()


    def lookup_and_verify_actor(self, actor_type):
        """Lookup and verify actor in actor store."""
        def actorstore_lookup():
            metadata = self.get_metadata(actor_type)
            src = self.get_source(actor_type)
            found = src is not None
            is_primitive = True
            actor_def = class_factory(src, metadata, actor_type) if found else None
            return (found, is_primitive, actor_def)
        found, is_primitive, actor_def = actorstore_lookup()
        if not found or not is_primitive:
            raise Exception("Unknown actor type: %s" % actor_type)
        return actor_def
