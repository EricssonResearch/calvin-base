# -*- coding: utf-8 -*-

# Copyright (c) 2018 Ericsson AB
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

import types
import re
from inspect import cleandoc
from calvin.utilities.calvinlogger import get_logger


_log = get_logger(__name__)

_routes = {}
_methods = []
_docs = []

uuid_re = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

app_uuid_re = "(APP_" + uuid_re + "|" + uuid_re + ")"
actor_uuid_re = "(ACTOR_" + uuid_re + "|" + uuid_re + ")"
port_uuid_re = "(PORT_" + uuid_re + "|" + uuid_re + ")"
repl_uuid_re = "(REPLICATION_" + uuid_re + "|" + uuid_re + ")"
trace_uuid_re = "(TRACE_" + uuid_re + "|" + uuid_re + ")"
node_uuid_re = "(NODE_" + uuid_re + "|" + uuid_re + ")"
policy_uuid_re = "(POLICY_" + uuid_re + "|" + uuid_re + ")"
path_re = r"(/?[0-9a-zA-Z\.\-/_]*)"

path_regex = {
    "uuid": uuid_re,
    "application_id": app_uuid_re,
    "actor_id": actor_uuid_re,
    "port_id": port_uuid_re,
    "replication_id": repl_uuid_re,
    "trace_id": trace_uuid_re,
    "node_id": node_uuid_re,
    "policy_id": policy_uuid_re,
    "path": path_re,
    # "ident": ident_re
}

def handler(method, path, optional=None):
    def wrap(func):
        _docs.append(cleandoc(func.__doc__))
        if optional:
            alts = "|".join(o for o in optional)
            opts = "(?:({alts}))?".format(alts=alts)
        else:
            opts = ""
        _routes[func] = "{method} {path}{opts}{end}".format(
            method=method,
            path=path.format(**path_regex),
            opts=opts,
            end=r"\s+HTTP/1")
        _methods.append(func)
        return func
    return wrap


def register(func):
    _methods.append(func)
    return func

def routes():
    return _routes

def methods():
    return _methods

def docs():
    return "\n\n".join(_docs)

def install_handlers(target):
    routes = []
    for f in _methods:
        setattr(target, f.__name__, types.MethodType(f, target))
        if f in _routes:
            routes.append((re.compile(_routes[f]), getattr(target, f.__name__)))
    return routes

