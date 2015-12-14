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

from calvin.actorstore.store import ActorStore, GlobalStore
from calvin.utilities.calvinlogger import get_logger


_log = get_logger(__name__)


def full_port_name(namespace, actor_name, port_name):
    if actor_name != ".":
        return namespace + ':' + actor_name + '.' + port_name
    return namespace + '.' + port_name


class Analyzer(object):

    """
    Process an cs_info dictionary (output from calvin parser) to
    produce a running calvin application.
    """

    # FIXME: Provide additional checks making use of
    #        - actor_def.inport_names and actor_def.outport_names
    #        - make use of arg_type (STRING, NUMBER, etc.)
    #        - analyze the actions wrt port use and token consumption:
    #          for f in actor_def.action_priority:
    #              print f.__name__, [x.cell_contents for x in f.__closure__]
    #
    def __init__(self, cs_info, verify=True):
        super(Analyzer, self).__init__()
        self.cs_info = cs_info
        self.local_components = cs_info['components'] if 'components' in cs_info else {}
        self.constants = {}
        self.app_info = {}
        self.connections = {}
        self.actors = {}
        self.verify = verify
        self.actorstore = ActorStore()
        self.analyze()

    def analyze(self):
        """
        Analyze a CalvinScript in canonical format (i.e. as given by the CS parser)
        and produce an app_info structure, sutitable for deploying an application.
        The app_info contains a dict of actors and their type, arguments, etc., and
        a dict of connections between ports where output ports are keys and the
        corresponding value is a list of input ports to connect to.
        The value for the 'valid' key is True of the script is syntactically correct.

        A CalvinScript consists of component definitions, and a _structure_ defining
        the actual script. Each component definition consists of statements declaring
        ports and arguments, and a _structure_ part, defining what the component does.
        """
        self.script_name = os.path.basename(self.cs_info['sourcefile'])
        s = self.cs_info['structure']
        root_namespace, _ = os.path.splitext(self.script_name)
        self.constants = self.cs_info['constants']
        argd = {}
        valid = True

        try:
            self.analyze_structure(s, root_namespace, argd)
        except Exception as e:
            _log.exception(e)
            valid = False
        self.app_info = {'valid': valid, 'actors': self.actors, 'connections': self.connections}
        if self.script_name:
            self.app_info['name'] = self.script_name

    def debug_info(self, d):
        file = 'File "%s"' % self.script_name
        line = ', line %d' % d['dbg_line'] if 'dbg_line' in d else ''
        return file + line

    def lookup_constant(self, identifier):
        """
        Return value for constant 'identifier'
        Raise an exception if not found
        """
        kind, value = self.constants[identifier]
        if kind != "IDENTIFIER":
            return (kind, value)
        return self.lookup_constant(value)

    def lookup(self, actor_type):
        """
        Search for the definition of 'actor_type'.
        Returns a tuple (found, is_primitive, info) where info is either a
        class (primitive) or a dictionary with component definition
        Search order:
          1 - components defined in the current script: self.local_components
          2 - primitive actors in the order defined by actor store
          3 - components in the order defined by actor store
        Steps 2 and 3 are handled by generic lookup in actor store
        """
        if actor_type in self.local_components:
            compdef = self.local_components[actor_type]
            return compdef, False
        found, is_actor, info = self.actorstore.lookup(actor_type)
        if self.verify and not found:
            msg = 'Actor "{}" not found.'.format(actor_type)
            raise Exception(msg)
        return info, is_actor or not found

    def add_connection(self, src_actor_port, dst_actor_port):
        if type(dst_actor_port) is list:
            self.connections.setdefault(src_actor_port, []).extend(dst_actor_port)
        else:
            self.connections.setdefault(src_actor_port, []).append(dst_actor_port)

    def expand_literals(self, structure, argd):
        # Check for literals on inports...
        const_count = 1
        implicit = [c for c in structure['connections'] if not c['src']]
        for c in implicit:
            kind, value = c['src_port']
            if kind == "IDENTIFIER":
                if value in argd:
                    kind, value = ('VALUE', argd[value])
                else:
                    kind, value = self.lookup_constant(value)
            # Replace constant with std.Constant(data=value, n=-1) its outport
            name = '_literal_const_' + str(const_count)
            const_count += 1
            # Replace implicit actor with actual actor ...
            structure['actors'][name] = {
                'actor_type': 'std.Constant',
                'args': {
                    'data': (kind, value),
                    'n': ('NUMBER', -1)
                },
                'dbg_line': c['dbg_line']}
            # ... and create a connection from it
            c['src'] = name
            c['src_port'] = 'token'

    def resolve_arguments(self, arguments, argd):
        args = {}
        for arg_name, (arg_type, arg_value) in arguments.iteritems():
            if arg_type == 'IDENTIFIER':
                # We are looking for the value of a variable whose name is in value
                variable_name = arg_value
                if variable_name in argd:
                    arg_value = argd[variable_name]
                else:
                    _, arg_value = self.lookup_constant(variable_name)
            args[arg_name] = arg_value
        return args

    def create_connection(self, c, namespace, in_mappings, out_mappings):
        # export_mapping = {'in':{}, 'out':{}}
        # Get the full port name.
        # If src/dst is ".", the full port name is component port name at caller level
        src_actor_port = full_port_name(namespace, c['src'], c['src_port'])
        dst_actor_port = full_port_name(namespace, c['dst'], c['dst_port'])

        # resolve any references to components first
        # N.B. if there is a match for src_actor_port the result is a list:
        dst_actor_port = in_mappings.get(dst_actor_port, dst_actor_port)
        src_actor_port = out_mappings.get(src_actor_port, src_actor_port)

        # Add connections if possible, or export a port mapping for calling level
        if c['src'] != '.' and c['dst'] != '.':
            self.add_connection(src_actor_port, dst_actor_port)
            export_mapping = {}, {}
        elif c['dst'] != '.':
            # Add mapping from component inport to internal actors/components
            if type(dst_actor_port) is not list:
                dst_actor_port = [dst_actor_port]
            export_mapping = {src_actor_port: dst_actor_port}, {}
        else:
            # Add mapping from internal actor/component to component outport
            export_mapping = {}, {dst_actor_port: src_actor_port}

        return export_mapping

    def analyze_structure(self, structure, namespace, argd):
        """
        Analyze a (sub) structure and resolve actor names, arguments, and connections.
        Parameter argd is a dict with arguments for the structure
        Returns a dict with port mappings corresponding to the externally visible ports
        of the structure, i.e. the ports of a component.
        """
        # Check for literals on inports...
        self.expand_literals(structure, argd)

        in_mappings = {}
        out_mappings = {}
        for actor_name, actor_def in structure['actors'].iteritems():
            # Look up actor
            info, is_actor = self.lookup(actor_def['actor_type'])
            # Resolve arguments
            args = self.resolve_arguments(actor_def['args'], argd)

            qualified_name = namespace + ':' + actor_name

            if is_actor:
                # Create the actor signature to be able to look it up in the GlobalStore if neccessary
                signature_desc = {'is_primitive': True,
                                  'actor_type': actor_def['actor_type'],
                                  'inports': [],
                                  'outports': []}
                for c in structure['connections']:
                    if actor_name == c['src'] and c['src_port'] not in signature_desc['outports']:
                        signature_desc['outports'].append(c['src_port'])
                    elif actor_name == c['dst'] and c['dst_port'] not in signature_desc['inports']:
                        signature_desc['inports'].append(c['dst_port'])
                signature = GlobalStore.actor_signature(signature_desc)
                # Add actor and its arguments to the list of actor instances
                self.actors[qualified_name] = {'actor_type': actor_def['actor_type'], 'args': args,
                                               'signature': signature, 'signature_desc': signature_desc}
            else:
                # Recurse into components
                # qualified_name constitutes a namespace here
                comp_in_mapping, comp_out_mapping = self.analyze_structure(info['structure'], qualified_name, args)
                in_mappings.update(comp_in_mapping)
                out_mappings.update(comp_out_mapping)

        export_in_mappings = {}
        export_out_mappings = {}
        for c in structure['connections']:
            in_mapping, out_mapping = self.create_connection(c, namespace, in_mappings, out_mappings)
            for p in in_mapping:
                export_in_mappings.setdefault(p, []).extend(in_mapping[p])
            export_out_mappings.update(out_mapping)

        return export_in_mappings, export_out_mappings


def generate_app_info(cs_info, verify=True):
    a = Analyzer(cs_info, verify=verify)
    return a.app_info


if __name__ == '__main__':
    import cscompiler
    import json

    filename = 'scripts/test2.calvin'
    with open(filename, 'r') as f:
        script = f.read()
        print script
        print "---------------"
        data, errors, warnings = cscompiler.compile(script, filename)
        if errors:
            print "{reason} {script} [{line}:{col}]".format(script=filename, **errors[0])

        a = Analyzer(data)
        print "======= DONE ========"
        print json.dumps(a.app_info, indent=4, sort_keys=True)
