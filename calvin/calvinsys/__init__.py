""" CalvinSys handler """

import importlib
import pkgutil
import os
import inspect


class Sys(object):
    """ Calvin system object """
    def __init__(self, node=None, actor=None):
        self._node = node
        self._actor = actor

        path = [os.path.dirname(inspect.getfile(Sys))]
        name = __name__

        self._name = name
        self._path = path
        self.modules = {}
        self.using = {}

        packages = pkgutil.walk_packages(path, name + '.')

        for package in packages:
            if not package[2]:
                (_, _, package_name) = package[1].partition(".")
                # this is a loadable module
                self.modules[package_name] = {'name': package[1], 'module': None, 'error': None}
            else:
                # This is a package, ignore it
                pass

    def scheduler_wakeup(self):
        self._node.sched.trigger_loop()

    def __getitem__(self, idx):
        if idx in self.using:
            return self.using[idx]
        else:
            raise KeyError(idx)

    def _loadmodule(self, modulename):
        if self.modules[modulename]['module'] or self.modules[modulename]['error']:
            return

        try:
            # print "loading %s" % (self.modules[modulename],)
            self.modules[modulename]['module'] = importlib.import_module(self.modules[modulename]['name'])
        except Exception as e:
            # print " Failed to load module %s: %s" % (modulename, str(e))
            self.modules[modulename]['error'] = e

    def use(self, modulename, shorthand=None):
        if self.require(modulename):
            raise self.modules[modulename]['error']

        # if not self.using.get(shorthand, False):
        #    self.using[shorthand] = self.modules[modulename]['module'].register(node=self._node, actor=self._actor)
        if shorthand:
            self.using[shorthand] = self.modules[modulename]['module'].register(node=self._node, actor=self._actor)
        else:
            return self.modules[modulename]['module'].register(node=self._node, actor=self._actor)

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
