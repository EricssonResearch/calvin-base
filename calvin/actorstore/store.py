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

from calvin.csparser.astnode import node_encoder, node_decoder
from calvin.utilities import calvinconfig
from calvin.utilities import dynops
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.calvin_callback import CalvinCB


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
            _log.exception("Could not load python module")
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
            actor_class.inport_names = inports
            actor_class.outport_names = outports
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
        docstring = class_.__doc__
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
                line = line.strip()
                if line:
                    dest.append(line)
                continue

            if dest in [inputs, outputs]:
                match = re.match(r'^\s*([a-zA-Z][a-zA-Z0-9_]*)\s*:?\s*(.*)$', line)
                if match:
                    dest.append((match.group(1), match.group(2)))

        return (inputs, outputs, doctext)


    def _gather_ports(self, class_):
        inputs, outputs, _ = self._parse_docstring(class_)
        return ([p for (p, _) in inputs], [p for (p, _) in outputs])


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
        self.node.storage.get_index(['actor', 'signature', signature],
                                    CalvinCB(self._global_lookup_cb, signature=signature, org_cb=cb))

    def _global_lookup_cb(self, key, value, signature, org_cb):
        if value:
            nbr = [len(value)]
            actors = []
            for a in value:
                self.node.storage.get('actor_type-', a,
                            CalvinCB(self._global_lookup_collect, nbr, actors, signature=signature, org_cb=org_cb))

    def _global_lookup_collect(self, key, value, nbr, actors, signature, org_cb):
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


def _escape_string_arg(arg):
    if type(arg) != str:
        return arg
    return '"{}"'.format(arg.encode('string_escape'))

def _escape_md(txt):
    escape = "\\`*_{}[]()<>#+-.!"
    for c in escape:
        txt = txt.replace(c, "\\"+c)
    return txt

class DocObject(object):
    """docstring for DocObject"""
    def __init__(self, namespace, name=None, docs=None):
        super(DocObject, self).__init__()
        self.ns = namespace
        self.name = name
        if type(docs) is list:
            docs = "\n".join(docs)
        self.docs = docs or "DocObject"

    @property
    def qualified_name(self):
        if self.name:
            return "{}.{}".format(self.ns, self.name)
        return self.ns

    @property
    def short_desc(self):
        short_desc, _, _ = self.docs.partition('\n')
        return short_desc

    @property
    def desc(self):
        return self.docs

    def terse(self):
        return "{} : {}".format(self.qualified_name, self.short_desc)

    def compact(self):
        return self.terse()

    def detailed(self, md=False):
        return self.terse()

    def raw(self):
        return self.__dict__

    def json(self):
        return self.__repr__()

    def metadata(self):
        return {'is_known': False}

    def __repr__(self):
        def _convert(x):
            try:
                return x.name or x.ns
            except:
                return None

        r = {'type':str(self.__class__.__name__)}
        r.update(self.__dict__)
        return json.dumps(r, default=_convert)


class ErrorDoc(DocObject):
    """docstring for ErrDoc"""
    def __init__(self, namespace, name, short_desc):
        docs = "(Error) {}".format(short_desc or "Unknown error")
        super(ErrorDoc, self).__init__(namespace, name, docs)


class ModuleDoc(DocObject):
    """docstring for ModuleDoc"""
    def __init__(self, namespace, modules, actors, doclines):
        super(ModuleDoc, self).__init__(namespace, None, doclines)
        self.modules = modules
        self.actors = actors

    def search(self, search_list):
        if not search_list:
            return self
        name = search_list.pop(0)
        for x in self.modules:
            if name == x.ns:
                return x.search(search_list)
        for x in self.actors:
            if name == x.name:
                if not search_list:
                    return x
                return None # Error
        return None


    def compact(self):
        FMT = "{0.qualified_name}\n{0.short_desc}\n\nModules: {xmodules}\nActors:  {xactors}\n"
        x = {
            'xmodules': ", ".join([x.ns for x in self.modules]) or "-",
            'xactors': ", ".join([x.name for x in self.actors]) or "-"
        }
        return FMT.format(self, **x)

    def detailed(self, md=False):
        if md:
            FMT = "## Module: {0.qualified_name} [module_{0.qualified_name}]\n\n{xdesc}\n\n### Modules:\n\n{xmodules}\n\n### Actors:\n\n{xactors}\n\n****\n"
            MODULE_FMT = "[{0.ns}][module_{0.ns}]\n: {0.short_desc}\n"
            ACTOR_FMT = "[{0.name}][actor_{0.ns}_{0.name}]\n: {0.short_desc}\n"
        else:
            FMT = "Module: {0.qualified_name}\n{xheading}\n{0.desc}\n\nModules:\n{xmodules}\n\nActors:\n{xactors}\n\n"
            MODULE_FMT = "  {0.ns} : {0.short_desc}"
            ACTOR_FMT = "  {0.name} : {0.short_desc}"
        x= {
            'xheading' : '-'*40,
            'xdesc': _escape_md(self.desc),
            'xmodules': "\n".join([MODULE_FMT.format(x) for x in self.modules if type(x) is not ErrorDoc]) or "-",
            'xactors': "\n".join([ACTOR_FMT.format(x) for x in self.actors if type(x) is not ErrorDoc]) or "-",
        }
        return FMT.format(self, **x)


