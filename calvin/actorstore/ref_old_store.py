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
import glob
import imp
import inspect
import json
import re
from types import ModuleType
import hashlib
import numbers

from calvin.csparser.astnode import node_encoder, node_decoder
from calvin.utilities import calvinconfig
from calvin.utilities import dynops
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCB
from calvin.csparser.port_property_syntax import port_property_data
from calvin.requests import calvinresponse


_log = get_logger(__name__)
_conf = calvinconfig.get()

#
# Helpers
#
def _split_path(path):
    """Split a path into tuple: (dirname, basename, ext)"""
    dirname, filename = os.path.split(path)
    basename, ext = os.path.splitext(filename)
    return (dirname, basename, ext)

def _extension(path):
    _, _, ext = _split_path(path)
    return ext

def _basename(path):
    _, basename, _ = _split_path(path)
    return basename


def _files_in_dir(dir, filter=None):
    """Return list of files in dir/, filter is optional list of extensions to look for."""
    if filter:
        files = [x for x in glob.glob(os.path.join(dir, "*")) if _extension(x) in filter]
    else:
        files = [x for x in glob.glob(os.path.join(dir, "*"))]
    return files


def _rel_path_to_namespace(rel_path):
    return '.'.join([x for x in rel_path.split('/')])

def _normalize_namespace(namespace):
    return namespace.strip('.')

#
# Singleton implementation
#
class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

#
# Base class for all "stores"
#
class Store(object):
    """Base class for retrieving paths to loadable components.

    Provides methods to collect all modules (namespaces) and the components within them in a dictionary
    with mo
    It doesn't know what to do with the
    """

    # List of directories to exclude from search
    _excluded_dirs = ('.git', )

    def __init__(self):
        """
            Subclass must set 'conf_paths_name' before calling superclass init.
        """
        base_path = os.path.abspath(os.path.dirname(__file__))
        # paths = [p for p in _conf.get('global', self.conf_paths_name) if not os.path.isabs(p)]
        # abs_paths = [p for p in _conf.get('global', self.conf_paths_name) if os.path.isabs(p)]
        paths = _conf.get('global', self.conf_paths_name)
        self._MODULE_PATHS = [os.path.join(base_path, p) if not os.path.isabs(p) else p for p in paths]
        _log.debug("Actor store paths: %s" % self._MODULE_PATHS)
        self._MODULE_CACHE = {}


    def update(self):
        """Should be called after a module has been added at runtime."""
        _log.debug("Store update SECURITY %s" % str(self.sec))
        self._MODULE_CACHE = self.find_all_modules()


    def directories(self):
        for path in self._MODULE_PATHS: # FIXME: Reverse order

            if not os.path.exists(path):
                continue

            for current, subdirs, _ in os.walk(path):
                rel_path = os.path.relpath(current, path)
                # Skip top directory
                if rel_path == '.':
                    continue
                namespace = _rel_path_to_namespace(rel_path)
                files = _files_in_dir(current, ('.py', '.comp'))

                yield (current, namespace, files)

                # Exclude special directories
                for exclude in self._excluded_dirs:
                    if exclude in subdirs:
                        subdirs.remove(exclude)


    def _load_pymodule(self, name, path):
        if not os.path.isfile(path):
            return (None, None)
        pymodule = None
        signer = None
        _log.debug("Store load_pymodule SECURITY %s" % str(self.sec))
        try:
            if self.sec:
                _log.debug("Verify signature for %s actor" % name)
                verified, signer = self.sec.verify_signature(path, "actor")
                if self.verify and not verified:
                    _log.debug("Failed verification of signature for %s actor" % name)
                    raise Exception("Actor security signature verification failed")
            pymodule = imp.load_source(name, path)
            # Check if we have a module or not
            if not isinstance(pymodule, ModuleType):
                pymodule = None
                raise Exception("Invalid module")
        except Exception as e:
            _log.exception("Could not load python module {}".format(name))
        finally:
            return (pymodule, signer)


    def _load_pyclass(self, name, path):
        if not os.path.isfile(path):
            return (None, None)
        pymodule, signer = self._load_pymodule(name, path)
        pyclass = pymodule and pymodule.__dict__.get(name, None)
        if not pyclass:
            _log.debug("No entry %s in %s" % (name, path))
        return (pyclass, signer)


    def find_all_modules(self):
        modules = {}
        for abs_path, namespace, files in self.directories():
            # Check that at least one file exists in dir
            if not files:
                continue
            if not namespace in modules:
                modules[namespace] = []
            if abs_path not in modules[namespace]:
                modules[namespace].append(abs_path)
        return modules


    def paths_for_module(self, namespace):
        return self._MODULE_CACHE.get(_normalize_namespace(namespace), [])


    def modules(self, namespace=''):
        """Return list of all modules in namespace (or top level if namespace omitted)"""
        if not namespace:
            modlist = [x.split('.', 1)[0] for x in self._MODULE_CACHE]
        else:
            ns = _normalize_namespace(namespace)
            depth = len(ns.split('.'))
            ns = ns + '.'
            modlist = [x.split('.')[depth] for x in self._MODULE_CACHE if x.startswith(ns)]
        # Remove duplicates and sort list
        return sorted(set(modlist))


