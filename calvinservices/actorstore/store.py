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



import os
import sys
import json
import inspect # import cleandoc, getargs

import jsonschema
import yaml

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
    root = 4

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

    def __init__(self, actorpaths=[]):
        super(Store, self).__init__()
        self.actorpaths = actorpaths
        self.actorpaths.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),
            'systemactors'))

    def normalize(self, actorpath, query):
        if not query:
            return (actorpath, Pathinfo.root)
        path = query.replace('.', '/')
        if os.path.isabs(path):
            return (path, Pathinfo.invalid)
        path = os.path.join(actorpath, path)
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
        index = 0 if len(codeobject.co_consts) == 2 else 1
        return codeobject.co_consts[index]

    def get_startofcode(self, codeobject):
        return codeobject.co_firstlineno - 1

    def parse_actor_docs(self, docs):
        props = yaml.load(docs, Loader=yaml.SafeLoader)
        jsonschema.validate(props, self.actor_properties_schema)
        return props

    def parse_module_docs(self, docs):
        props = yaml.load(docs, Loader=yaml.SafeLoader)
        jsonschema.validate(props, self.module_properties_schema)
        return props

    def get_args(self, co):
        argspec = inspect.getargs(co)
        args = [{'mandatory':True, 'name':name} for name in argspec.args[1:]]
        return args

    def get_actor(self, path):
        basepath, filename = os.path.split(path)
        _, ns = os.path.split(basepath)
        actor_class, _ = os.path.splitext(filename)
        # print  path, actor_class
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

    def _extract_module_docs(self, path):
        src = self.read_file(path)
        co = compile(src, '<string>', 'exec')
        docstr = self.get_docs(co)
        return self.parse_module_docs(docstr)


    def get_directory(self, path):
        tmp_path = os.path.join(path, '__init__.py')
        docs = self._extract_module_docs(tmp_path)
        _, ns = os.path.split(path)
        filenames = os.listdir(path)
        actors = []
        # modules = []
        actor_names = [os.path.splitext(f)[0] for f in filenames if f.endswith('.py') and not f == '__init__.py']
        actor_names.sort()
        for a in actor_names:
            props = self.get_metadata("{}.{}".format(ns, a))
            actors.append({'name':props['name'], 'documentation':props['documentation']})

        props = {
            'type': 'module',
            'name': ns,
            'documentation': docs,
            'items': actors,
        }
        return (None, props)

    def get_root(self, path):
        tmp_path = os.path.join(path, '__init__.py')
        docs = self._extract_module_docs(tmp_path)
        filenames = os.listdir(path)
        modules = []
        module_names = []
        for f in filenames:
            filepath = os.path.join(path, f)
            if os.path.isdir(filepath) and os.path.exists(os.path.join(filepath, '__init__.py')):
                module_names.append(f)
        module_names.sort()
        for m in module_names:
            props = self.get_metadata(m)
            modules.append({'name':props['name'], 'documentation':props['documentation']})

        props = {
            'type': 'module',
            'name': '/',
            'documentation': docs,
            'items': modules,
        }
        return (None, props)


    def error_handler(self, path):
        return (None, "Error: Can't resolve query '{}'".format(path))

    def get_info(self, query):
        """
        Get information on actor_type specified as <ns>.<Name>, e.g. 'io.Print

        Returns tuple (info, src, properties), where
            info is an enum: Pathinfo(invalid, directory, actor, component)
            src is the actor implementation
            properties is metadata
        """
        for actorpath in self.actorpaths:
            path, typeinfo = self.normalize(actorpath, query)
            if typeinfo == Pathinfo.invalid:
                continue
            handler = {
                Pathinfo.root : self.get_root,
                Pathinfo.directory : self.get_directory,
                Pathinfo.actor : self.get_actor,
                Pathinfo.component : self.get_component,
            }.get(typeinfo, self.error_handler)
            src, properties = handler(path)
            return (typeinfo, src, properties)
        return (Pathinfo.invalid, None, None)

    def get_metadata(self, query):
        _, _, metadata = self.get_info(query)
        return metadata

    def get_src(self, query):
        _, src, _ = self.get_info(query)
        return src


    # metadata_example
    #     'flow.Init' => {
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

    # metadata_example
    #     'flow' => {
    #     'type': 'module',
    #     'name': 'flow',
    #     'items': [
    #         {
    #             'name':'Foo',
    #             'documentation': ["actor doc", ""]
    #         },
    #         {
    #             'name':'Bar',
    #             'documentation': ["actor doc", ""]
    #         },
    #     ]
    #     'documentation': ['', '',]
    # }

    # metadata_example
    #     '' => {
    #     'type': 'module',
    #     'name': '/',
    #     'items': [
    #         {
    #             'name':'Baz',
    #             'documentation': ["module doc", ""]
    #         },
    #         {
    #             'name':'Bit',
    #             'documentation': ["module doc", ""]
    #         },
    #     ]
    #     'documentation': ['', '',]
    # }




if __name__ == '__main__':
    s = Store()
    print(json.dumps((s.get_metadata('std.CountTimer')), indent=4))
    print(json.dumps((s.get_metadata('std')), indent=4))
    print(json.dumps((s.get_metadata('')), indent=4))
