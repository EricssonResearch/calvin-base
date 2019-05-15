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

from twisted.internet import reactor, inotify
from twisted.python import filepath

class INotify(object):
    """Monitor filesystems events"""
    def __init__(self, path, events, actor, trigger):
        super(INotify, self).__init__()
        self._path = path
        self._actor = actor
        self._trigger = trigger
        self.last_event = {}
        mask = 0x0
        if "modify" in events:
            mask = mask | inotify.IN_MODIFY
        if "create" in events:
            mask = mask | inotify.IN_CREATE
        if "delete" in events:
            mask = mask | inotify.IN_DELETE
        self._notifier = inotify.INotify(reactor=reactor)
        self._notifier.startReading()
        self._notifier.watch(filepath.FilePath(path), callbacks=[self.notify_cb], mask=mask)

    def notify_cb(self, ignored, filepath, mask):
        path = filepath.path.decode('utf-8')
        if mask & inotify.IN_CREATE:
            self.last_event = {"type": "create", "path": path}
            self._trigger(self._actor)
        elif mask & inotify.IN_DELETE:
            self.last_event = {"type": "delete", "path": path}
            self._trigger(self._actor)
        elif mask & inotify.IN_MODIFY:
            self.last_event = {"type": "modify", "path": path}
            self._trigger(self._actor)

    def triggered(self):
        return len(self.last_event) > 0

    def read(self):
        event = self.last_event
        self.last_event = {}
        return event

    def close(self):
        self._notifier.ignore(self._path)
