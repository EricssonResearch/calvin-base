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
import os.path
import json
import ast

from calvin.utilities import calvinconfig
_conf = calvinconfig.get()
schema_names = ["init_schema", "can_read_schema", "read_schema", "can_write_schema", "write_schema"]

class CalvinSysDoc(object):

    def __init__(self):
        self.objects = {}
        calvinsys_paths = _conf.get(None, 'calvinsys_paths') or []
        for path in calvinsys_paths:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    if filename.endswith('.py') and filename != "__init__.py":
                        name = self.rel_path_to_namespace(dirpath + os.sep + filename[:-3])
                        path = dirpath + "/" + filename
                        data = self.parse(path)
                        if data:
                            self.objects[name[len(dirpath) + 1:]] = data

    def create_doc(self, name, schemas, formatting="plain"):
        data = ""
        if formatting == "md":
            data += "## " + name + "\n\n"
        else:
            data += name + "\n"

        #for name, schema in schemas.iteritems():
        for name in schema_names: # init_string
            schema = schemas.get(name, None)
            if schema:
                description = schema.get('description', "")
                if formatting == "md":
                    data += "### `{}`\n".format(name) + "\n" + description + "\n```\n" + json.dumps(schema, indent=4, separators=(',', ': ')) + "\n```\n\n"
                else:
                    data += name + " = " + json.dumps(schema) + "\n"

        if formatting != "md":
            data += "\n"
        return data

    def help_raw(self, what=None):
        data = {}
        if what and what in self.objects:
            return json.dumps(self.objects[what])
        return json.dumps(self.objects)

    def help(self, what=None, formatting="plain"):
        data = ""
        if what and what in self.objects:
            data += self.create_doc(what, self.objects[what], formatting)
        else:
            for obj, schemas in sorted(self.objects.iteritems()):
                data += self.create_doc(obj, schemas, formatting)
        return data

    def convert(self, node):
        if isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Tuple):
            return tuple(map(self.convert, node.elts))
        elif isinstance(node, ast.List):
            return list(map(self.convert, node.elts))
        elif isinstance(node, ast.Dict):
            return dict((self.convert(k), self.convert(v)) for k, v in zip(node.keys, node.values))
        elif isinstance(node, ast.Name):
            return node.id
        raise ValueError('Unknown type')

    def parse(self, path):
        schemas = None
        file = open(path, 'r')
        data = file.read()
        root = ast.parse(data)

        try:
            for node in ast.walk(root):
                if isinstance(node, ast.Assign):
                    if hasattr(node.targets[0], 'id') and node.targets[0].id in schema_names:
                        schema_name = node.targets[0].id
                        for name, val in ast.iter_fields(node):
                            if isinstance(val, ast.Dict):
                                if not schemas:
                                    schemas = {}
                                schemas[schema_name] = self.convert(val)
        except:
            schemas = None
        file.close()
        return schemas

    def rel_path_to_namespace(self, rel_path):
        return '.'.join([x for x in rel_path.split('/')]).strip('.')

if __name__ == '__main__':
    obj = CalvinSysDoc()
    print obj.help(formatting="md")
