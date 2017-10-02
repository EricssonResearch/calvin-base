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
import json
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.utils import get_home

_log = get_logger(__name__)
_config = None


class CalvinConfig(object):

    """
    Handle configuration of Calvin, works similiarly to python's ConfigParser
    Looks for calvin.conf or .calvin.conf files in:
    1. Built-ins
    2. Calvin's install directory
    3. home folder
    4. all directories between $CWD and home folder
    5. current working directory ($CWD)
    If $CWD is outside of home folder, only (1) through (3) are searched.

    The environment variable CALVIN_CONFIG_PATH can be set to a colon-separated list of paths that
    will be searched after directories (1) through (5) above.

    All config files found in the above locations will be read, and merged into a single config.
    Note that the last config file read has the highest preceedence. The following rules apply:
    New key/value pairs are ADDED, but for existing keys, simple values are OVERRIDDEN by later configs,
    whereas lists are PREPENDED by values from later configs.

    In order to completely bypass the standard config paths, the environment variable CALVIN_CONFIG
    can be set to point to a config FILE that will be taken as the ONLY configuration file,
    disregarding even the built-in settings.

    Finally, wildcard environment variables on the form CALVIN_<SECTION>_<OPTION> may override
    options read from defaults or config files. <SECTION> must be one of GLOBAL, TESTING, DEVELOPER, or
    ARGUMENTS e.g. CALVIN_TESTING_UNITTEST_LOOPS=42

    Printing the config object provides a great deal of information about the configuration.
    """
    def __init__(self):
        super(CalvinConfig, self).__init__()
        self.config = {}
        self.wildcards = []
        self.override_path = os.environ.get('CALVIN_CONFIG', None)
        self.extra_paths = os.environ.get('CALVIN_CONFIG_PATH', None)

        # Setting CALVIN_CONFIG takes preceedence over all other configs
        if self.override_path is not None:
            config = self.read_config(self.override_path)
            if config is not None:
                self.set_config(config)
            else:
                self.override_path = None
                _log.info("CALVIN_CONFIG does not point to a valid config file.")

        # This is the normal config procedure
        if self.override_path is None:
            # The next line is guaranteed to work, so we have at least a default config
            self.set_config(self.default_config())
            conf_paths = self.config_paths()
            for p in conf_paths:
                delta_config = self.config_at_path(p)
                self.update_config(delta_config)

        # Check if any options were set on the command line
        self.set_wildcards()

        _log.debug("\n{0}\n{1}\n{0}".format("-" * 80, self))

    def default_config(self):
        default = {
            'global': {
                'comment': 'User definable section',
                'actor_paths': ['systemactors'],
                'framework': 'twistedimpl',
                'storage_type': 'dht', # supports dht, securedht, local, and proxy
                'storage_proxy': None,
                'capabilities_blacklist': [],
                'remote_coder_negotiator': 'static',
                'static_coder': 'json',
                'metering_timeout': 10.0,
                'metering_aggregated_timeout': 3600.0,  # Larger or equal to metering_timeout
                'display_plugin': 'stdout_impl',
                'stdout_plugin': 'defaultimpl',
                'transports': ['calvinip'],
                'control_proxy': None,
                'fcm_server_secret': None
            },
            'testing': {
                'comment': 'Test settings',
                'unittest_loops': 2
            },
            'developer': {
                'comment': 'Experimental settings',
            },
            'security': {},
            'calvinsys': {
                "capabilities": {
                    "sys.timer.once": {
                        "module": "sys.timer.Timer",
                        "attributes": {}
                    },
                    "sys.timer.repeating": {
                        "module": "sys.timer.Timer",
                        "attributes": {"repeats": True }
                    }
                }
             },
             'calvinlib': {
                 "capabilities": {
                     "json": {
                         "module": "jsonlib.Json"
                     },
                     "base64": {
                         "module": "base64lib.Base64"
                     },
                     "copy": {
                         "module": "datalib.Copy"
                     }
                 }
             }
        }
        return default

    def sections(self):
        return self.config.keys()

    def has_section(self, section):
        return section in self.config

    def add_section(self, section):
        """Add a named section"""
        self.config.setdefault(section.lower(), {})

    def get_in_order(self, option, default=None):
        v = self.get('ARGUMENTS', option)
        if v is None:
            v = self.get('GLOBAL', option)
        if v is None:
            v = default
        return v

    def get_section(self, section):
        """Get value of option in named section, if section is None 'global' section is implied."""
        try:
            _section = section.lower()
            return self.config[_section]
        except KeyError:
            _log.debug("Option {} does not exist".format(_section))
        except Exception as e:
            _log.error("Error reading option {}: {}".format(_section, e))
            return None

    def get(self, section, option):
        """Get value of option in named section, if section is None 'global' section is implied."""
        try:
            _section = 'global' if section is None else section.lower()
            _option = option.lower()
            return self.config[_section][_option]
        except KeyError:
            _log.debug("Option {}.{} does not exist".format(_section, _option ))
        except Exception as e:
            _log.error("Error reading option {}.{}: {}".format(_section, _option, e))
            return None

    def set(self, section, option, value):
        """Set value of option in named section"""
        _section = self.config[section.lower()]
        _section[option.lower()] = value

    def append(self, section, option, value):
        """Append value (list) of option in named section"""
        _section = self.config[section.lower()]
        _option = option.lower()
        old_value = _section.setdefault(_option, [])
        if type(old_value) is not dict:
            raise Exception("Can't append, {}:{} is not a list".format(section, option))
        if type(value) is not list:
            raise Exception("Can't append, value is not a list")

        _section[_option] = value + [ v for v in _section[_option] if v not in value ]

    def update(self, section, option, value):
        """Set value of option in named section"""
        _section = self.config[section.lower()]
        _section[option.lower()].update(value)


    def set_config(self, config):
        """Set complete config"""
        for section in config:
            _section = section.lower()
            self.add_section(_section)
            for option, value in config[section].iteritems():
                _option = option.lower()
                self.set(_section, _option, value)

    def _case_sensitive_keys(self, section, option, conf):
        """Return the case sensitive keys for 'secton' and 'option' (or None if not present) in 'conf'."""
        for _section in conf:
            if _section.lower() != section.lower():
                continue
            for _option in conf[section]:
                if _option.lower() == option.lower():
                    return _section, _option
            return _section, None
        return None, None

    def _expand_actor_paths(self, conf, conf_dir):
        """Expand $HOME, $USER etc. and resolve './actors' etc. relative to the config file."""
        # Get the correct keys to use with the config dict since we allow mixed case, but convert to lower internally
        _section, _option = self._case_sensitive_keys('global', 'actor_paths', conf)
        if not _option:
            return
        paths = conf[_section][_option]
        # First handle expansion of env vars
        expanded = [os.path.expandvars(p) for p in paths]
        # Normalize and handle './', i.e. relative to config file
        conf[_section][_option] = [os.path.normpath(os.path.join(conf_dir, p) if p.startswith('./') else p) for p in expanded]

    def config_at_path(self, path):
        """Returns config or None if no config at path."""
        if os.path.exists(path + '/calvin.conf'):
            confpath = path + '/calvin.conf'
        elif os.path.exists(path + '/.calvin.conf'):
            confpath = path + '/.calvin.conf'
        elif os.path.exists(path) and os.path.isfile(path):
            confpath = path
        else:
            return None
        return self.read_config(confpath)

    def read_config(self, filepath):
        try:
            with open(filepath) as f:
                conf = json.loads(f.read())
                path = os.path.dirname(filepath)
                self._expand_actor_paths(conf, path)
        except Exception as e:
            _log.info("Could not read config at '{}': {}".format(filepath, e))
            conf = None
        return conf

    def update_config(self, delta_config):
        """
        Update config using delta_config.
        If value in delta_config is list, prepend to value in config,
        otherwise replace value in config.
        """
        if not delta_config:
            return
        for section in delta_config:
            for option, value in delta_config[section].iteritems():
                if option.lower() == 'comment':
                    continue
                operation = {
                    list:self.append,
                    dict:self.update
                }.get(type(value), self.set) # self.append if type(value) is list else self.set
                operation(section, option, value)

    def install_location(self):
        """Return the 'installation dir'."""
        this_dir = os.path.dirname(os.path.realpath(__file__))
        install_dir = os.path.abspath(os.path.join(this_dir, '..'))
        return install_dir

    def config_paths(self):
        """
        Return the list of paths to search for configs.
        If install dir is in the path from home folder to CWD it is not included a second time.
        """
        if self.override_path is not None:
            return [self.override_path]

        inst_loc = self.install_location()
        curr_loc = os.getcwd()
        home = get_home() or curr_loc
        paths = [inst_loc, home]

        insert_index = len(paths)
        if curr_loc.startswith(home):
            while len(curr_loc) > len(home):
                if curr_loc != inst_loc:
                    paths.insert(insert_index, curr_loc)
                curr_loc, part = curr_loc.rsplit('/', 1)

        epaths = self.extra_paths.split(':') if self.extra_paths else []
        paths.extend(epaths)

        return paths

    def set_wildcards(self):
        """
        Allow environment variables on the form CALVIN_<SECTION>_<OPTION> to override options
        read from defaults or config files. <SECTION> must be one of GLOBAL, TESTING, or DEVELOPER.
        """
        wildcards = [e for e in os.environ if e.startswith('CALVIN_') and not e.startswith('CALVIN_CONFIG')]
        for wildcard in wildcards:
            parts = wildcard.split('_', 2)
            if len(parts) < 3 or parts[1] not in ['GLOBAL', 'TESTING', 'DEVELOPER', 'ARGUMENTS']:
                _log.info("Malformed environment variable {}, skipping.".format(wildcard))
                continue
            section, option = parts[1:3]
            value = os.environ[wildcard]
            try:
                self.set(section, option, json.loads(value))
                self.wildcards.append(wildcard)
            except Exception as e:
                _log.warning("Value {} of environment variable {} is malformed, skipping.".format(repr(value), wildcard))

    def save(self, path, skip_arguments=True):
        json.dump({k: v for k, v in self.config.iteritems() if k != "arguments" or not skip_arguments}, open(path, 'w'))

    def __str__(self):
        d = {}
        d['config searchpaths'] = self.config_paths(),
        d['config paths'] = [p for p in self.config_paths() if self.config_at_path(p) is not None],
        d['config'] = self.config
        d['CALVIN_CONFIG'] = self.override_path
        d['CALVIN_CONFIG_PATH'] = self.extra_paths
        d['wildcards'] = self.wildcards
        return self.__class__.__name__ + " : " + json.dumps(d, indent=4, sort_keys=True)


def get():
    global _config
    if _config is None:
        _config = CalvinConfig()
    return _config


if __name__ == "__main__":
    os.environ['CALVIN_CONFIG_PATH'] = '/Users/eperspe/Source/spikes/ConfigParser'
    os.environ['CALVIN_TESTING_UNITTEST_LOOPS'] = '44'
    a = get()

    print(a)
    p = a.get('global', 'actor_paths')
    print(p, type(p))

    p = a.get(None, 'framework')
    print(p, type(p))
    p = a.get(None, 'unittest_loops')
    print(p, type(p))

    p = a.get('Testing', 'unittest_loops')
    print(p, type(p))
