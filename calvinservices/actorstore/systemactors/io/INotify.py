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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys

class INotify(Actor):

    """
    documentation:
    - Monitor filesystem for changes
    ports:
    - direction: in
      help: Path to monitor.
      name: path
    - direction: out
      help: dictionary with type (create/delete/modify) and path
      name: data
    requires:
    - io.inotify
    """

    @manage(['notify'])
    def init(self):
        self.notify = None
        self.path = None

    @stateguard(lambda self: not self.notify)
    @condition(['path'], [])
    def watch(self, path):
        self.path = path
        self.notify = calvinsys.open(self, "io.inotify", path=path, events=["modify", "create", "delete"])

    @stateguard(lambda self: self.notify is not None and calvinsys.can_read(self.notify))
    @condition([], ['data'])
    def modified(self):
        data = calvinsys.read(self.notify)
        return (data, )

    action_priority = (watch, modified)
