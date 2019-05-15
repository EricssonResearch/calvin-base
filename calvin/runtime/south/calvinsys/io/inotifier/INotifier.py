# -*- coding: utf-8 -*-

# Copyright (c) 2019 Ericsson AB
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

from calvin.runtime.south.calvinsys import base_calvinsys_object
from calvin.runtime.south.asynchronous import INotify

class INotifier(base_calvinsys_object.BaseCalvinsysObject):
    """
    Monitoring of filesystems events
    """

    init_schema = {
        "type": "object",
        "properties": {
            "path": {
                "description": "Path to monitor",
                "type": "string"
            }
        },
        "required": ["path"],
        "description": "Initialize notifier"
    }

    can_read_schema = {
        "description": "Returns True if modified",
        "type": "boolean"
    }

    read_schema = {
        "description": "Clear event and get path"
    }

    def init(self, path, events, *kwargs):
        self.path = path
        self.notifier = INotify(path, events, self.actor, self.calvinsys.scheduler_wakeup)

    def can_read(self):
        return self.notifier.triggered()

    def read(self):
        return self.notifier.read()

    def close(self):
        self.notifier.close()