#
# Actor Store
#
class ActorStore(Store):

    def __init__(self, security=None, verify=True):
        self.conf_paths_name = 'actor_paths'
        super(ActorStore, self).__init__()
        self.sec = security
        self.verify = verify
        _log.debug("ActorStore init SECURITY %s" % str(self.sec))
        self.update()


    def load_from_path(self, path):
        actor_type, _  = os.path.splitext(os.path.basename(path))
        return self.load_actor(actor_type, path)


    def load_actor(self, actor_type, actor_path):
        actor_class, signer = self._load_pyclass(actor_type, actor_path)
        if actor_class:
            inports, outports = self._gather_ports(actor_class)
            actor_class.inport_properties = {p: pp for p, pp in inports}
            actor_class.outport_properties = {p: pp for p, pp in outports}
        return actor_class, signer


    def lookup(self, qualified_name):
        """
        Look up actor using qualified_name, e.g. foo.bar.Actor
        If self.sec is set use it to verify access rights
        Return a tuple (found, is_primitive, info) where
            found:         boolean
            is_primitive:  boolean
            info:          if is_primitive is
                            True  => actor object
                            False => component definition dictionary
            signer:         name of actor signer (string) if security is used, else None
        """
        _log.debug("ActorStore lookup SECURITY %s" % str(self.sec))
        namespace, _, actor_type = qualified_name.rpartition('.')
        # Search in the order given by config
        for path in self.paths_for_module(namespace):
            # Primitives has precedence over components
            actor_path = os.path.join(path, actor_type + '.py')
            actor_class, signer = self.load_actor(actor_type, actor_path)
            if actor_class:
                return (True, True, actor_class, signer)
        for path in self.paths_for_module(namespace):
            actor_path = os.path.join(path, actor_type + '.comp')
            # TODO add credential verification of components
            comp = self.load_component(actor_type, actor_path)
            if comp:
                return (True, False, comp, None)
        return (False, False, None, None)


    def _parse_docstring(self, class_):
        # Extract port names from docstring
        docstring = inspect.cleandoc(class_.__doc__)
        inputs = []
        outputs = []
        doctext = []
        dest = doctext
        for line in docstring.split('\n'):
            if re.match(r'^\s*[Ii]nputs?\s?:\s*$', line):
                dest = inputs
                continue
            elif re.match(r'^\s*[Oo]utputs?\s?:\s*$', line):
                dest = outputs
                continue
            elif dest is doctext:
                line = line.rstrip()
                dest.append(line)
                continue

            if dest in [inputs, outputs]:
                match = re.match(
                    # Match port name
                    r'^\s*([a-zA-Z][a-zA-Z0-9_]*)' +
                    # Match optional port properties
                    # property names is standard identifiers
                    # property values kan be lists, strings or numbers
                    # FIXME be more forgiving for putting whitespace at wrong places or any string value
                    r'(\((?:[a-zA-Z][a-zA-Z0-9_]*=[a-zA-Z0-9_\-"\.\[\],\s]*)+\))?' +
                    # Match optional documentation
                    r'\s*:?\s*(.*)$', line)
                if match:
                    if match.group(2) is not None:
                        try:
                            prop_strings_split = [s for s in match.group(2)[1:-1].split(",")]
                            prop_strings = []
                            comb = False
                            # Fix that list value got splitted
                            for s in prop_strings_split:
                                if r'[' in s:
                                    prop_strings.append(s)
                                    if r']' not in s:
                                        comb = True
                                elif comb:
                                    prop_strings[-1] += ", " + s
                                    if r']' in s:
                                        comb = False
                                elif not comb:
                                    prop_strings.append(s)

                            port_properties = {}
                            for s in prop_strings:
                                key, value = s.split("=", 1)
                                port_properties[key.strip()] = json.loads(value)
                        except:
                            _log.exception("Malformed syntax for port properties %s in actor %s and port %s" %
                                            (value, class_.__name__, match.group(1)))
                            port_properties = {}
                    else:
                        port_properties = {}
                    direction = "in" if dest == inputs else "out"
                    # FIXME Should validation be moved to higher layer?
                    issues = self._validate_port_properties(port_properties, direction)
                    if issues:
                        _log.error("Error in port property of actor %s: %s" % (class_.__name__,
                                   ", ".join([r.data['reason'] for r in issues])))
                    dest.append((match.group(1), match.group(3), port_properties))

        while not doctext[-1]:
            doctext.pop()

        return (inputs, outputs, doctext)


    def _validate_port_properties(self, port_properties, direction):
        # TODO break out the validation and consolidate it with codegen.py:ConsolidatePortProperty
        issues = []
        for key, values in port_properties.items():
            if not isinstance(values, (list, tuple)):
                values = [values]
            for value in values:
                if key not in port_property_data.keys():
                    reason = "Port property {} is unknown".format(key)
                    issues.append(calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST, {'reason': reason}))
                    continue
                ppdata = port_property_data[key]
                if ppdata['type'] == "category":
                    if value not in ppdata['values']:
                        reason = "Port property {} can only have values {}".format(
                            key, ", ".join(ppdata['values'].keys()))
                        issues.append(calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST, {'reason': reason}))
                        continue
                    if direction not in ppdata['values'][value]['direction']:
                        reason = "Port property {}={} is only for {} ports".format(
                            key, value, ppdata['values'][value]['direction'])
                        issues.append(calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST, {'reason': reason}))
                        continue
                if ppdata['type'] == 'scalar':
                    if not isinstance(value, numbers.Number):
                        reason = "Port property {} can only have scalar values".format(key)
                        issues.append(calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST, {'reason': reason}))
                        continue
                if ppdata['type'] == 'string':
                    if not isinstance(value, basestring):
                        reason = "Port property {} can only have string values".format(key)
                        issues.append(calvinresponse.CalvinResponse(calvinresponse.BAD_REQUEST, {'reason': reason}))
                        continue
        return issues

    def _gather_ports(self, class_):
        inputs, outputs, _ = self._parse_docstring(class_)
        # tuples with port names and port properties
        return ([(p, pp) for (p, _, pp) in inputs], [(p, pp) for (p, _, pp) in outputs])


    def _get_args(self, actor_class):
        """
        Return a dict with a list of mandatory arguments, and a dictionary of optional arguments.
        Either one may be empty.
        """
        a = inspect.getargspec(actor_class.init)
        defaults = [] if not a.defaults else a.defaults
        n_mandatory = len(a.args) - len(defaults)
        mandatory = a.args[1:n_mandatory]
        optional = {arg:default for arg, default in zip(a.args[n_mandatory:], defaults)}
        return {'mandatory':mandatory, 'optional':optional}


    def load_component(self, name, path):
        if not os.path.isfile(path):
            return None
        try:
          with open(path, 'r') as source:
            dict = json.load(source, object_hook=node_decoder)
        except Exception as e:
          _log.exception("Failed to read source for component '%s' : " % ( name, ))
          return None
        if dict['type'] != name:
          _log.info("Found component '%s' didn't match type '%s'" % (dict['type'], name))
          return None
        return dict['definition']

    def add_component(self, namespace, component_type, definition, overwrite=False):
      """
      Install a component definition into an actor store
      namespace is relative to config parameter actor_paths
      component_type is the "class" name and must be unique wrt namespace
      definition is the component definition as derived by the compiler
      Returns True on success, False otherwise
      """
      # Find place to store component based on namespace
      paths = self.paths_for_module(namespace)
      if not paths:
          _log.error('namespace creation not implemented: %s' % namespace)
          return False
      qualified_name = namespace + "." + component_type
      found, is_primitive, _, signer = self.lookup(qualified_name)
      if found and is_primitive:
          _log.error("Can't overwrite actor: %s" % qualified_name)
          return False
      if found and not overwrite:
          _log.error("Can't overwrite existing component (overwrite=%s): %s" % (overwrite, qualified_name))
          return False

      filename = component_type + ".comp"
      filepath = os.path.join(paths[0], filename)
      comp = {'type':component_type, 'definition':definition}

      try:
        with open(filepath, 'w') as f:
          json.dump(comp, f, default=node_encoder, indent=2)
      except Exception as e:
         _log.exception("Could not write component to: %s" % filepath)
         return False
      return True


    def actors(self, namespace):
        """Return list of actors in namespace"""
        actors = []
        for path in self.paths_for_module(namespace):
            actors = actors + [_basename(x) for x in _files_in_dir(path, ('.py', '.comp')) if '__init__.py' not in x]
        return actors

    def actor_paths(self, module):
        # Depth first
        l = []
        prefix = module + "." if module else ""
        for m in self.modules(module):
            l = l + self.actor_paths(prefix + m)
        actors = []
        for path in self.paths_for_module(module):
            actors = actors + [x for x in _files_in_dir(path, ('.py', '.comp')) if '__init__.py' not in x]
        if not l and not actors:
            # Fully qualifying name?
            namespace, name = module.rsplit('.', 1)
            for path in self.paths_for_module(namespace):
                actors = actors + [x for x in _files_in_dir(path, ('.py', '.comp')) if _basename(x) == name]
        return l + actors



