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

import logging
import json
import inspect
import os
import traceback

from colorlog import ColoredFormatter

_name = "calvin"
_log = None
_use_color = False


class JSONEncoderIters(json.JSONEncoder):
    def default(self, o):
        # Convert any iterable to list
        try:
            iterable = iter(o)
        except TypeError:
            pass
        else:
            return list(iterable)
        if isinstance(o, (dict, list, basestring, int, long, float, bool, type(None))):
            # Let the base class handle it
            return json.JSONEncoder.default(self, o)
        else:
            # Convert it to a string
            return unicode(str(o))

def analyze(self, node_id, func, param, peer_node_id=None, tb=False, mute=False, *args, **kws):
    if not mute and self.isEnabledFor(5):
        if node_id is None:
            # Allow None node_id and enter the process id instead
            node_id = os.getpid()
        if func.startswith("+"):
            f = inspect.currentframe()
            if f is not None:
                func = os.path.basename(f.f_back.f_code.co_filename) + ":" + f.f_back.f_code.co_name + func[1:]
        if tb:
            stack = traceback.extract_stack()
        else:
            stack = None
        self._log(5, "[[ANALYZE]]" + json.dumps({'node_id': node_id,
                                                 'peer_node_id': peer_node_id,
                                                 'func': func,
                                                 'param': param,
                                                 'stack': stack}, cls=JSONEncoderIters), args, **kws)


logging.Logger.analyze = analyze
logging.addLevelName(5, "ANALYZE")


def _create_logger(filename=None):
    global _log
    global _name
    if _log is None:
        _log = logging.getLogger(_name)
        _log.setLevel(logging.INFO)

        # create console handler and set level to debug
        if filename:
            ch = logging.FileHandler(filename=filename, mode='w')
        else:
            ch = logging.StreamHandler()
        ch.setLevel(5)

        # create formatter
        colored = ColoredFormatter(
            "%(asctime)-15s %(log_color)s%(levelname)-8s %(process)d-%(name)s%(reset)s: %(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red',
            }
        )

        plain = ColoredFormatter(
            "%(asctime)-15s %(levelname)-8s %(process)d-%(name)s: %(message)s",
            datefmt=None,
            reset=False,
            log_colors={}
        )

        # formatter = logging.Formatter('%(asctime)-15s - %(levelname)-7s - %(name)s: %(message)s')s

        # add formatter to ch
        ch.setFormatter(colored if _use_color else plain)

        # add ch to logger
        _log.addHandler(ch)

    return _log


def set_file(filename):
    _create_logger(filename)


def get_logger(name=None):
    log = _create_logger()
    if name is None:
        return log
    return log.getChild("%s" % (name))


def get_actor_logger(name):
    log = _create_logger()
    return log.getChild("%s.%s" % ("actors", name))
