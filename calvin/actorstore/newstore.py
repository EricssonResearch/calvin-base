import os
import sys
import json
import jsonschema
import yaml
import inspect # import cleandoc, getargs
# from __future__ import print_function

# Stand-alone actorstore
# REST API
# Supplies: source code (raw), properties (JSON)
# Requires: Actors in filesystem, git (TODO), db (TODO), ...
# Assumptions: Properties (dosctring) in YAML format
#              JSON-schema for properties JSON
# FIXME: Components
#        Chache and check timestamp


class Pathinfo(object):
    invalid = 0
    directory = 1
    actor = 2
    component = 3

class Store(object):
    
    actor_properties_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$ref": "#/definitions/ActorProperties",
        "definitions": {
            "ActorProperties": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "documentation": {
                        "type": "array",
                        "items": { "type": "string" }
                    },
                    "ports": {
                        "type": "array",
                        "items": { "$ref": "#/definitions/Port" }
                    },
                    "requires": {
                        "type": "array",
                        "items": { "type": "string" }                        
                    }
                },
                "required": ["documentation", "ports"],
                "title": "ActorProperties"
            },
            "Port": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": { "type": "string" },
                    "direction": { "enum": ["in", "out"] },
                    "help": { "type": "string" },
                    "properties": { "$ref": "#/definitions/Properties" },
                },
                "required": ["name", "direction"],
                "title": "Port"
            },
            "Properties": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "routing": { "type": "string" }
                },
                "title": "Properties"
            }
        }
    }

    module_properties_schema = {
        "type": "array",
        "items": { "type": "string" },
    }
    
    """docstring for Store"""
    
    def __init__(self, basepath=None):
        super(Store, self).__init__()
        basepath = basepath or os.path.dirname(os.path.realpath(__file__))
        self.basepath = os.path.join(basepath, 'systemactors')
    
    def normalize(self, actor_type):
        path = actor_type.replace('.', '/')
        if os.path.isabs(path):
            return (path, Pathinfo.invalid)
        path = os.path.join(self.basepath, path)
        return self.pathinfo(path)
        
    def pathinfo(self, path):
        if os.path.isdir(path):
            tmp_path = os.path.join(path, '__init__.py')
            if os.path.isfile(tmp_path): 
                return (path, Pathinfo.directory)
        # Check for .py and .comp in that order
        tmp_path = path + '.py'
        if os.path.isfile(tmp_path):
            return (tmp_path, Pathinfo.actor)
        tmp_path = path + '.comp'
        if os.path.isfile(tmp_path):
            return (tmp_path, Pathinfo.component)
        return (path, Pathinfo.invalid)    
    
    def read_file(self, path):
        with open(path) as f:
            src = f.read()
        return src
    
    def locate_codeobject(self, codeobject, actor_class):
        for x in codeobject.co_consts:
            if type(x) is type(codeobject) and x.co_name == actor_class:
                return x
        return None
    
    def get_docs(self, codeobject):
        return codeobject.co_consts[0]
    
    def get_startofcode(self, codeobject):
        return codeobject.co_firstlineno - 1        
                
    def parse_actor_docs(self, docs):
        props = yaml.load(docs)
        jsonschema.validate(props, self.actor_properties_schema)
        props = self.transform_properties(props)
        return props
        # json_props = json.dumps(props)
        # return json_props

    def parse_module_docs(self, docs):
        props = yaml.load(docs)
        jsonschema.validate(props, self.module_properties_schema)
        return props
        # json_props = json.dumps(props)
        # return json_props
    
    def transform_properties(self, props):
        return props
        
    def get_args(self, co):
        # FIXME: Assumes all arguments are mandatory
        argspec = inspect.getargs(co)
        args = [{'mandatory':True, 'name':name} for name in argspec.args[1:]]
        return args
        
    def get_actor(self, path):
        basepath, filename = os.path.split(path)
        _, ns = os.path.split(basepath)
        actor_class, _ = os.path.splitext(filename)
        print  path, actor_class
        src = self.read_file(path)
        co = compile(src, '<string>', 'exec')
        i = self.get_startofcode(co)
        # trim source to get rid of encoding markers that chokes compile
        # also remove initial comment
        # remove import statements, they will be taken care of elsewhere.
        # (besides, only calvin.actor.actor is allowed anyway)
        lines = src.split("\n")
        while lines[i].startswith("from") or lines[i].startswith("import") or lines[i].strip() == "":
            i += 1
        src = "\n".join(lines[i:])    
        aco = self.locate_codeobject(co, actor_class)
        docs = self.get_docs(aco)
        props = self.parse_actor_docs(docs)
        mco = self.locate_codeobject(aco, 'init')
        args = self.get_args(mco)
        props['args'] = args
        # ns
        props['ns'] = ns
        # name
        props['name'] = actor_class
        # type
        props['type'] = 'actor'
        # required
        props.setdefault('requires', [])
        # is_known 
        props['is_known'] = True
        
        return (src, props)
        
    def get_component(self, path):
        raise Exception("FIXME")
        src = self.read_file(path)
        return (src, {})
        
    def get_directory(self, path):
        tmp_path = os.path.join(path, '__init__.py')
        src = self.read_file(tmp_path)
        co = compile(src, '<string>', 'exec')
        docs = self.get_docs(co) 
        props = self.parse_module_docs(docs)
        return (None, props)
        
    def error_handler(self, path):
        return (path, "Error message")

    def get(self, actor_type):
        path, info = self.normalize(actor_type)
        handler = {
            Pathinfo.directory : self.get_directory,
            Pathinfo.actor : self.get_actor,
            Pathinfo.component : self.get_component,
        }.get(info, self.error_handler)
        src, properties = handler(path)
        return (info, src, properties)
        
        
    # metadata_example = {
    #     'type': 'actor',
    #     'ns': 'flow',
    #     'name': 'Init',
    #     'args': {
    #         'mandatory': ['data'],
    #         'optional': {},
    #     },
    #     'inputs': ['in'],
    #     'input_properties': {
    #         'in': {}
    #     },
    #     'outputs': ['out'],
    #     'output_properties': {
    #         'out': {}
    #     },
    #     'requires': ['sys.schedule'],
    #     'is_known': True,
    # }
    #
    # new_metadata_example = {
    #     'type': 'actor',
    #     'ns': 'flow',
    #     'name': 'Init',
    #     'args': [
    #         {
    #             'name':'data',
    #             'mandatory': True
    #         },
    #         {
    #             'name':'hidden',
    #             'mandatory': False,
    #             'default': None
    #         },
    #     ]
    #     'ports': [
    #         {
    #             'name':'in',
    #             'help': 'help text',
    #             'properties': {},
    #             'direction': 'in'
    #         },
    #         {
    #             'name':'out',
    #             'help': 'help text',
    #             'properties': {},
    #             'direction': 'out'
    #         },
    #     ],
    #     'requires': ['sys.schedule'],
    #     'is_known': True,
    #     'documentation': ['', '',] 
    # }
            
         
if __name__ == '__main__':
    s = Store()
    # print(s.normalize('/Users/eperspe/Source/calvin-base/calvin/std'))
    # print(s.normalize('std'))
    # print(s.normalize('std/'))
    # print(s.normalize('std/Init'))
    # print(s.normalize('std/Identity'))
    # print(s.normalize(''))
    #
    # print(s.get('std'))
    # print(s.get('std.Init'))
    # print(s.get('std.Identity'))
    # print(s.get(''))
    
    print('')
    print s.get('std')[2]
    print
    print s.get('std.Identity')[2]
    print s.get('std.CountTimer')[2]
    print s.get('io.Print')[2]
    
    
    
    
