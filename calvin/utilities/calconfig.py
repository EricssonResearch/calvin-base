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
import ConfigParser
import json

_config = None


class CalConfig(ConfigParser.ConfigParser):
    dirname = os.path.join(os.path.expanduser("~"), ".calvin")
    filename = 'calvin.conf'

    # All default will be written to file at first run
    defaults = {'unittest_loops': '2',
                'actor_paths': ["systemactors", "devactors", "demoactors", "appactors"],
                'remote_coder_negotiator': 'static', 'static_coder': 'json',
                'framework': 'twistedimpl'}
    section_name = "Global"

    def __init__(self):
        ConfigParser.ConfigParser.__init__(self)

        filepath = os.getenv("CALVIN_CONFIG_PATH")

        if filepath:
            self.filepath = filepath
        else:
            self.filepath = os.path.join(self.dirname, self.filename)

        # First time start lets create defs
        if not os.path.exists(self.filepath):
            self.create_defaults()
            # Do not write the calvin.conf at the moment.
            # TODO: Write 'sample' calvin.conf for users to peruse
            # self.write(open(self.filepath, "w"))
            pass
        else:
            self.read(self.filepath)

    def intify(self, val):
        try:
            a = int(val)
        except:
            return val
        return a

    def _get_json(self, value):
        try:
            value = json.loads(value)
        except (ValueError, TypeError) as e:
            pass
        return value

    # Override get so enviorment overrides configs
    def get(self, section, option, raw=False, vars=None):

        if section is None:
            section = self.section_name

        val = os.getenv('CALVIN_%s' % option.upper())
        conf_val = self._get_json(ConfigParser.ConfigParser.get(self, section, option,
                                                          raw, vars))
        if val:
            if not raw and os.pathsep in val:
                # We have list extend with config
                val = val.split(os.pathsep)
            else:
                val = self._get_json(val)

            if isinstance(conf_val, type([])) and isinstance(val, type([])):
                return val + conf_val

            return val

        return conf_val

    def create_defaults(self):
        self.add_section(self.section_name)
        for k, v in self.defaults.items():
            self.set(self.section_name, k, v)

    def set(self, section, key, value):
        value_str = value
        try:
            value_str = json.dumps(value)
        except ValueError as e:
            pass
            # _log.warning(e)

        if section is None:
            section = self.section_name

        ConfigParser.ConfigParser.set(self, section, key, value_str)


def get():
    global _config
    if _config is None:
        _config = CalConfig()
    return _config


if __name__ == "__main__":
    a = get()
    print(a.get(None, 'actor_paths'))