class GlobalStore(ActorStore):
    """ Interface to distributed global actor store
        Currently supports meta information on actors and full components
    """

    def __init__(self, node=None, runtime=None, security=None, verify=True):
        super(GlobalStore, self).__init__(security, verify)
        self.node = node  # Used inside runtime
        # FIXME this is not implemented
        self.rt = runtime  # Use Control API from outside runtime

    def _collect(self, ns=None):
        for a in [] if ns is None else self.actors(ns):
            self.qualified_actor_list.append(ns + "." + a if ns else a)
        for m in self.modules(ns):
            self._collect(ns + "." + m if ns else m)

    @staticmethod
    def actor_signature(desc):
        """ Takes actor/component description and
            generates a signature string
        """
        if 'is_primitive' not in desc or desc['is_primitive']:
            signature = {u'actor_type': unicode(desc['actor_type']),
                         u'inports': sorted([unicode(i) for i in desc['inports']]),
                         u'outports': sorted([unicode(i) for i in desc['outports']])}
        else:
            if type(desc['component']) is dict:
                signature = {u'actor_type': unicode(desc['actor_type']),
                             u'inports': sorted([unicode(i) for i in desc['component']['inports']]),
                             u'outports': sorted([unicode(i) for i in desc['component']['outports']])}
            else:
                signature = {u'actor_type': unicode(desc['actor_type']),
                             u'inports': sorted([unicode(i) for i in desc['component'].inports]),
                             u'outports': sorted([unicode(i) for i in desc['component'].outports])}
        return hashlib.sha256(json.dumps(signature, separators=(',', ':'), sort_keys=True)).hexdigest()

    @staticmethod
    def list_sort(obj):
        if isinstance(obj, dict):
            for k, v in obj.iteritems():
                obj[k] = GlobalStore.list_sort(v)
            return obj
        elif isinstance(obj, (set, list, tuple)):
            _obj=[]
            for v in obj:
                _obj.append(GlobalStore.list_sort(v))
            return sorted(_obj)
        else:
            return obj

    @staticmethod
    def actor_hash(desc):
        """ Takes actor/component description and
            generates one hash of the complete info
        """
        # return hashlib.sha256(json.dumps(GlobalStore.list_sort(desc), separators=(',', ':'), sort_keys=True)).hexdigest()
        # FIXME: This is a temporary hack to make things work while we rewrite the store and signing infrastructure
        return hashlib.sha256(GlobalStore.actor_signature(desc)).hexdigest()

    def export_actor(self, desc):
        signature = self.actor_signature(desc)
        hash = self.actor_hash(desc)
        if self.node:
            # FIXME should have callback to verify OK
            self.node.storage.add_index(['actor', 'signature', signature, self.node.id], hash, root_prefix_level=3)
            # FIXME should have callback to verify OK
            # FIXME: This is a temporary hack to make things work while we rewrite the store and signing infrastructure
            if 'component' in desc and type(desc['component']) is not dict:
                mess = json.dumps(desc['component'], default=node_encoder)
                desc['component'] = json.loads(mess)
            self.node.storage.set('actor_type-', hash, desc, None)
        else:
            print "global store index %s -> %s" %(signature, hash)

    def export(self):
        self.qualified_actor_list = []
        self._collect()
        for a in self.qualified_actor_list:
            found, is_primitive, actor, signer = self.lookup(a)
            if not found:
                continue
            # Currently only args and requires differences that would generate multiple hits
            if is_primitive:
                inputs, outputs, _ = self._parse_docstring(actor)
                args = self._get_args(actor)
                desc = {'is_primitive': is_primitive,
                        'actor_type': a,
                        'args': args,
                        'inports': [p[0] for p in inputs],
                        'outports': [p[0] for p in outputs],
                        'requires': actor.requires if hasattr(actor, 'requires') else [],
                        'signer': signer}
            else:
                desc = {'is_primitive': is_primitive,
                        'actor_type': a,
                        'component': actor}
            self.export_actor(desc)

    def global_lookup(self, desc, cb):
        """ Lookup the described actor
            desc is a dict with keys: actor_type, inports and outports
            cb is callback with signature and list of full descriptions
        """
        signature = GlobalStore.actor_signature(desc)
        self.global_signature_lookup(signature, cb)

    def global_signature_lookup(self, signature, cb):
        """ Lookup the actor signature
            signature is an actor signature
            cb is callback with signature and list of full descriptions
        """
        self.node.storage.get_index(['actor', 'signature', signature], root_prefix_level=3,
                                    cb=CalvinCB(self._global_lookup_cb, signature=signature, org_cb=cb))

    def _global_lookup_cb(self, value, signature, org_cb):
        _log.debug("_global_lookup_cb %s" % value)
        if value:
            nbr = [len(value)]
            actors = []
            for a in value:
                self.node.storage.get('actor_type-', a,
                            CalvinCB(self._global_lookup_collect, nbr=nbr, actors=actors, signature=signature, org_cb=org_cb))
        else:
            # Not found
            org_cb(signature=signature, description=[])

    def _global_lookup_collect(self, key, value, nbr, actors, signature, org_cb):
        _log.debug("_global_lookup_collect %s" % value)
        actors.append(value)
        nbr[0] -= 1
        if nbr[0] == 0:
            org_cb(signature=signature, description=actors)

    def global_lookup_actor(self, out_iter, kwargs, final, actor_type_id):
        _log.analyze(self.node.id, "+", {'actor_type_id': actor_type_id})
        if final[0]:
            _log.analyze(self.node.id, "+ FINAL", {'actor_type_id': actor_type_id, 'counter': kwargs['counter']})
            out_iter.auto_final(kwargs['counter'])
        else:
            kwargs['counter'] += 1
            self.node.storage.get_iter('actor_type-', actor_type_id, it=out_iter)
            _log.analyze(self.node.id, "+ GET", {'actor_type_id': actor_type_id, 'counter': kwargs['counter']})

    def filter_actor_on_params(self, out_iter, kwargs, final, desc):
        param_names = kwargs.get('param_names', [])
        if not final[0] and desc != dynops.FailedElement:
            if desc['is_primitive']:
                mandatory = desc['args']['mandatory']
                optional = desc['args']['optional'].keys()
            else:
                mandatory = desc['component']['arg_identifiers']
                optional = []
            # To be valid actor type all mandatory params need to be supplied and only valid params
            if all([p in param_names for p in mandatory]) and all([p in (mandatory + optional) for p in param_names]):
                _log.analyze(self.node.id, "+ FOUND DESC", {'desc': desc})
                out_iter.append(desc)
        if final[0]:
            out_iter.final()

    def global_lookup_iter(self, signature, param_names=None, node_id=None):
        """ Lookup the described actor type
            signature is the actor/component signature
            param_names is optional list argument to filter out any descriptions which does not support the params
            returns a dynops iterator with all found matching descriptions
        """
        if node_id is None:
            sign_iter = self.node.storage.get_index_iter(['actor', 'signature', signature]).set_name("signature")
        else:
            sign_iter = self.node.storage.get_index_iter(['actor', 'signature', signature, node_id]).set_name("signature")
        actor_type_iter = dynops.Map(self.global_lookup_actor, sign_iter, counter=0, eager=True)
        if param_names is None:
            actor_type_iter.set_name("global_lookup")
            return actor_type_iter
        filtered_actor_type_iter = dynops.Map(self.filter_actor_on_params, actor_type_iter, param_names=param_names,
                                              eager=True)
        actor_type_iter.set_name("unfiltered_global_lookup")
        filtered_actor_type_iter.set_name("global_lookup")
        return filtered_actor_type_iter

