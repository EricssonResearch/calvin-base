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

from calvin.utilities import calvinconfig
from calvin.utilities.calvinlogger import get_logger

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
        base_path = os.path.dirname(__file__)
        # paths = [p for p in _conf.get('global', self.conf_paths_name) if not os.path.isabs(p)]
        # abs_paths = [p for p in _conf.get('global', self.conf_paths_name) if os.path.isabs(p)]
        paths = _conf.get('global', self.conf_paths_name)
        self._MODULE_PATHS = [os.path.join(base_path, p) if not os.path.isabs(p) else p for p in paths]
        self._MODULE_CACHE = {}


    def update(self):
        """Should be called after a module has been added at runtime."""
        self._MODULE_CACHE = self.find_all_modules()


    def directories(self):
        for path in self._MODULE_PATHS: # FIXME: Reverse order

            if not os.path.exists(path):
                continue

            for dir, subdirs, _ in os.walk(path):
                rel_path = os.path.relpath(dir, path)
                # Skip top directory
                if rel_path == '.':
                    continue
                namespace = _rel_path_to_namespace(rel_path)
                files = _files_in_dir(dir, ('.py', '.comp'))

                yield (dir, namespace, files)

                # Exclude special directories
                for exclude in self._excluded_dirs:
                    if exclude in subdirs:
                        subdirs.remove(exclude)


    def _load_pymodule(self, name, path):
        if not os.path.isfile(path):
            return None
        pymodule = None
        try:
            pymodule = imp.load_source(name, path)
            # Check if we have a module or not
            if not isinstance(pymodule, ModuleType):
                pymodule = None
                raise Exception("Invalid module")
        except Exception as e:
            _log.exception("Could not load python module")
        finally:
            return pymodule


    def _load_pyclass(self, name, path):
        if not os.path.isfile(path):
            return None
        pymodule = self._load_pymodule(name, path)
        pyclass = pymodule and pymodule.__dict__.get(name, None)
        if not pyclass:
            _log.debug("No entry %s in %s" % (name, path))
        return pyclass


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
    __metaclass__ = Singleton

    def __init__(self):
        self.conf_paths_name = 'actor_paths'
        super(ActorStore, self).__init__()
        self.update()


    def lookup(self, qualified_name):
        """
        Look up actor using qualified_name, e.g. foo.bar.Actor
        Return a tuple (found, is_primitive, info) where
            found:         boolean
            is_primitive:  boolean
            info:          if is_primitive is
                            True  => actor object
                            False => component definition dictionary
        """
        namespace, _, actor_type = qualified_name.rpartition('.')
        # Search in the order given by config
        for path in self.paths_for_module(namespace):
            # Primitives has precedence over components
            actor_path = os.path.join(path, actor_type + '.py')
            actor_class = self._load_pyclass(actor_type, actor_path)
            if actor_class:
                inports, outports = self._gather_ports(actor_class)
                actor_class.inport_names = inports
                actor_class.outport_names = outports
                return (True, True, actor_class)
        for path in self.paths_for_module(namespace):
            actor_path = os.path.join(path, actor_type + '.comp')
            comp = self.load_component(actor_type, actor_path)
            if comp:
                return (True, False, comp)
        return (False, False, None)


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


    def load_component(self, name, path):
        if not os.path.isfile(path):
            return None
        try:
          with open(path, 'r') as source:
            dict = json.load(source)
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
      found, is_primitive, _ = self.lookup(qualified_name)
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
          json.dump(comp, f)
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


