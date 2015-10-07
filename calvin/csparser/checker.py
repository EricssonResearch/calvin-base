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

import json

from calvin.csparser.parser import calvin_parser
from calvin.actorstore.store import DocumentationStore
import json

class Checker(object):
    # FIXME: Provide additional checks making use of
    #        - actor_def.inport_names and actor_def.outport_names
    #        - make use of arg_type (STRING, NUMBER, etc.)
    #        - analyze the actions wrt port use and token consumption:
    #          for f in actor_def.action_priority:
    #              print f.__name__, [x.cell_contents for x in f.__closure__]
    #
    def __init__(self, cs_info, verify=True):
        super(Checker, self).__init__()
        self.ds = DocumentationStore()
        self.cs_info = cs_info
        self.constants = self.cs_info['constants']
        self.comp_defs = self.cs_info['components']
        self.errors = []
        self.warnings = []
        self.verify = verify
        self.check()

    def issue(self, fmt, **info):
        return {'reason':fmt.format(**info), 'line':info.get('line', 0), 'col':info.get('col', 0)}

    def append_error(self, fmt, **info):
        issue = self.issue(fmt, **info)
        self.errors.append(issue)

    def append_warning(self, fmt, **info):
        issue = self.issue(fmt, **info)
        self.warnings.append(issue)

    def check(self):
        """
        Check constants, local components, and program, in that order.
        Generate error and warning issues as they are encountered.
        """
        self.check_constants()
        for comp in self.comp_defs.values():
            self.check_component(comp)
        self.check_structure(self.cs_info['structure'])

    def check_component(self, comp_def):
        """
        Check connections, structure, and argument for local component
        """
        defs = self.get_definition(comp_def['name'])
        self.check_component_connections(defs, comp_def['structure']['connections'])
        self.check_structure(comp_def['structure'], comp_def['arg_identifiers'])
        implicits = self._find_implicits(comp_def['structure']['connections'])
        self.check_component_arguments(comp_def, implicits)

    def _find_implicits(self, connections):
        implicit = [c['src_port'] for c in connections if not c['src']]
        arg_names = [value for kind, value in implicit if kind == 'IDENTIFIER']
        return arg_names

    def get_definition(self, actor_type):
        """
        Get the actor/component definition from the docstore.
        For local components, let the docstore generate the definition.
        """
        if actor_type in self.comp_defs:
            return self.ds.component_docs("local."+actor_type, self.comp_defs[actor_type])
        return self.ds.actor_docs(actor_type)

    def dbg_lines(self, s):
        """Return the debug line numbers in a construct. Default to 0."""
        try:
            return [x['dbg_line'] for x in s] or [0]
        except:
            return [0]

    def twiddle_portrefs(self, is_component, port_dir):
        if port_dir not in ['in', 'out']:
            raise Exception("Invalid port direction: {}".format(port_dir))
        if is_component:
            target, target_port = ('dst', 'dst_port') if port_dir == 'out' else ('src', 'src_port')
        else:
            target, target_port = ('dst', 'dst_port') if port_dir == 'in' else ('src', 'src_port')
        return target, target_port


    def generate_ports(self, definition, actor=None):
        """
        This generator takes care of remapping src and dst with respect to programs and component definitions.
        Given definition, connections, and optionally actor it will generate a list of tuples:
        (port, target, target_port, port_dir, actor) according to the following scheme:

        component inports  : (port, 'src', 'src_port', 'in', '.')
        component outports : (port, 'dst', 'dst_port', 'out', '.')
        actor inports      : (port, 'dst', 'dst_port', 'in', actor)
        actor outports     : (port, 'src', 'src_port', 'out', actor)

        that help sorting out connections.
        """
        is_component = actor is None
        actor = '.' if is_component else actor
        for port_dir in ['in', 'out']:
            target, target_port = self.twiddle_portrefs(is_component, port_dir)
            def_dir = 'inputs' if port_dir == 'in' else 'outputs'
            for p, _ in definition[def_dir]:
                yield((p, target, target_port, port_dir, actor))


    def _verify_port_names(self, definition, connections, actor=None):
        """Look for misspelled port names."""
        # A little transformation is required depending on actor vs. component and port direction
        retval = []
        is_component = actor is None
        actor = '.' if is_component else actor
        for port_dir in ['in', 'out']:
            target, target_port = self.twiddle_portrefs(is_component, port_dir)
            def_dir = 'inputs' if port_dir == 'in' else 'outputs'
            ports = [p for p, _ in definition[def_dir]]
            invalid_ports = [(c[target_port], port_dir, c['dbg_line']) for c in connections if c[target] == actor and c[target_port] not in ports]
            retval.extend(invalid_ports)
        return retval


    def check_atleast_one_connection(self, definition, connections, actor=None):
        """Check that all ports have at least one connection"""
        retval = []
        for port, target, target_port, port_dir, actor in self.generate_ports(definition, actor):
            pc = [c for c in connections if c[target] == actor and c[target_port] == port]
            if len(pc) < 1:
                retval.append((port, port_dir, max(self.dbg_lines(connections))))
        return retval

    def check_atmost_one_connection(self, definition, connections, actor=None):
        """Check that input ports have at most one connection"""
        retval = []
        for port, target, target_port, port_dir, actor in self.generate_ports(definition, actor):
            if target == 'src':
                # Skip output (src) ports since they can have multiple connections
                continue
            pc = [c for c in connections if c[target] == actor and c[target_port] == port]
            if len(pc) > 1:
                retval.extend([(port, port_dir, c['dbg_line']) for c in pc])
        return retval


    def report_port_errors(self, fmt, portspecs, definition, actor=None):
        for port, port_dir, line in portspecs:
            self.append_error(fmt, line=line, port=port, port_dir=port_dir, actor=actor, **definition)


    def check_component_connections(self, definition, connections):
        # Check for bogus ports
        invalid_ports = self._verify_port_names(definition, connections)
        fmt = "Component {name} has no {port_dir}port '{port}'"
        self.report_port_errors(fmt, invalid_ports, definition)

        # All ports should have at least one connection...
        bad_ports = self.check_atleast_one_connection(definition, connections)
        fmt = "Component {name} is missing connection to {port_dir}port '{port}'"
        self.report_port_errors(fmt, bad_ports, definition)

        # ... but outports should have exactly one connection
        bad_ports = self.check_atmost_one_connection(definition, connections)
        fmt = "Component {name} has multiple connections to {port_dir}port '{port}'"
        self.report_port_errors(fmt, bad_ports, definition)

        # Check for illegal passthrough (.in > .out) connections
        fmt = "Component {name} passes port '{src_port}' directly to port '{dst_port}'"
        for pc in [c for c in connections if c['src']==c['dst']=='.']:
            self.append_error(fmt, line=c['dbg_line'], src_port=c['src_port'], dst_port=c['dst_port'], **definition)


    def check_actor_connections(self, actor, definition, connections):
        invalid_ports = self._verify_port_names(definition, connections, actor)
        fmt = "Actor {actor} ({ns}.{name}) has no {port_dir}port '{port}'"
        self.report_port_errors(fmt, invalid_ports, definition, actor)

        # All ports should have at least one connection...
        bad_ports = self.check_atleast_one_connection(definition, connections, actor)
        fmt = "Actor {actor} ({ns}.{name}) is missing connection to {port_dir}port '{port}'"
        self.report_port_errors(fmt, bad_ports, definition, actor)

        # ... but inports should have exactly one connection
        bad_ports = self.check_atmost_one_connection(definition, connections, actor)
        fmt = "Actor {actor} ({ns}.{name}) has multiple connections to {port_dir}port '{port}'"
        self.report_port_errors(fmt, bad_ports, definition, actor)

    def check_constants(self):
        """Verify that all constant definitions evaluate to a value."""
        for constant in self.constants:
            try:
                self.lookup_constant(constant)
            except KeyError as e:
                fmt = "Constant '{name}' is undefined"
                self.append_error(fmt, name=e.args[0])
            except:
                fmt = "Constant '{name}' has a circular reference"
                self.append_error(fmt, name=constant)


    def lookup_constant(self, identifier, seen=None):
        """
        Return value for constant 'identifier' by recursively looking for a value.
        Raise an exception if not found
        """
        seen = seen or []
        kind, value = self.constants[identifier]
        if kind != "IDENTIFIER":
            return value
        if value in seen:
            raise Exception("Circular reference in constant definition")
        seen.append(value)
        return self.lookup_constant(value, seen)

    def check_component_arguments(self, comp_def, implicits):
        """
        Warn if component declares parameters that are not used by the actors in the component.
        """
        declared_args = set(comp_def['arg_identifiers'])
        used_args = set(implicits)
        for actor_def in comp_def['structure']['actors'].values():
            used_args.update({value for kind, value in actor_def['args'].values() if kind == 'IDENTIFIER'})

        unused_args = declared_args - used_args
        for u in unused_args:
            fmt = "Unused argument: '{param}'"
            self.append_error(fmt, line=comp_def['dbg_line'], param=u)

    def check_arguments(self, definition, declaration, arguments):
        """
        Verify that all arguments are present and valid when instantiating actors.
        'arguments' is a list of the arguments whose value is supplied by a component
        to it's constituent actors.
        """
        mandatory = set(definition['args']['mandatory'])
        optional = set(definition['args']['optional'])
        defined = set(declaration['args'].keys())

        # Case 1: Missing arguments
        missing = mandatory - defined
        for m in missing:
            fmt = "Missing argument: '{param}'"
            self.append_error(fmt, line=declaration['dbg_line'], param=m)

        # Case 2: Extra (unused) arguments
        unused = defined - (mandatory | optional)
        for m in unused:
            fmt = "Unused argument: '{param}'"
            self.append_error(fmt, line=declaration['dbg_line'], param=m)

        # Case 3: value for arg is IDENTIFIER rather than VALUE, and IDENTIFIER is not in constants
        for param, (kind, value) in declaration['args'].iteritems():
            # If kind is not IDENTIFIER we have an actual value => continue to next argument
            if kind != 'IDENTIFIER':
                continue
            # First check if the identifier (value) is provided by a wrapping component...
            if value in arguments:
                continue
            # ... and if it is not it have to be a constant or there was an error in the script.
            if value not in self.constants:
                fmt = "Undefined identifier: '{param}'"
                self.append_error(fmt, line=declaration['dbg_line'], param=value)


    def undeclared_actors(self, connections, declared_actors):
        """
        Scan connections for actors and compare to the set of declared actors in order
        to find actors that are referenced in the script but not declared.
        """
        # Look for undeclared actors
        src_actors = {c['src'] for c in connections if c['src'] != "."}
        dst_actors = {c['dst'] for c in connections if c['dst'] != "."}
        # Implicit src actors are defined by a constant on the inport
        implicit_src_actors = {c['src'] for c in connections if c['src'] is None}
        all_actors = src_actors | dst_actors
        undefined_actors = all_actors - (set(declared_actors) | implicit_src_actors)
        return undefined_actors

    def unknown_actors(self, actor_decls):
        """
        Find unknown actors, i.e. actors that are declared in the script,
        but whose definition is missing from the actorstore.
        """
        unknown_actors = [a for a, decl in actor_decls.iteritems() if not self.get_definition(decl['actor_type'])]
        return unknown_actors

    def check_structure(self, structure, arguments=None):
        """
        Check structure of program or component definition.
        'arguments' is a list of the parameters provided by the component to its constituent actors,
        and is only present if this method is called from 'check_component'.
        """
        connections = structure['connections']
        actor_declarations = structure['actors']
        declared_actors = actor_declarations.keys()
        arguments = arguments or []

        # Look for missing actors
        for actor in self.undeclared_actors(connections, declared_actors):
            fmt = "Undefined actor: '{actor}'"
            lines = [c['dbg_line'] for c in connections if c['src'] == actor or c['dst'] == actor]
            for line in lines:
                self.append_error(fmt, line=line, actor=actor)

        # FIXME: Add check for actors declared more than once
        # Note: Unused actors will be caught when checking connections

        # Check if actor definition exists
        unknown_actors = self.unknown_actors(actor_declarations)
        if self.verify:
            for actor in unknown_actors:
                fmt = "Unknown actor type: '{type}'"
                self.append_error(fmt, type=actor_declarations[actor]['actor_type'], line=actor_declarations[actor]['dbg_line'])

        # Check the validity of the known actors
        known_actors = set(declared_actors) - set(unknown_actors)
        for actor in known_actors:
            definition = self.get_definition(actor_declarations[actor]['actor_type'])
            self.check_actor_connections(actor, definition, connections)
            self.check_arguments(definition, actor_declarations[actor], arguments)


def check(cs_info, verify=True):
    clint = Checker(cs_info, verify=verify)
    return clint.errors, clint.warnings


if __name__ == '__main__':
    import sys
    import os
    import json

    if len(sys.argv) < 2:
        script = 'inline'
        source_text = \
"""# Test script
        component Count(len) -> seq {
            src : std.Constant(data="hup", n=len)
            src.token > .seq
        }

        src: Count(len=5)
        snk : io.StandardOut()
        src.seq > snk.token
"""
    else:
        script = sys.argv[1]
        script = os.path.expanduser(script)
        try:
            with open(script, 'r') as source:
                source_text = source.read()
        except:
            print "Error: Could not read file: '%s'" % script
            sys.exit(1)

    result, errors, warnings = calvin_parser(source_text, script)
    if errors:
        print "{reason} {script} [{line}:{col}]".format(script=script, **errors[0])
    else:
        errors, warnings = check(result)
        print "errors:", [x['reason'] for x in errors]
        print "warnings:", [x['reason'] for x in warnings]
