# -*- coding: utf-8 -*-

# Copyright (c) 2015-2019 Ericsson AB
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



import inspect
import json
from collections import namedtuple

import pystache

from calvin.common.calvinlogger import get_logger

_log = get_logger(__name__)

class DocObject(object):
    """docstring for DocObject"""

    use_links = False

    COMPACT_FMT = "{{{qualified_name}}} : {{{short_desc}}}"
    DETAILED_FMT_MD = "{{{e_qualified_name}}} : {{{e_short_desc}}}"
    DETAILED_FMT_PLAIN = COMPACT_FMT

    def __init__(self, metadata):
        super(DocObject, self).__init__()
        self.metadata = metadata
    #
    # Allow templates to use e_<attr> to access an escaped version of attribute <attr>
    #
    def __getattr__(self, synthetic_attr):
        if not synthetic_attr.startswith('e_'):
            raise AttributeError("No such attribute: %s" % synthetic_attr)
        _, attr = synthetic_attr.split('_', 1)
        if not hasattr(self, attr):
            raise AttributeError("No such attribute: %s" % attr)
        x = getattr(self, attr)
        # N.B. Kind of escape should depend on desired output
        return self._escape_text(x)

    def _escape_text(self, txt):

        def _escape_line(line):
            if line.startswith('    '):
                return line
            for c in "\\<>*_{}[]()#+-.!":
                line = line.replace(c, "\\"+c)
            return line

        lines_in = txt.split('\n')
        lines_out = [_escape_line(line) for line in lines_in]
        return "\n".join(lines_out)

    @property
    def label(self):
        return self.metadata['type'].capitalize()
    
    @property
    def has_actors(self):
        return False

    @property
    def has_modules(self):
        return False

    @property
    def ns(self):
        self.metadata.get('ns', 'NO_NAMESPACE')
        
    @property
    def name(self):
        self.metadata['name']
        
    @property
    def qualified_name(self):
        if 'ns' in self.metadata:
            return "{}.{}".format(self.metadata['ns'], self.metadata['name'])
        return self.metadata['name']

    @property
    def own_name(self):
        return self.metadata['name'] or self.metadata['ns']

    @property
    def short_desc(self):
        return self.metadata['documentation'][0]

    @property
    def docs(self):
        return "\n".join(self.metadata['documentation'])
        
    @property
    def slug(self):
        return self.qualified_name.replace('.', '_')

    #
    # "API" to produce output from a DocObject
    #
    def compact(self):
        fmt = inspect.cleandoc(self.COMPACT_FMT)
        return pystache.render(fmt, self)

    def detailed(self):
        fmt = inspect.cleandoc(self.DETAILED_FMT_PLAIN)
        return pystache.render(fmt, self)

    def markdown(self):
        DocObject.use_links = False
        fmt = inspect.cleandoc(self.DETAILED_FMT_MD)
        return pystache.render(fmt, self)

    def markdown_links(self):
        DocObject.use_links = True
        fmt = inspect.cleandoc(self.DETAILED_FMT_MD)
        return pystache.render(fmt, self)



class ErrorDoc(DocObject):
    """docstring for ErrDoc"""

    COMPACT_FMT = "({{{label}}}) {{{qualified_name}}} : {{{short_desc}}}"
    DETAILED_FMT_MD = "({{{label}}}) {{{e_qualified_name}}} : {{{e_short_desc}}}"
    DETAILED_FMT_PLAIN = COMPACT_FMT

    def __init__(self, namespace, name, short_desc):
        docs = short_desc or "Unknown error"
        super(ErrorDoc, self).__init__(namespace, name, docs)
        self.label = "Error"

    def search(self, search_list):
        _log.debug("Actor module {}/ is missing file __init__.py".format(self.ns))
        return self

class ModuleDoc(DocObject):
    """docstring for ModuleDoc"""

    COMPACT_FMT = """
    {{{label}}}: {{{qualified_name}}}
    {{{short_desc}}}

    {{#items_compact}}
    Items: {{{items_compact}}}
    {{/items_compact}}
    """

    DETAILED_FMT_PLAIN = """
    ============================================================
    {{{label}}}: {{{qualified_name}}}
    ============================================================
    {{{docs}}}

    Items:
    {{#items}}
      {{{own_name}}} : {{{short_desc}}}
    {{/items}}

    """

    DETAILED_FMT_MD = """
    ## {{{label}}}: {{{e_qualified_name}}} {{#use_links}}<a name="{{{slug}}}"></a>{{/use_links}}

    {{{e_docs}}}

    ### Items:

    {{#items}}
    {{#use_links}}[**{{{e_own_name}}}**](#{{{slug}}}){{/use_links}}{{^use_links}}**{{{e_own_name}}}**{{/use_links}} : {{{e_short_desc}}}

    {{/items}}

    {{#use_links}}[\[Top\]](#Calvin){{/use_links}}
    ***
    """

    @property
    def label(self):
        return "Module"

    @property
    def has_items(self):
        return bool(self.metadata.get['items'])

    @property
    def items_compact(self):
        return ", ".join([a['name'] for a in self.metadata['items']])
        
    @property
    def items(self):
        return [DocObject(a) for a in self.metadata['items']]
    