from docobject import ErrorDoc, ModuleDoc, ComponentDoc, ActorDoc

class DocumentationStore(ActorStore):
    """Interface to documentation"""
    def __init__(self):
        super(DocumentationStore, self).__init__()
        self.docs = self.root_docs()


    def module_docs(self, namespace):
        modules = [self.module_docs(x) for x in self.modules(namespace)]
        actors = [self.actor_docs(".".join([namespace, x])) for x in self.actors(namespace)]
        paths = self.paths_for_module(namespace)
        for path in paths:
            docpath = os.path.join(path, '__init__.py')
            pymodule, _ = self._load_pymodule('__init__', docpath)
            if pymodule and pymodule.__doc__:
                doclines = pymodule.__doc__.splitlines()
                return ModuleDoc(namespace, modules, actors, doclines)
        return ErrorDoc(namespace, None, "Unknown module")


    def actor_docs(self, qualified_name):
        found, is_primitive, actor, _ = self.lookup(qualified_name)
        if not found:
            return ErrorDoc(qualified_name, None, "Unknown actor")
        if not actor:
            return ErrorDoc(qualified_name, None, "Broken actor")

        namespace, name = qualified_name.rsplit('.', 1)
        if is_primitive:
            args = self._get_args(actor)
            inputs, outputs, doclines = self._parse_docstring(actor)
            requires = getattr(actor, 'requires', [])
            doc = ActorDoc(namespace, name, args, inputs, outputs, doclines, requires)
        else:
            if type(actor) is dict:
                return ErrorDoc(namespace, name, "Old-style components are not valid")
            args = {'mandatory':actor.arg_names, 'optional':{}}
            inputs = [(x, "", {}) for x in actor.inports or []] # FIXME append port docs and port properties
            outputs = [(x, "", {}) for x in actor.outports or []] # FIXME append port docs and port properties
            doclines = actor.docstring.splitlines()
            definition = actor.children[0]
            doc = ComponentDoc(namespace, name, args, inputs, outputs, doclines, definition)
        return doc


    def root_docs(self):
        modules = [self.module_docs(x) for x in self.modules()]
        return ModuleDoc('Calvin', modules, [], ["A systematic approach to handling impedance mismatch in IoT."])


    def metadata(self, qualified_name):
        doc = self._help(qualified_name)
        return doc.metadata()

    def _help(self, what):
        if not what:
            doc = self.docs
        else:
            search_list = what.split('.')
            doc = self.docs.search(search_list)
        if not doc:
            doc = ErrorDoc(what, None, "No such entity")
        return doc


    def help_raw(self, what=None):
        doc = self._help(what)
        metadata = doc.metadata()
        metadata['short_desc'] = doc.short_desc
        metadata['long_desc'] = doc.docs
        if doc.label in ["Actor", "Component"]:
            metadata['input_docs'] = {port.name:port.docs for port in doc.inports}
            metadata['output_docs'] = {port.name:port.docs for port in doc.outports}
        return json.dumps(metadata, default=node_encoder)


    def _formatter(self, doc, compact=False, formatting='plain', links=False):
        if compact:
            return doc.compact
        if formatting != 'md':
            return doc.detailed
        return doc.markdown_links if links else doc.markdown

    def help(self, what=None, compact=False, formatting='plain', links=False):
        """Return help for <what>"""
        doc = self._help(what)
        formatter = self._formatter(doc, compact, formatting, links)
        return formatter()
        # if compact:
        #     return doc.compact()
        # return doc.detailed(md=bool(formatting == 'md'), links=links)


    def documentation(self, formatting='md', links=True):
        doc = self.docs
        docs = []
        visit = [doc]
        while visit:
            next = visit.pop(0)
            if type(next) is ErrorDoc:
                continue
            if type(next) is ModuleDoc:
                visit.extend(next.actors)
                visit.extend(next.modules)
            docs.append(next)
        # docs = [x.detailed(md=bool(formatting == 'md'), links=links) for x in docs if type(x) is not ErrorDoc]
        docs = [self._formatter(x, False, formatting, links)() for x in docs if type(x) is not ErrorDoc]
        docs = "\n".join(docs)
        return docs



def install_component(namespace, definition, overwrite):
    astore = ActorStore()
    return astore.add_component(namespace, definition.name, definition, overwrite)


if __name__ == '__main__':
    import json
    import sys

    d = DocumentationStore()
    def gather_actors(module):
        # Depth first
        l = []
        for m in d.modules(module):
            l = l + gather_actors(m)
        actors = d.actors(module)
        if module:
            # Add namespace
            actors = ['.'.join([module, a]) for a in actors]
        return l + actors

    def list_actors():
        print "Actors:"
        l = gather_actors('')
        for a in l:
            print "  ", a

    def list_actors_with_default_args():
        l = gather_actors('')
        # bad_args = [x for x in l if not 'args' in d.metadata(x)]
        with_defaults = [x for x in l if 'args' in d.metadata(x) and d.metadata(x)['args']['optional']]
        print "With default params:"
        for a in with_defaults:
            print "  ", a, ":", d.metadata(a)['args']['optional'].keys()

    list_actors()
    list_actors_with_default_args()
