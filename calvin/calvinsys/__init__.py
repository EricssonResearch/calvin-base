""" CalvinSys handler """

import importlib
import pkgutil
import os
import inspect
from calvin.utilities import calvinconfig
from calvin.utilities.calvinlogger import get_logger

_conf = calvinconfig.get()
_log = get_logger(__name__)


class Sys(object):
    """ Calvin system object """
    def __init__(self, node=None):
        self._node = node

        path = [os.path.dirname(inspect.getfile(Sys))]
        name = __name__

        self._name = name
        self._path = path
        self.modules = {}

        packages = pkgutil.walk_packages(path, name + '.')
        blacklist = _conf.get(None, 'capabilities_blacklist') or []
        _log.analyze(node.id if node else None, "+ BLACKLIST", {'blacklist': blacklist})
        for package in packages:
            if not package[2]:
                (_, _, package_name) = package[1].partition(".")
                # this is a loadable module
                if package_name not in blacklist:
                    self.modules[package_name] = {'name': package[1], 'module': None, 'error': None}
            else:
                # This is a package, ignore it
                pass

    def scheduler_wakeup(self):
        self._node.sched.trigger_loop()

    def _loadmodule(self, modulename):
        if self.modules[modulename]['module'] or self.modules[modulename]['error']:
            return

        try:
            self.modules[modulename]['module'] = importlib.import_module(self.modules[modulename]['name'])
        except Exception as e:
            _log.info("Module '%s' not available: %s" % (modulename, e))
            self.modules[modulename]['error'] = e

    def use_requirement(self, actor, modulename):
        if self.require(modulename):
            raise self.modules[modulename]['error']
        return self.modules[modulename]['module'].register(node=self._node, actor=actor)

    def require(self, modulename):
        if not self.modules.get(modulename, None):
            self.modules[modulename] = {'error': Exception("No such capability '%s'" % (modulename,)), 'module': None}

        self._loadmodule(modulename)

        return self.modules[modulename]['error']

    def has_capability(self, requirement):
        """
        Returns True if "requirement" is satisfied in this system,
        otherwise False.
        """
        return not self.require(requirement)

    def list_capabilities(self):
        """
        Returns list of requirements this system satisfies
        """
        return [cap for cap in self.modules.keys() if self.has_capability(cap)]
