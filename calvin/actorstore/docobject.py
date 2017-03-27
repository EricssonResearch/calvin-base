import json
import inspect
import pystache
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class DocObject(object):
    """docstring for DocObject"""

    use_links = False

    COMPACT_FMT = "{{{qualified_name}}} : {{{short_desc}}}"
    DETAILED_FMT_MD = "{{{e_qualified_name}}} : {{{e_short_desc}}}"
    DETAILED_FMT_PLAIN = COMPACT_FMT

    def __init__(self, namespace, name=None, docs=None):
        super(DocObject, self).__init__()
        self.ns = namespace
        self.name = name
        if type(docs) is list:
            docs = "\n".join(docs)
        self.label = "DocObject"
        self.docs = docs.rstrip() or ""

    #
    # Allow templates to use e_attr to access an escaped version of attribute attr
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
    def has_actors(self):
        return False

    @property
    def has_modules(self):
        return False

    @property
    def qualified_name(self):
        if self.name:
            return "{}.{}".format(self.ns, self.name)
        return self.ns

    @property
    def own_name(self):
        return self.name or self.ns

    @property
    def short_desc(self):
        short_desc, _, _ = self.docs.partition('\n')
        return short_desc

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
    {{{qualified_name}}}
    {{{short_desc}}}

    {{#modules_compact}}
    Modules: {{{modules_compact}}}
    {{/modules_compact}}
    {{#actors_compact}}
    Actors: {{{actors_compact}}}
    {{/actors_compact}}
    """

    DETAILED_FMT_PLAIN = """
    ============================================================
    {{{label}}}: {{{qualified_name}}}
    ============================================================
    {{{docs}}}
    {{#has_modules}}

    Modules:
    {{/has_modules}}
    {{#modules}}
      {{{own_name}}} : {{{short_desc}}}
    {{/modules}}
    {{#has_actors}}

    Actors:
    {{/has_actors}}
    {{#actors}}
      {{{own_name}}} : {{{short_desc}}}
    {{/actors}}
    """

    DETAILED_FMT_MD = """
    ## {{{label}}}: {{{e_qualified_name}}} {{#use_links}}<a name="{{{slug}}}"></a>{{/use_links}}

    {{{e_docs}}}

    {{#has_modules}}
    ### Modules:

    {{/has_modules}}
    {{#modules}}
    {{#use_links}}[**{{{e_own_name}}}**](#{{{slug}}}){{/use_links}}{{^use_links}}**{{{e_own_name}}}**{{/use_links}} : {{{e_short_desc}}}

    {{/modules}}
    {{#has_actors}}
    ### Actors:

    {{/has_actors}}
    {{#actors}}
    {{#use_links}}[**{{{e_own_name}}}**](#{{{slug}}}){{/use_links}}{{^use_links}}**{{{e_own_name}}}**{{/use_links}} : {{{e_short_desc}}}

    {{/actors}}
    {{#use_links}}[\[Top\]](#Calvin){{/use_links}}
    ***
    """


    def __init__(self, namespace, modules, actors, doclines):
        super(ModuleDoc, self).__init__(namespace, None, doclines)
        self.modules = modules
        self.actors = actors
        self.label = "Module"

    @property
    def has_actors(self):
        return bool(self.actors)

    @property
    def has_modules(self):
        return bool(self.modules)

    @property
    def modules_compact(self):
        return ", ".join([x.own_name for x in self.modules if type(x) is not ErrorDoc])

    @property
    def actors_compact(self):
        return ", ".join([x.own_name for x in self.actors if type(x) is not ErrorDoc])

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

    def metadata(self):
        metadata = super(ModuleDoc, self).metadata()
        metadata['modules'] = [x.ns for x in self.modules]
        metadata['actors'] = [x.name for x in self.actors]
        return metadata


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
      {{{name}}} : {{{docs}}} {{#props}}Properties({{{props}}}){{/props}}
    {{/inports}}
    {{#has_outports}}

    Outports:
    {{/has_outports}}
    {{#outports}}
      {{{name}}} : {{{docs}}} {{#props}}Properties({{{props}}}){{/props}}
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


    def __init__(self, namespace, name, args, inputs, outputs, doclines, requires):
        super(ActorDoc, self).__init__(namespace, name, doclines)
        self.args = args
        self.inports = [PortDoc(namespace='in', name=pn, docs=pd, properties=pp) for pn, pd, pp in inputs]
        self.outports = [PortDoc(namespace='out', name=pn, docs=pd, properties=pp) for pn, pd, pp in outputs]
        self.input_properties = {pn:pp for pn, _, pp in inputs}
        self.output_properties = {pn:pp for pn, _, pp in outputs}
        self.inputs = [pn for pn, _, _ in inputs]
        self.outputs = [pn for pn, _, _ in outputs]
        self.requires = sorted(requires)
        self.label = "Actor"

    @property
    def has_inports(self):
        return bool(self.inports)

    @property
    def has_outports(self):
        return bool(self.outports)

    @property
    def has_requirements(self):
        return bool(self.requires)

    @property
    def fargs(self):
        def _escape_string_arg(arg):
            if type(arg) == str or type(arg) == unicode:
                # Handle \n, \r etc
                return '"{}"'.format(arg).encode('string_escape')
            if arg is True:
                return 'true'
            if arg is False:
                return 'false'
            if arg is None:
                return 'null'
            return arg
            # return '"{}"'.format(arg)
        return ", ".join(self.args['mandatory'] + ["{}={}".format(k, _escape_string_arg(v)) for k,v in self.args['optional'].iteritems()])

    @property
    def inports_compact(self):
        return ", ".join(self.inputs)

    @property
    def outports_compact(self):
        return ", ".join(self.outputs)

    @property
    def requires_compact(self):
        return ", ".join(self.requires)

    def metadata(self):
        metadata = {
            'ns': self.ns,
            'name': self.name,
            'type': 'actor',
            'args': self.args,
            'inputs': self.inputs,
            'input_properties': self.input_properties,
            'outputs': self.outputs,
            'output_properties': self.output_properties,
            'requires': self.requires,
            'is_known': True
        }
        return metadata

class PortDoc(DocObject):

    def __init__(self, namespace, name, docs, properties):
        super(PortDoc, self).__init__(namespace, name, docs)
        self.properties = properties;

    @property
    def props(self):
        def _fmt_val(v):
            if type(v) is not list:
                return str(v)
            l = ", ".join(v)
            return "[{}]".format(l) if l else ""
        res = ", ".join(["{}:{}".format(k, _fmt_val(v)) for k,v in self.properties.iteritems()])
        return res



class ComponentDoc(ActorDoc):
    #
    # Augment a couple of methods in the superclass
    #
    def __init__(self, namespace, name, args, inputs, outputs, doclines, definition):
        # FIXME: Build requirements by recursing definition
        requires = []
        super(ComponentDoc, self).__init__(namespace, name, args, inputs, outputs, doclines, requires)
        self.definition = definition
        self.label = "Component"

    def metadata(self):
        metadata = super(ComponentDoc, self).metadata()
        metadata['type'] = 'component'
        metadata['definition'] = self.definition
        return metadata


if __name__ == '__main__':

    def test_all_formatters(d):
        print "\n%s\n=======================" % (d.__class__.__name__,)
        for formatter in [d.compact, d.detailed, d.markdown, d.markdown_links]:
            print "%s:\n-----------------------" % (formatter.__name__,)
            print formatter()

    # d = DocObject('yadda')
    # test_all_formatters(d)

    # d = ErrorDoc('foo', 'Bar', 'short error description')
    # test_all_formatters(d)
    # #
    # d = ModuleDoc('root', [ModuleDoc('std', [], [], 'std short description'), ModuleDoc('io', [], [], 'io short description')], [], 'short description')
    # test_all_formatters(d)
    #
    doclines = """actor yaddda, yadda

        Even more
    """
    a = ActorDoc('std', 'Comp', {'mandatory':['x', 'y'], 'optional':{'z':1}}, [('in1', 'anything', 'property'), ('in2', 'something', 'property')], [('out', 'token', {'foo':['apa', 'banan']})], doclines)
    test_all_formatters(a)

    # c = ComponentDoc('std', 'Args', {'mandatory':['x', 'y'], 'optional':{'z':1}}, [('in1', 'anything', 'property'), ('in2', 'something', 'property')], [('out', 'token', 'property')], doclines, ['alpha', 'beta'], {})
    # test_all_formatters(c)
    #
    # d = ModuleDoc('std', [], [a, c], 'short description')
    # test_all_formatters(d)





