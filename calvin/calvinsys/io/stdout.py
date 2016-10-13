# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

from calvin.runtime.south.plugins.io.stdout import stdout


class StandardOut(object):

    """
    Write text to stdout (for some definition of stdout)
    """

    def __init__(self, node, actor):
        super(StandardOut, self).__init__()
        self._node = node
        self._actor = actor
        if self._node.attributes.has_private_attribute("/io/stdout"):
            # Use runtime specific stdout configuration
            stdout_config = self._node.attributes.get_private("/io/stdout")
        else :
            stdout_config = None
        self.stdout = stdout.StandardOut(stdout_config)

    def enable(self):
        """
        start stdout
        """
        self.stdout.enable()

    def disable(self):
        """
        stop stdout
        """
        self.stdout.disable()
        
    def write(self, text):
        """
        write text to stdout
        """
        self.stdout.write(text)

    def writeln(self, text):
        """
        write text to stdout, add newline
        """
        self.stdout.writeln(text)
        
def register(node=None, actor=None):
    """
        Called when the system object is first created.
    """
    return StandardOut(node, actor)