class ActorDoc(DocObject):
    """docstring for ActorDoc"""

    COMPACT_FMT = """
    {{{qualified_name}}}({{{fargs}}})
    {{{short_desc}}}

    {{#has_inports}}Inports: {{{inports_compact}}}{{/has_inports}}
    {{#has_outports}}Outports: {{{outports_compact}}}{{/has_outports}}
    {{#has_requirements}}Requires: {{{requires_compact}}}{{/has_requirements}}
    """

    DETAILED_FMT_PLAIN = """
    ============================================================
    {{{label}}}: {{{qualified_name}}}({{{fargs}}})
    ============================================================
    {{{docs}}}
    {{#has_inports}}

    Inports:
    {{/has_inports}}
    {{#inports}}
      {{{name}}} {{#props}}({{{props}}}){{/props}} : {{{docs}}} 
    {{/inports}}
    {{#has_outports}}

    Outports:
    {{/has_outports}}
    {{#outports}}
      {{{name}}} {{#props}}({{{props}}}){{/props}} : {{{docs}}} 
    {{/outports}}
    {{#has_requirements}}

    Requires:
      {{{requires_compact}}}
    {{/has_requirements}}
    """

    DETAILED_FMT_MD = """
    ## {{{label}}}: {{{e_qualified_name}}}({{{e_fargs}}}) {{#use_links}}<a name="{{{slug}}}"></a>{{/use_links}}

    {{{e_docs}}}

    {{#has_inports}}
    ### Inports:

    {{/has_inports}}
    {{#inports}}
    **{{{e_name}}}** : {{{e_docs}}} {{#props}}_Properties({{{e_props}}})_{{/props}}

    {{/inports}}
    {{#has_outports}}
    ### Outports:

    {{/has_outports}}
    {{#outports}}
    **{{{e_name}}}** : {{{e_docs}}} {{#props}}_Properties({{{e_props}}})_{{/props}}

    {{/outports}}
    {{#has_requirements}}
    ### Requires:

    {{{e_requires_compact}}}

    {{/has_requirements}}
    {{#use_links}}[\[Top\]](#Calvin) [\[Module: {{{e_ns}}}\]](#{{{ns}}}){{/use_links}}
    ***
    """

    PortDoc = namedtuple('PortDoc', ['name', 'docs', 'props'])

    def __init__(self, metadata):
        super(ActorDoc, self).__init__(metadata)
        self.metadata = metadata
    
    @property
    def has_inports(self):
        return any((p['direction'] == 'in' for p  in self.metadata['ports']))

    @property
    def has_outports(self):
        return any((p['direction'] == 'out' for p  in self.metadata['ports']))

    @property
    def has_requirements(self):
        return bool(self.metadata['requires'])

    @property
    def fargs(self):
        return ", ".join([a['name'] for a in self.metadata['args']])
    
    @property
    def inports_compact(self):
        return ", ".join(p['name'] for p  in self.metadata['ports'] if p['direction'] == 'in' )

    @property
    def outports_compact(self):
        return ", ".join(p['name'] for p  in self.metadata['ports'] if p['direction'] == 'out' )
    
    @property
    def inports(self):
        return [self.PortDoc(p['name'], p['help'], p.get('properties', {}).get('routing')) for p  in self.metadata['ports'] if p['direction'] == 'in' ]

    @property
    def outports(self):
        return [self.PortDoc(p['name'], p['help'], p.get('properties', {}).get('routing')) for p  in self.metadata['ports'] if p['direction'] == 'out' ]
        
    @property
    def requires_compact(self):
        return ", ".join(self.metadata['requires'])


class ComponentDoc(ActorDoc):
    pass


class DocFormatter(object):
    """docstring for DocFormatter"""
    def __init__(self, outputformat='plain', compact=False, links=False):
        super(DocFormatter, self).__init__()
        self.outputformat = outputformat
        self.compact = compact
        self.links = links
        
    def format(self, metadata):
        class_ = {
            'actor': ActorDoc,
            'component': ComponentDoc,
            'module': ModuleDoc,
        }.get(metadata['type'], ErrorDoc)
        a = class_(metadata)
        if self.outputformat == 'md':
            if self.links:
                return a.markdown_links()
            else:
                return a.markdown()
        if self.compact:
            return a.compact()
        else:    
            return a.detailed()

