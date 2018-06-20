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

_routes = {}
_methods = []
_docs = []

uuid_re = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

def handler(method, path):
    def wrap(func):
        _docs.append(cleandoc(func.__doc__))
        _routes[func] = method + " " + path + r"\s+HTTP/1"
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