class ActorDoc(DocObject):
    """docstring for ActorDoc"""
    def __init__(self, namespace, name, args, inputs, outputs, doclines):
        super(ActorDoc, self).__init__(namespace, name, doclines)
        self.args = args
        self.inputs = [p for p, _ in inputs]
        self.input_docs = [d for _, d in inputs]
        self.outputs = [p for p, _ in outputs]
        self.output_docs = [d for _, d in outputs]


    @property
    def formatted_args(self):
        return self.args['mandatory'] + ["{}={}".format(k, _escape_string_arg(v)) for k,v in self.args['optional'].iteritems()]

    @property
    def slug(self):
        return self.qualified_name.replace('.', '_')

    def formatted_inputs(self, fmt):
        return [fmt.format(p, doc) for p, doc in zip(self.inputs, self.input_docs)]

    def formatted_outputs(self, fmt):
        return [fmt.format(p, doc) for p, doc in zip(self.outputs, self.output_docs)]

    def metadata(self):
        metadata = {
            'ns': self.ns,
            'name': self.name,
            'type': 'actor',
            'args': self.args,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'is_known': True
        }
        return metadata


    def compact(self):
        FMT = "{0.qualified_name}({xargs})\n{0.desc}\n\nInports:  {xinports}\nOutports: {xoutports}\n"
        x = {
            'xargs': ", ".join(self.formatted_args),
            'xinports': ", ".join(self.inputs) or "-",
            'xoutports': ", ".join(self.outputs) or "-"
        }
        return FMT.format(self, **x)


    def _detailed_data(self, port_fmt):
        return {
            'xlabel' : 'Actor',
            'xargs' : ", ".join(self.formatted_args),
            'xdesc' : _escape_md(self.desc),
            'xheading' : '-'*40,
            'xinports' : "\n".join(self.formatted_inputs(port_fmt)) or "-",
            'xoutports' : "\n".join(self.formatted_outputs(port_fmt)) or "-",
        }


    def _detailed_plain_fmt(self):
        FMT = "{xlabel}: {0.qualified_name}({xargs})\n{xheading}\n{0.desc}\n\nInports:\n{xinports}\n\nOutports:\n{xoutports}\n\n"
        PORT_FMT = "  {} : {}"
        x = self._detailed_data(PORT_FMT)
        return FMT, x


    def _detailed_md_fmt(self):
        FMT = "## {xlabel}: {0.qualified_name}({xargs}) [actor_{0.slug}]\n\n{xdesc}\n\n### Inports:\n\n{xinports}\n\n### Outports:\n\n{xoutports}\n\n****\n"
        PORT_FMT = "{}\n: {}\n"
        x = self._detailed_data(PORT_FMT)
        return FMT, x


    def detailed(self, md=False):
        if md:
            fmt, x = self._detailed_md_fmt()
        else:
            fmt, x = self._detailed_plain_fmt()
        return fmt.format(self, **x)



