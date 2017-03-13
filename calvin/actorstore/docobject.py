import json
import inspect
import pystache



class DocObject(object):
    """docstring for DocObject"""

    use_links = False
    use_md = False

    COMPACT_FMT = """{{fqualified_name}} : {{fshort_desc}}"""
    DETAILED_FMT_MD = COMPACT_FMT
    DETAILED_FMT_PLAIN = COMPACT_FMT

    def __init__(self, namespace, name=None, docs=None):
        super(DocObject, self).__init__()
        self.ns = namespace
        self.name = name
        if type(docs) is list:
            docs = "\n".join(docs)
        self.docs = docs or "DocObject"

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
    def fns(self):
        return self._escape_text(self.ns)

    @property
    def fname(self):
        return self._escape_text(self.name or self.ns)

    @property
    def fqualified_name(self):
        return self._escape_text(self.qualified_name)

    @property
    def fshort_desc(self):
        short_desc, _, _ = self.docs.partition('\n')
        return self._escape_text(short_desc)

    @property
    def fdesc(self):
        return self._escape_text(self.docs)

    @property
    def fslug(self):
        return self.qualified_name.replace('.', '_')

    @property
    def flabel(self):
        return "DocObject"

    def _escape_text(self, txt):
        if not self.use_md:
            return txt
        for c in "\\`*_{}[]()<>#+-.!":
            txt = txt.replace(c, "\\"+c)
        return txt

    #
    # "API" to produce output from a DocObject
    #
    def compact(self):
        DocObject.use_md = False
        DocObject.use_links = False
        fmt = inspect.cleandoc(self.COMPACT_FMT)+ "\n"
        return pystache.render(fmt, self)

    def detailed(self):
        DocObject.use_md = False
        DocObject.use_links = False
        fmt = inspect.cleandoc(self.DETAILED_FMT_PLAIN)+ "\n"
        return pystache.render(fmt, self)

    def markdown(self):
        DocObject.use_md = True
        DocObject.use_links = False
        fmt = inspect.cleandoc(self.DETAILED_FMT_MD)+ "\n"
        return pystache.render(fmt, self)

    def markdown_links(self):
        DocObject.use_md = True
        DocObject.use_links = True
        fmt = inspect.cleandoc(self.DETAILED_FMT_MD)+ "\n"
        return pystache.render(fmt, self)

    def metadata(self):
        return {'is_known': False}

    def raw(self):
        raw = self.metadata()
        raw['short_desc'] = self.fshort_desc
        raw['long_desc'] = self.fdesc
        return raw

    #
    #
    #

    # FIXME: Get rid of
    def json(self):
        return self.__repr__()

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

    COMPACT_FMT = "({{flabel}}) {{fqualified_name}} : {{fshort_desc}}"
    DETAILED_FMT_MD = COMPACT_FMT
    DETAILED_FMT_PLAIN = COMPACT_FMT

    def __init__(self, namespace, name, short_desc):
        docs = short_desc or "Unknown error"
        super(ErrorDoc, self).__init__(namespace, name, docs)

    @property
    def flabel(self):
        return "Error"

    def search(self, search_list):
        _log.debug("Actor module {}/ is missing file __init__.py".format(self.ns))
        return self

class ModuleDoc(DocObject):
    """docstring for ModuleDoc"""

    COMPACT_FMT = """
    {{fqualified_name}}
    {{fshort_desc}}

    {{#fmodules_compact}}
    Modules: {{fmodules_compact}}
    {{/fmodules_compact}}
    {{#factors_compact}}
    Actors: {{factors_compact}}
    {{/factors_compact}}
    """

    DETAILED_FMT_PLAIN = """
    ============================================================
    {{flabel}}: {{fqualified_name}}
    ============================================================
    {{fdesc}}

    {{#has_modules}}
    Modules:
    {{/has_modules}}
    {{#modules}}
      {{fname}} : {{fshort_desc}}
    {{/modules}}

    {{#has_actors}}
    Actors:
    {{/has_actors}}
    {{#actors}}
      {{fname}} : {{fshort_desc}}
    {{/actors}}
    """

    DETAILED_FMT_MD = """
    ## Module: {{fqualified_name}} {{#use_links}}<a name="{{fslug}}"></a>{{/use_links}}

    {{fdesc}}

    {{#has_modules}}
    ### Modules:
    {{/has_modules}}

    {{#modules}}
    {{#use_links}}[{{fname}}](#{{fslug}})  {{/use_links}}
    {{^use_links}}**{{fname}}**  {{/use_links}}
    {{fshort_desc}}

    {{/modules}}

    {{#has_actors}}
    ### Actors:
    {{/has_actors}}

    {{#actors}}
    {{#use_links}}[{{fname}}](#{{fslug}})  {{/use_links}}
    {{^use_links}}**{{fname}}**  {{/use_links}}
    {{fshort_desc}}

    {{/actors}}
    {{#use_links}}

    [\[Top\]](#Calvin)
    {{/use_links}}
    """


    def __init__(self, namespace, modules, actors, doclines):
        super(ModuleDoc, self).__init__(namespace, None, doclines)
        self.modules = modules
        self.actors = actors

    @property
    def has_actors(self):
        return bool(self.actors)

    @property
    def has_modules(self):
        return bool(self.modules)

    @property
    def fmodules_compact(self):
        return ", ".join([x.fname for x in self.modules if type(x) is not ErrorDoc])

    @property
    def factors_compact(self):
        return ", ".join([x.fname for x in self.actors if type(x) is not ErrorDoc])

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

    def raw(self):
        raw = super(ModuleDoc, self).raw()
        raw['modules'] = [x.ns for x in self.modules]
        raw['actors'] = [x.name for x in self.actors]
        return raw


