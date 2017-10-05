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

from calvin.actor.actor import Actor, manage, condition
from calvin.utilities import calvinlogger
_log = calvinlogger.get_logger(__name__)


class Log(Actor):
    """
    Write data to calvin log using specified loglevel.
    Supported loglevels: INFO, WARNING, ERROR

    Input:
      data : data to be logger
    """

    def exception_handler(self, action_function, args):
        # The action 'log' takes a single token
        exception_token = args[0]
        return action_function(self, "Exception '%s'" % (exception_token,))

    @manage(['loglevel'])
    def init(self, loglevel):
        self.loglevel = loglevel
        self.setup()

    def setup(self):
        if self.loglevel == "INFO":
            self._logger = _log.info
        elif self.loglevel == "WARNING":
            self._logger = _log.warning
        elif self.loglevel == "ERROR":
            self._logger = _log.error
        else :
            self._logger = _log.info

    def will_migrate(self):
        self._logger(" -- migrating")

    def did_migrate(self):
        self.setup()
        self._logger(" -- finished migrating")

    @condition(action_input=['data'])
    def log(self, data):
        self._logger("{}".format(data))


    action_priority = (log, )
