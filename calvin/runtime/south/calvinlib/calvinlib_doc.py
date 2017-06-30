# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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
import json

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class CalvinLibDoc(object):
    def __init__(self):
        _log.info("init")
        data = ""
        for dirpath, dirnames, filenames in os.walk("calvin/runtime/south/calvinlib"):
            for filename in filenames:
                if filename.endswith('.py'):
                    filename = filename[:-3]
                    try:
                        _log.info("importing {}".format(self.rel_path_to_namespace(os.path.join(dirpath, filename))))
                        pymodule = importlib.import_module(self.rel_path_to_namespace(os.path.join(dirpath, filename)))
                        if pymodule is not None:
                            pyclass = getattr(pymodule, filename)
                            if not pyclass:
                                continue
                            for attr in dir(pyclass):
                                if attr.endswith('_schema'):
                                    data += "### " + pyclass.__doc__.lstrip() + "\n"
                                    data += "### {}(args)\n#### args:\n```".format(attr[:-len("_schema")]) + json.dumps(getattr(pyclass, attr), indent=4, separators=(',', ': ')) + "```\n\n"
                    except Exception as e:
                        _log.info("Error: {}".format(e))
                        pass
        print data

    def rel_path_to_namespace(self, rel_path):
        return '.'.join([x for x in rel_path.split('/')]).strip('.')


if __name__ == '__main__':
    obj = CalvinLibDoc()
