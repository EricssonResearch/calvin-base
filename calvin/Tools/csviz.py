#!/usr/bin/env python
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


import sys
import textwrap
import argparse
from calvin.actorstore.store import DocumentationStore
from calvin.Tools import cscompiler
from calvin.csparser.parser import calvin_parser


def _refname(name):
    return "" if name == '.' else name.replace(':', '_')

class Viz(object):
    """docstring for Viz"""
    def __init__(self):
        super(Viz, self).__init__()

    def __str__(self):
        raise Exception("Direct subclass MUST implement __str__")

    def render(self):
        return str(self)

class LinkViz(Viz):
    """docstring for LinkViz"""
    def __init__(self, link):
        super(LinkViz, self).__init__()
        link['src'] = _refname(link['src'])
        link['dst'] = _refname(link['dst'])
        self.link = link

    def __str__(self):
        if not self.link['src']:
            return '{src_port}_in:e -> {dst}:{dst_port}_in:w [arrowhead="none"];'.format(**self.link)
        elif not self.link['dst']:
            return '{src}:{src_port}_out:e -> {dst_port}_out:w [arrowhead="none"];'.format(**self.link)
        else:
            return '{src}:{src_port}_out:e -> {dst}:{dst_port}_in:w;'.format(**self.link)

class ActorViz(Viz):
    """docstring for ActorViz"""

    docstore = DocumentationStore()

    def __init__(self, name, actor_type, args, **dummy):
        super(ActorViz, self).__init__()
        self.type_color = 'lightblue'
        self.name = name
        self.args = args
        self.actor_type = actor_type
        doc = self.docstore.help_raw(actor_type)
        self.set_ports(doc)

    def set_ports(self, doc):
        inports = [p for p,_ in doc['inputs']]
        outports = [p for p,_ in doc['outputs']]
        inlen = len(inports)
        outlen = len(outports)
        self.portrows = max(inlen, outlen)
        self.inports = inports + ['']*(self.portrows - inlen)
        self.outports = outports + ['']*(self.portrows - outlen)


    def __str__(self):
        lines = []
        lines.append('{0} [label=<'.format(_refname(self.name)))
        lines.append('<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">')
        # Name
        lines.append('<TR><TD bgcolor="{1}" COLSPAN="3">{0}</TD></TR>'.format(self.name, self.type_color))
        # Class
        lines.append('<TR><TD COLSPAN="3">{0}</TD></TR>'.format(self.actor_type))
        is_first=True
        for inport, outport in zip(self.inports, self.outports):
            inref = ' bgcolor="lightgrey" PORT="{0}_in"'.format(inport) if inport else ''
            outref = ' bgcolor="lightgrey" PORT="{0}_out"'.format(outport) if outport else ''
            if is_first:
                is_first = False
                middle = '<TD ROWSPAN="{0}">    </TD>'.format(self.portrows)
            else:
                middle = ''
            lines.append('<TR><TD{0} align="left">{1}</TD>{4}<TD{2} align="right">{3}</TD></TR>'.format(inref, inport, outref, outport, middle))
        lines.append('</TABLE>>];')

        return '\n'.join(lines)


class PadViz(Viz):
    """docstring for PadViz"""
    def __init__(self, padname, direction):
        super(PadViz, self).__init__()
        self.padname = padname
        self.direction = direction

    def __str__(self):
        return '{0}_{1} [shape="cds" style="filled" fillcolor="lightgrey" label="{0}"];'.format(self.padname, self.direction)


class CompViz(ActorViz):
    """docstring for CompViz"""
    def __init__(self, name, comp_type, comp_def):
        self.type_color = 'lightyellow'
        self.name = name
        self.args = comp_def['arg_identifiers']
        self.actor_type = comp_type
        doc = self.docstore.component_docs('.'+comp_type, comp_def)
        self.set_ports(doc)