class DocumentationStore(ActorStore):
    """Interface to documentation"""


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


    def module_docs(self, namespace):
        """
        Return a dict with docstrings for namespace.

        Since a namespace can be implemented in more than one place,
        the path where docstring was found is used as key.
        """
        doc = {
            'ns': namespace, 'name': '',
            'type': 'module',
            'short_desc': '',
            'long_desc': '',
            'modules': self.modules(namespace),
            'actors': self.actors(namespace),
            }
        paths = self.paths_for_module(namespace)
        for path in paths:
            docpath = os.path.join(path, '__init__.py')
            pymodule = self._load_pymodule('__init__', docpath)
            if pymodule and pymodule.__doc__:
                doclines = pymodule.__doc__.splitlines()
                doc['short_desc'] = doclines[0]
                doc['long_desc'] = '\n'.join(doclines[2:])
                break
        if not doc['short_desc'] and not doc['long_desc']:
            doc['short_desc'] = 'No documentation for "%s"' % namespace
        return doc


    def actor_docs(self, actor_type):
        found, is_primitive, actor = self.lookup(actor_type)
        if not found:
            return None
        if is_primitive:
            docs = self.primitive_docs(actor_type, actor)
        else:
            docs = self.component_docs(actor_type, actor)
        return docs


    def primitive_docs(self, actor_type, actor_class):
        """Combine info from class and docstring into actor raw docs"""
        namespace, name = actor_type.rsplit('.', 1)
        # Extract docs
        inputs, outputs, doctext = self._parse_docstring(actor_class)

        doc = {
            'ns': namespace, 'name': name,
            'type': 'actor',
            'short_desc': doctext[0],
            'long_desc': '\n'.join(doctext[1:]),
            'args': self._get_args(actor_class),
            'inputs': inputs,
            'outputs': outputs,
            }
        return doc


    def component_docs(self, comp_type, compdef):
        """Combine info from compdef to raw docs"""
        namespace, name = comp_type.rsplit('.', 1)
        doctext = compdef['docstring'].splitlines()
        doc = {
            'ns': namespace, 'name': name,
            'type': 'component',
            'short_desc': doctext[0],
            'long_desc': '\n'.join(doctext[1:]),
            'requires':list({compdef['structure']['actors'][a]['actor_type'] for a in compdef['structure']['actors']}),
            'args': {'mandatory':compdef['arg_identifiers'], 'optional':{}},
            'inputs': [(p, self._fetch_port_docs(compdef, 'in', p)) for p in compdef['inports']],
            'outputs': [(p, self._fetch_port_docs(compdef, 'out', p)) for p in compdef['outports']],
            }
        return doc


    def _fetch_port_docs(self, compdef, port_direction, port_name):
        structure = compdef['structure']
        for c in structure['connections']:
            if port_direction.startswith('in'):
                actor, port, target_actor, target_port = c['src'], c['src_port'],c['dst'], c['dst_port']
            else:
                actor, port, target_actor, target_port = c['dst'], c['dst_port'], c['src'], c['src_port']
            if not actor and port == port_name and target_actor in structure['actors']:
                return self.port_docs(structure['actors'][target_actor]['actor_type'], port_direction, target_port)
        return 'Not documented'


    def port_docs(self, actor_type, port_direction, port_name):
        docs = ''
        adoc = self.actor_docs(actor_type)
        if not adoc:
            return docs
        pdocs = adoc['inputs'] if port_direction.startswith('in') else adoc['outputs']
        for port, pdoc in pdocs:
            if port == port_name:
                docs = pdoc
                break
        return docs


    def root_docs(self):
        doc = {
            'ns': None, 'name': 'Calvin',
            'type': 'module',
            'short_desc': 'Merging cloud and IoT',
            'long_desc': """A systematic approach to handling impedence mismatch in device-to-device, device-to-service, and service-to-service operations.""",
            'modules': self.modules(),
            'footer': '(C) 2015',
            }
        return doc


    def _list_items(self, items, namespace):
        lines = []
        for name in items:
            full_name = namespace + "." + name if namespace else name
            lines.append(self._format_terse(self.help_raw(full_name)))
        return '\n\n'.join(lines)


    def _list_ports(self, items):
        lines = []
        for name, desc in items:
            lines.append("%s\n:    %s" % (name, desc))
        return '\n\n'.join(lines)

    def _escape_string_arg(self, arg):
        if type(arg) != str:
            return arg
        return '"'+arg.encode('string_escape')+'"'

    def _format_args(self, args):
        opt_list = ['{0}={1}'.format(param, self._escape_string_arg(default)) for param, default in args['optional'].iteritems()]
        arg_list = args['mandatory'] + opt_list
        return ', '.join(arg_list)


    def _format_detailed(self, raw):
        doc = ''
        if 'header' in raw:
            doc += "{header}\n----\n".format(**raw)
        if raw['type'] == 'module':
            doc += self._format_detailed_module(raw)
        else:
            doc += self._format_detailed_actor(raw)
        if 'footer' in raw:
            doc += "\n----\n{footer}".format(**raw)
        return doc


    def _format_detailed_actor(self, raw):
        doc = "#### {ns}.{name}({fargs})\n\n{short_desc}\n\n".format(fargs=self._format_args(raw['args']), **raw)
        doc += "%s\n\n" % raw['long_desc'] if raw['long_desc'] else ''
        if raw['type'] == 'component':
            doc += '\n##### Requires\n\n{req_list}\n'.format(req_list=', '.join(raw['requires']))
        if raw['inputs']:
            doc += '\n##### Inputs\n\n{ports}\n'.format(ports=self._list_ports(raw['inputs']))
        if raw['outputs']:
            doc += '\n##### Outputs\n\n{ports}\n'.format(ports=self._list_ports(raw['outputs']))
        return doc


    def _format_detailed_module(self, raw):
        if not raw['ns']:
            doc = "## {name}\n\n{short_desc}\n\n".format(**raw)
        else:
            doc = "## Module: {ns}\n\n{short_desc}\n\n".format(**raw)
        doc += "%s\n\n" % raw['long_desc'] if raw['long_desc'] else ''
        if raw['modules']:
            doc += '\n### Modules\n\n{items}\n'.format(items=self._list_items(raw['modules'], raw['ns']))
        if 'actors' in raw and raw['actors']:
            doc += '\n### Actors\n\n{items}\n'.format(items=self._list_items(raw['actors'], raw['ns']))
        return doc


    def _format_compact(self, raw):
        doc = ''
        if raw['type'] == 'module':
            doc += self._format_compact_module(raw)
        else:
            doc += self._format_compact_actor(raw)
        return doc


    def _format_compact_actor(self, raw):
        doc = "{ns}.{name}({fargs}): {short_desc}\n".format(fargs=self._format_args(raw['args']), **raw)
        if raw['type'] == 'component':
            doc += 'Requires: %s\n' % ', '.join(raw['requires'])
        if raw['inputs']:
           doc += 'Inputs: %s\n' % ', '.join([p for p, _ in raw['inputs']])
        if raw['outputs']:
           doc += 'Outputs: %s\n' % ', '.join([p for p, _ in raw['outputs']])
        return doc


    def _format_compact_module(self, raw):
        doc = "%s: %s\n" % (raw['ns'] if raw['ns'] else raw['name'], raw['short_desc'])
        if raw['modules']:
            doc += 'Modules: %s\n' % ", ".join(raw['modules'])
        if 'actors' in raw and raw['actors']:
            doc += 'Actors: %s\n' % ", ".join(raw['actors'])
        return doc


    def _format_terse(self, raw):
        """Return a terse description as a single line."""
        title = raw['ns'] if raw['type'] == 'module' else raw['name']
        doc = "%s\n:    %s" % (title , raw['short_desc'])
        return doc


    def help_raw(self, what):
        """
        Return help for 'what' in a structured form, but not suitable for printing as-is.
        If what is None, return help on the command itself.
        """
        if what:
            # First check for actors and components
            doc = self.actor_docs(what)
            if not doc:
                doc = self.module_docs(what)
        else:
            doc = self.root_docs()
        return doc


    def help(self, what=None, compact=False, formatting='md'):
        """Return help for """
        raw = self.help_raw(what)
        # print "raw", raw
        if not raw:
            doc = 'No help for "%s"' % what
        else:
            doc = self._format_compact(raw) if compact else self._format_detailed(raw)
        return doc


if __name__ == '__main__':
    import json

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
    print ds.help(what='misc.ArgWrapper', compact=False)
    print "====="
    print ds.help(what='misc.ArgWrapper', compact=True)

    print
    for actor in ['std.Constant', 'std.Join', 'std.Identity', 'io.FileReader']:
        found, is_primitive, actor_class = a.lookup(actor)
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
