import types
import re
from inspect import cleandoc

_routes = {}
_methods = []
_docs = []

uuid_re = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

def handler(route):
    def wrap(func):
        _docs.append(cleandoc(func.__doc__))
        _routes[func] = route
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