class AppViz(Viz):
    """docstring for AppViz"""
    def __init__(self, deployable):
        super(AppViz, self).__init__()
        self.actors = [ActorViz(name, **args) for name, args in deployable['actors'].iteritems()]
        self.links = []
        for src, dstlist in deployable['connections'].iteritems():
            _src, _src_port = src.split('.')
            for dst in dstlist:
                _dst, _dst_port = dst.split('.')
                link = {'src':_src, 'src_port':_src_port, 'dst':_dst, 'dst_port':_dst_port}
                self.links.append(LinkViz(link))
        self.components = []

    def __str__(self):
        viz = [str(v) for v in self.actors + self.links + self.components]
        return '\n'.join(viz)

    def render(self):
        return 'digraph structs {{ node [shape=plaintext]; rankdir=LR;\n{0}\n}}'.format(str(self))


class ScriptViz(AppViz):
    """docstring for ScriptViz"""
    def __init__(self, ir):
        comp_defs = ir['components'] if 'components' in ir else {}
        self.actors = [ActorViz(name, **args) for name, args in ir['structure']['actors'].iteritems() if '.' in args['actor_type']]
        self.links = [LinkViz(link) for link in ir['structure']['connections'] if link['src'] and link['dst']]
        self.components = [CompViz(name, args['actor_type'], comp_defs[args['actor_type']]) for name, args in ir['structure']['actors'].iteritems() if args['actor_type'] in comp_defs]


class CompInternalsViz(ScriptViz):
    """docstring for CompInternalsViz"""
    def __init__(self, comp_def):
        super(CompInternalsViz, self).__init__(comp_def)
        self.name = comp_def['name']
        self.inpads = [PadViz(p, 'in') for p in comp_def['inports']]
        self.outpads = [PadViz(p, 'out') for p in comp_def['outports']]
        self.padlinks = [LinkViz(link) for link in comp_def['structure']['connections'] if link['src'] == '.' or link['dst'] == '.']

    def render(self):
        viz = ['digraph comp { node [shape=plaintext]; rankdir=LR;']
        # Declare "pads"
        viz += ['subgraph inpads { rank="source";']
        viz += [str(v) for v in self.inpads]
        viz.append('}')
        viz += ['subgraph outpads { rank="sink";']
        viz += [str(v) for v in self.outpads]
        viz.append('}')
        viz += ['subgraph cluster_comp {{ label="{0}";'.format(self.name)]
        # Component structure (same as any script)
        viz.append(str(self))
        viz.append('}')
        # Links to component ports
        viz += [str(v) for v in self.padlinks]
        viz.append('}')
        return '\n'.join(viz)


def visualize_deployment(filename):
    deployable, errors, warnings = cscompiler.compile_file(filename)
    return AppViz(deployable).render()


def visualize_script(filename):
    with open(filename, 'r') as f:
        source_text = f.read()
        ir, errors, warnings = calvin_parser(source_text, 'filename')
        return ScriptViz(ir).render()

def visualize_component_internals(filename, component):
    with open(filename, 'r') as f:
        source_text = f.read()
        ir, errors, warnings = calvin_parser(source_text, 'filename')
        if component in ir['components']:
            comp_def = ir['components'][component]
            return CompInternalsViz(comp_def).render()

def main():
    long_description = """
    Generate a DOT output for use with GraphViz to generate a vizualization
    of the Calvin application graph.

    Typical usage would be something like (Linux):
    csviz --script foo.calvin | dot -Tpdf | pdfviewer -
    or (Mac OS X):
    csviz --script foo.calvin | dot -Tpdf | open -f -a Preview
    """

    argparser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(long_description)
    )
    argparser.add_argument('--script', type=str, required=True,
                           help='script file to visualize.')
    group = argparser.add_mutually_exclusive_group()
    group.add_argument('--deployment', action='store_true',
                       help='expand all components into constituent parts.')
    group.add_argument('--component', type=str,
                       help='show internals of a component in script.')

    args = argparser.parse_args()

    exit_val = 0
    try:
        if args.deployment:
            res = visualize_deployment(args.script)
        elif args.component:
            res = visualize_component_internals(args.script, args.component)
        else:
            res = visualize_script(args.script)
        print(res)
    except Exception as e:
        print e
        exit_val = 1

if __name__ == '__main__':
    sys.exit(main())
