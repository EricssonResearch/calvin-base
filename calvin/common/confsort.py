#!/usr/bin/python
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
"""
Option Parser sorting module.
This module implements a sorting method for options in a
configuration file.
"""
from operator import itemgetter, attrgetter, methodcaller


class Options:
    """
    Collection of options.
    """
    def __init__(self):
        self.options = []

    def insert(self, option):
        """
        Insert option in to options
        """
        self.options.append(option)

    def __repr__(self):
        return repr(self.options)

    def dict(self):
        """
        Return unstructured dictionary with key, value of options.
        """
        optionsdict = {}
        for option in self.options:
            optionsdict[option.key] = option.value
        return optionsdict

    def compare(self, comparable):
        if comparable.getvar() == None:  # Non variable options pass
            return 0

        for option in self.options:
            if comparable.getvar() == option.key:
                return 1  # Variables are lower
        return 0  # Non resolvable variables can go high

    def sort(self):
        """
        Sort options based on definition before use.
        """
        self.options = sorted(self.options,
                              key=self.compare)
        return self.options


class Option:
    """
    Class to store one option in a section of a ConfigParser.
    """
    def __init__(self, key, value):
        self.key = key.strip()
        self.value = value.strip()

    def __repr__(self):
        return self.key

    def getvar(self):
        """
        Find variable in a string.
        """
        variable = "".join(self.value.split("$")[1:])
        variable = variable.split("/")[0]
        return variable


def reorder(fname):
    """
    Reorder fields in a configuration file so that
    assignments of variables comes before use.
    """
    fp = open(fname, 'r+')
    options = Options()
    configresult = {}
    section = ""
    configresult[section] = Options()

    for line in fp.readlines():
        line = line.strip()
        if line.startswith("["):
            # New section
            section = line
            configresult[section] = Options()
        elif line.startswith("#"):
            pass
            # Lonely comments are removed
        else:
            # Store an option
            try:
                key, value = line.split("=")
                configresult[section].insert(Option(key, value))
            except ValueError:
                pass  # Ignore all weird lines
    fp.seek(0)
    fp.truncate()

    for section in configresult:
        fp.write("{}\n".format(section))
        configresult[section].sort()  # Sort options in this section
        for option in configresult[section].options:
            fp.write("{}={}\n".format(option.key, option.value))

    fp.close()