class ActorDoc(DocObject):
    """docstring for ActorDoc"""

    COMPACT_FMT = """
    {{fqualified_name}}({{fargs}})
    {{fshort_desc}}

    {{#finports_compact}}Inports:  {{finports_compact}}{{/finports_compact}}
    {{#foutports_compact}}Outports: {{foutports_compact}}{{/foutports_compact}}
    {{#is_component}}Requires: {{frequires}}{{/is_component}}
    """

    DETAILED_FMT_PLAIN = """
    ============================================================
    {{flabel}}: {{fqualified_name}}({{fargs}})
    ============================================================
    {{fdesc}}

    {{#has_inputs}}Inports:{{/has_inputs}}
    {{#inputs}}
      {{port}} : {{docs}} {{#props}}({{props}}){{/props}}
    {{/inputs}}

    {{#has_outputs}}Outports::{{/has_outputs}}
    {{#outputs}}
      {{port}} : {{docs}} {{#props}}({{props}}){{/props}}
    {{/outputs}}
    {{#is_component}}

    Requires: {{frequires}}
    {{/is_component}}
    """

    DETAILED_FMT_MD = """
    ## {{flabel}}: {{fqualified_name}}({{fargs}}) {{#use_links}}<a name="{{fslug}}"></a>{{/use_links}}

    {{fdesc}}

    {{#has_inputs}}### Inports:{{/has_inputs}}

    {{#inputs}}
    **{{port}}** : {{docs}} {{#props}}(_{{props}}_){{/props}}
    {{/inputs}}

    {{#has_outputs}}### Outports:{{/has_outputs}}

    {{#outputs}}
    **{{port}}** : {{docs}} {{#props}}(_{{props}}_){{/props}}
    {{/outputs}}
    {{#is_component}}

    ### Requires:

    {{frequires}}
    {{/is_component}}
    {{#use_links}}

    [\[Top\]](#Calvin) [\[Module: {{fns}}\]](#{{fns}})
    {{/use_links}}
    """


    def __init__(self, namespace, name, args, inputs, outputs, doclines):
        super(ActorDoc, self).__init__(namespace, name, doclines)
        self.args = args
        self.inputs = [{'port':pn, 'docs':self._escape_text(pd), 'props':self._escape_text(pp)} for pn, pd, pp in inputs]
        self.outputs = [{'port':pn, 'docs':self._escape_text(pd), 'props':self._escape_text(pp)} for pn, pd, pp in outputs]
        self.is_component = False

    @property
    def has_inputs(self):
        return bool(self.inputs)

    @property
    def has_outputs(self):
        return bool(self.outputs)

    @property
    def flabel(self):
        return "Actor"

    @property
    def fargs(self):
        def _escape_string_arg(arg):
            if type(arg) != str:
                return arg
            if self.use_md:
                return '"{}"'.format(arg.encode('string_escape'))
            return '"{}"'.format(arg)
        return self._escape_text(", ".join(self.args['mandatory'] + ["{}={}".format(k, _escape_string_arg(v)) for k,v in self.args['optional'].iteritems()]))

    @property
    def finports_compact(self):
        return ", ".join([p['port'] for p in self.inputs])

    @property
    def foutports_compact(self):
        return ", ".join([p['port'] for p in self.outputs])

    def metadata(self):
        metadata = {
            'ns': self.ns,
            'name': self.name,
            'type': 'actor',
            'args': self.args,
            'inputs': [p['port'] for p in self.inputs],
            'input_properties': {p['port']:p['props'] for p in self.inputs},
            'outputs': [p['port'] for p in self.outputs],
            'output_properties': {p['port']:p['props'] for p in self.outputs},
            'is_known': True
        }
        return metadata


class ComponentDoc(ActorDoc):
    #
    # Augment a couple of methods in the superclass
    #
    def __init__(self, namespace, name, args, inputs, outputs, doclines, requires, definition):
        super(ComponentDoc, self).__init__(namespace, name, args, inputs, outputs, doclines)
        self.requires = requires # "FIXME"
        self.definition = definition # actor.children[0]
        self.is_component = True

    @property
    def flabel(self):
        return "Component"

    @property
    def frequires(self):
        return self._escape_text(", ".join(self.requires))

    def metadata(self):
        metadata = super(ComponentDoc, self).metadata()
        metadata['type'] = 'component'
        metadata['definition'] = self.definition
        metadata['requires'] = self.requires
        return metadata





if __name__ == '__main__':

    def test_all_formatters(d):
        print "\n%s\n=======================" % (d.__class__.__name__,)
        for formatter in [d.compact, d.detailed, d.markdown, d.markdown_links]:
            print "%s:\n-----------------------" % (formatter.__name__,)
            print formatter()

    d = DocObject('yadda')
    test_all_formatters(d)

    d = ErrorDoc('foo', 'Bar', 'short error description')
    test_all_formatters(d)
    #
    d = ModuleDoc('root', [ModuleDoc('std', [], [], 'std short description'), ModuleDoc('io', [], [], 'io short description')], [], 'short description')
    test_all_formatters(d)

    doclines = """actor yaddda, yadda

        Even more
    """
    a = ActorDoc('std', 'Comp', {'mandatory':['x', 'y'], 'optional':{'z':1}}, [('in1', 'anything', 'property'), ('in2', 'something', 'property')], [('out', 'token', 'property')], doclines)
    test_all_formatters(a)

    c = ComponentDoc('std', 'Args', {'mandatory':['x', 'y'], 'optional':{'z':1}}, [('in1', 'anything', 'property'), ('in2', 'something', 'property')], [('out', 'token', 'property')], doclines, ['alpha', 'beta'], {})
    test_all_formatters(c)

    d = ModuleDoc('std', [], [a, c], 'short description')
    test_all_formatters(d)





