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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class ResourceReporter(Actor):
    """
    Sends node's CPU usage to output
    Outputs:
      out : A JSON string containing System CPU Usage
    """

    @manage([])
    def init(self, quiet=False):
        self.quiet = quiet
        self.use('calvinsys.native.python-psutil', shorthand='psutil')
        self._setup()

    def _setup(self):
        if self.quiet:
            self.logger = _log.debug
        else:
            self.logger = _log.info

    @condition([], ['out'])
    @guard(lambda self: not self.quiet)
    def report(self):
        usage = {'cpu_percent': self['psutil'].cpu_percent()}

        self.logger("%s<%s>: %s" % (self.__class__.__name__, self.id, str(usage)))

        return ActionResult(production=(usage, ))

    action_priority = (report, )
    requires = ['calvinsys.native.python-psutil']

    test_kwargs = {'quiet': False}
    test_set = [
        {
            'out': {'out': [{
                'cpu_percent': 25.8
            }]}
        }
    ]
