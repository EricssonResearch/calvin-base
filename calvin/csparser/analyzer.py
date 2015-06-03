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

from calvin.actorstore.store import ActorStore
from calvin.utilities.calvinlogger import get_logger


_log = get_logger(__name__)


def full_port_name(namespace, actor_name, port_name):
    if actor_name:
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
    def __init__(self, cs_info):
        super(Analyzer, self).__init__()
        self.cs_info = cs_info
        self.local_components = {c['name']:c for c in cs_info['components']}
        self.app_info = {}
        self.connections = {}
        self.actors = {}
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
        argd = {}
        valid = True

        try:
            self.analyze_structure(s, root_namespace, argd)
        except Exception as e:
            _log.exception(e)
            valid = False
        self.app_info = {'valid':valid, 'actors': self.actors, 'connections':self.connections}

    def debug_info(self, d):
        file = 'File "%s"' % self.script_name
        line = ', line %d' % d['dbg_line'] if 'dbg_line' in d else ''
        return file + line

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
            return (True, False, compdef)

        return ActorStore().lookup(actor_type)

    def add_connection(self, src_actor_port, dst_actor_port):
        if type(dst_actor_port) is list:
            self.connections.setdefault(src_actor_port, []).extend(dst_actor_port)
        else:
            self.connections.setdefault(src_actor_port, []).append(dst_actor_port)

    def analyze_structure(self, structure, namespace, argd):
        """
        Analyze a (sub) structure and resolve actor names, arguments, and connections.
        Parameter argd is a dict with arguments for the structure
        Returns a dict with port mappings corresponding to the externally visible ports
        of the structure, i.e. the ports of a component.
        """

        mappings = {'in':{}, 'out':{}}
        export_mappings = {'in':{}, 'out':{}}

        for actor_name, actor_def in structure['actors'].iteritems():
            # Look up actor
            found, is_actor, info = self.lookup(actor_def['actor_type'])
            if not found:
                msg = 'Actor "%s" not found. %s' % (actor_def['actor_type'], self.debug_info(actor_def))
                raise Exception(msg)
            # Resolve arguments
            args = {}
            for arg_name, (arg_type, arg_value) in actor_def['args'].iteritems():
                if arg_type == 'IDENTIFIER':
                    # We are looking for the value of a variable whose name is in value
                    variable_name = arg_value
                    if variable_name not in argd:
                        # If the value is missing from argd the programmer made an error, e.g.
                        # component PrefixFile(prefix, filename) -> out {
                        #   file:io.FileReader(file=foo) // Should have been 'file=filename'
                        #   ...
                        msg = 'Undefined variable "%s". %s' % (variable_name, self.debug_info(actor_def))
                        raise Exception(msg)
                    arg_value = argd[variable_name]
                args[arg_name] = arg_value

            qualified_name = namespace+':'+actor_name
            if is_actor:
                # Add actor and its arguments to the list of actor instances
                self.actors[qualified_name] = {'actor_type':actor_def['actor_type'], 'args':args}
            else:
                # Recurse into components
                # qualified_name constitutes a namespace here
                port_mappings = self.analyze_structure(info['structure'], qualified_name, args)
                mappings['in'].update(port_mappings['in'])
                mappings['out'].update(port_mappings['out'])

        for c in structure['connections']:
            # Get the full port name.
            # If src/dst is None, the full port name is component port name at caller level
            src_actor_port = full_port_name(namespace, c['src'], c['src_port'])
            dst_actor_port = full_port_name(namespace, c['dst'], c['dst_port'])

            can_resolve_src = bool(c['src'])
            can_resolve_dst = bool(c['dst'])
            if not can_resolve_src and not can_resolve_dst:
                msg = 'Mapping in > out in component is illegal. %s' % self.debug_info(c)
                raise Exception(msg)

            # resolve any references to components first
            # N.B. if there is a match for src_actor_port the result is a list:
            dst_actor_port = mappings['in'].get(dst_actor_port, dst_actor_port)
            src_actor_port = mappings['out'].get(src_actor_port, src_actor_port)

            # Add connections if possible, or add a export a port mapping for calling level
            if can_resolve_src and can_resolve_dst:
                self.add_connection(src_actor_port, dst_actor_port)
            elif can_resolve_dst:
                # Add mapping from component inport to internal actors/components
                if type(dst_actor_port) is not list:
                    dst_actor_port = [dst_actor_port]
                export_mappings['in'].setdefault(src_actor_port, []).extend(dst_actor_port)
            else:
                # Add mapping from internal actor/component to component outport
                export_mappings['out'][dst_actor_port] = src_actor_port

        return export_mappings

def generate_app_info(cs_info):
    a = Analyzer(cs_info)
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
            print "{reason} {script} [{line}:{col}]".format(script=filename, **error[0])

        a = Analyzer(data)
        print "======= DONE ========"
        print json.dumps(a.app_info, indent=4, sort_keys=True)



