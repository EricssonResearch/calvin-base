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
import importlib
import inspect
import json

class CalvinSysDoc(object):
    def __init__(self):
        data = ""
        for dirpath, dirnames, filenames in os.walk("calvin/runtime/south/calvinsys"):
            for filename in filenames:
                if filename.endswith('.py'):
                    filename = filename[:-3]
                    try:
                        pymodule = importlib.import_module(self.rel_path_to_namespace(os.path.join(dirpath, filename)))
                        if pymodule is not None:
                            pyclass = getattr(pymodule, filename)
                            if not pyclass:
                                continue
                            if hasattr(pyclass, 'init_schema'):
                                data += "### " + pyclass.__doc__.lstrip() + "\n"
                                data += "### init(args)\n#### args:\n```\n" + json.dumps(pyclass.init_schema, indent=4, separators=(',', ': ')) + "```\n\n"
                            if hasattr(pyclass, 'can_read_schema'):
                                data += "### can_read()\n#### Returns:\n```\n" + json.dumps(pyclass.can_read_schema, indent=4, separators=(',', ': ')) + "```\n\n"
                            if hasattr(pyclass, 'read_schema'):
                                data += "### read()\n#### Returns:\n```\n" + json.dumps(pyclass.read_schema, indent=4, separators=(',', ': ')) + "```\n\n"
                            if hasattr(pyclass, 'can_write_schema'):
                                data += "### can_write()\n#### Returns:\n```\n" + json.dumps(pyclass.can_write_schema, indent=4, separators=(',', ': ')) + "```\n\n"
                            if hasattr(pyclass, 'write_schema'):
                                data += "### write(args)\n#### args:\n```\n" + json.dumps(pyclass.write_schema, indent=4, separators=(',', ': ')) + "```\n\n"
                    except Exception:
                        pass
        print data

    def rel_path_to_namespace(self, rel_path):
        return '.'.join([x for x in rel_path.split('/')]).strip('.')


if __name__ == '__main__':
    obj = CalvinSysDoc()
