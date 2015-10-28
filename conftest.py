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

import pytest
import uuid
import logging
import sys
import os

from calvin.utilities import calvinlogger

_config_pytest = None

# pytest_plugins = "pytest_twisted"

def pytest_addoption(parser):
    parser.addoption("--loglevel", action="append", default=[],
            help="Set log level, levels: CRITICAL, ERROR, WARNING, INFO, DEBUG and ANALYZE. To enable on specific modules use 'module:level'")
    parser.addoption("--logfile", action="store", default=None,
            help="Set logging to file, specify filename")
    parser.addoption("--actor", action="store", default="",
                     help="Select an actor for test, if empty all actors are tested")
    parser.addoption("--runslow", action="store_true",
                     help="run slow tests")
    parser.addoption("--runinteractive", action="store_true",
                     help="run interactive tests")


def pytest_runtest_setup(item):
    essential = 'essential' in item.keywords

    if not essential and 'slow' in item.keywords and not item.config.getoption("--runslow"):
        pytest.skip("need --runslow option to run")
    if 'interactive' in item.keywords and not item.config.getoption("--runinteractive"):
        pytest.skip("need --runinteractive option to run")


def pytest_configure(config):
    global _config_pytest
    _config_pytest = config
    filename = config.getoption("logfile")
    if filename:
        calvinlogger.set_file(filename)
    levels = config.getoption("loglevel")
    for level in levels:
        module = None
        if ":" in level:
            module, level = level.split(":")
        print("Setting debuglevel %s on module %s" % (level, module))
        if level == "CRITICAL":
            calvinlogger.get_logger(module).setLevel(logging.CRITICAL)
        elif level == "ERROR":
            calvinlogger.get_logger(module).setLevel(logging.ERROR)
        elif level == "WARNING":
            calvinlogger.get_logger(module).setLevel(logging.WARNING)
        elif level == "INFO":
            calvinlogger.get_logger(module).setLevel(logging.INFO)
        elif level == "DEBUG":
            calvinlogger.get_logger(module).setLevel(logging.DEBUG)
        elif level == "ANALYZE":
            calvinlogger.get_logger(module).setLevel(5)

    if not os.environ.get('CALVIN_GLOBAL_DHT_NETWORK_FILTER'):
        # TODO: add func to set any argument from here also
        from calvin.utilities import calvinconfig
        _conf = calvinconfig.get()
        _conf.add_section('ARGUMENTS')
        _conf.set('ARGUMENTS', 'DHT_NETWORK_FILTER', str(uuid.uuid4()))

@pytest.fixture
def testarg_actor(request):
    return request.config.getoption("--actor")