class ComponentDoc(ActorDoc):
    #
    # Augment a couple of methods in the superclass
    #
    def __init__(self, namespace, name, args, inputs, outputs, doclines, requires, definition):
        super(ComponentDoc, self).__init__(namespace, name, args, inputs, outputs, doclines)
        self.requires = requires # "FIXME"
        self.definition = definition # actor.children[0]

    def metadata(self):
        metadata = super(ComponentDoc, self).metadata()
        metadata['type'] = 'component'
        metadata['definition'] = self.definition
        metadata['requires'] = self.requires
        return metadata

    def compact(self):
        FMT = "{xbase}\n\nRequires: {xrequires}"
        x = {
            'xbase': super(ComponentDoc, self).compact(),
            'xrequires': ", ".join(self.requires),
        }
        return FMT.format(**x)

    def _detailed_data(self, port_fmt):
        # Will be called from superclass' _detailed_xxx_fmt
        x = super(ComponentDoc, self)._detailed_data(port_fmt)
        x['xlabel'] = 'Component'
        x['xrequires'] = ", ".join(self.requires)
        return x

    def _detailed_plain_fmt(self):
        FMT, x = super(ComponentDoc, self)._detailed_plain_fmt()
        FMT = FMT + "Requires: {xrequires}\n\n"
        return FMT, x

    def _detailed_md_fmt(self):
        FMT, x = super(ComponentDoc, self)._detailed_md_fmt()
        FMT = FMT.rstrip('\n*')
        FMT = FMT + "\n### Requires: {xrequires}\n\n****\n"
        return FMT, x



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

        namespace, name = qualified_name.rsplit('.', 1)
        if is_primitive:
            args = self._get_args(actor)
            inputs, outputs, doclines = self._parse_docstring(actor)
            doc = ActorDoc(namespace, name, args, inputs, outputs, doclines)
        else:
            if type(actor) is dict:
                return ErrorDoc(namespace, name, "Old-style components are not valid")
            args = {'mandatory':actor.arg_names, 'optional':{}}
            inputs = [(x, "") for x in actor.inports or []] # FIXME append port docs
            outputs = [(x, "") for x in actor.outports or []] # FIXME append port docs
            doclines = actor.docstring.splitlines()
            requires = [] # FIXME Requirements
            definition = actor.children[0]
            doc = ComponentDoc(namespace, name, args, inputs, outputs, doclines, requires, definition)
        return doc


    def root_docs(self):
        modules = [self.module_docs(x) for x in self.modules()]
        return ModuleDoc('Calvin', modules, [], ["A systematic approach to handling impedence mismatch in IoT."])


    def metadata(self, qualified_name):
        doc = self._help(qualified_name)
        return doc.metadata()


    def _help(self, what):
        if what is None:
            doc = self.docs
        else:
            search_list = what.split('.')
            doc = self.docs.search(search_list)
        if not doc:
            doc = ErrorDoc(what, None, "No such entity")
        return doc


    def help_raw(self, what=None):
        doc = self._help(what)
        return doc.raw()


    def help(self, what=None, compact=False, formatting='plain'):
        """Return help for <what>"""
        doc = self._help(what)
        if compact:
            return doc.compact()
        return doc.detailed(md=bool(formatting == 'md'))


    def documentation(self, formatting='md'):
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
        docs = [x.detailed(md=bool(formatting == 'md')) for x in docs if type(x) is not ErrorDoc]
        docs = "\n".join(docs)
        return docs



def install_component(namespace, definition, overwrite):
    astore = ActorStore()
    return astore.add_component(namespace, definition.name, definition, overwrite)


if __name__ == '__main__':
    import json
    import sys

    d = DocumentationStore()

    # print d.documentation()
    print d.help()
    # print d.metadata('std.Rip')
    # print d.metadata('foo')

    print d.help()
    print d.help('std')
    print d.help('std.Select')
    print d.help('std.Rip')
    print d.help('std.Bazz')
    print d.help('std.DelayedCounter')

    print d.help(compact=True)
    print d.help('std', compact=True)
    print d.help('std.Select', compact=True)
    print d.help('std.Rip', compact=True)
    print d.help('std.Bazz', compact=True)
    print d.help('std.DelayedCounter', compact=True)

    sys.exit()

    a = ActorStore()
    ds = DocumentationStore()

    print ds.help()
    print "====="
    print ds.help(compact=True)
    print "====="
    print ds.help(what='xyz', compact=True)
    print "====="
    print ds.help(what='std', compact=False)


    print ds.help(what='std', compact=True)
    print ds.help(what='std.Constant', compact=False)
    print "====="
    print ds.help(what='std.SumActor', compact=True)
    print "====="
    print ds.help(what='std.Foo', compact=False)
    print "====="
    print ds.help(what='misc.ArgWrapper', compact=True)

    print
    for actor in ['std.Constant', 'std.Join', 'std.Identity', 'io.FileReader']:
        found, is_primitive, actor_class, signer = a.lookup(actor)
        if not found or not is_primitive:
            raise Exception('Bad actor')
        print actor, ":", ds._get_args(actor_class)
    #
    #
    # print json.dumps(a.find_all_modules(), sort_keys=True, indent=4)
    # print a.modules()
    # print a.modules('foo')
    # print a.modules('foo.bar')
    # print a.modules('network')
    # print ds.module_docs('foo.bar')
    # print "\n================\n"
    #
    # for m in a.modules():
    #     print m
    #     print "  ", a.actors(m)
    # actor_class =  a.lookup('std.Tee')
    # print actor_class
    # print a.lookup('misc.ArgWrapper')
    # for x in ['std.Tee', 'foo', 'foo.bar', 'foo.bar.baz', 'misc.ArgWrapper', 'no.way']:
    #     print
    #     print "------------------------"
    #     print ds.docs_for(x)
    #     print "------------------------"
    #
    #
    # astore = ActorStore()
    # actor_types = []
    #
    # def gather_actors(module):
    #     # Depth first
    #     l = []
    #     for m in DocumentationStore().modules(module):
    #         l = l + gather_actors(m)
    #     actors = DocumentationStore().actors(module)
    #     if module:
    #         # Add namespace
    #         actors = ['.'.join([module, a]) for a in actors]
    #     return l + actors
    #
    #
    # print gather_actors('')
