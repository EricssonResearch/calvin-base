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
from calvin.runtime.south import asynchronous
from calvin.common.calvinlogger import get_logger

_log = get_logger(__name__)

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
            mask = mask | inotify.IN_DELETE | inotify.IN_DELETE_SELF
        self._mask = mask
        self._backoffcnt = 0
        self._notifier = inotify.INotify(reactor=reactor)
        self._notifier.startReading()
        try:
            self._notifier.watch(filepath.FilePath(path), callbacks=[self.notify_cb], mask=mask)
        except:
            # No way to respond with failure, retry instead
            _log.exception("Failed watching {} with inotify, retry in a while".format(self._path))
            self._delayedwatch = asynchronous.DelayedCall(1, self.rewatch_cb)

    def rewatch_cb(self):
        try:
            self._notifier.watch(filepath.FilePath(self._path), callbacks=[self.notify_cb], mask=self._mask)
            self._backoffcnt = 0
        except:
            _log.error("Failed watching {} with inotify, retry in a while".format(self._path))
            self._backoffcnt += 1
            self._delayedwatch.reset(1 if self._backoffcnt < 60 else 30)

    def notify_cb(self, ignored, filepath, mask):
        path = filepath.path.decode('utf-8')
        if mask & inotify.IN_CREATE:
            self.last_event = {"type": "create", "path": path}
            self._trigger(self._actor)
        elif (mask & inotify.IN_DELETE) or (mask & inotify.IN_DELETE_SELF):
            self.last_event = {"type": "delete", "path": path}
            if mask & inotify.IN_DELETE_SELF:
                # Since object is deleted commonly is used to replace a file, try to watch path again
                self._delayedwatch = asynchronous.DelayedCall(0, self.rewatch_cb)
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
        try:
            self._notifier.ignore(self._path)
        except:
            pass
