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

from datetime import datetime
from calvin.actorstore.store import GlobalStore
from calvin.utilities import dynops
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class PolicyInformationPoint(object):

    def __init__(self, node, request):
        self.attributes = {
            "subject": {
                "actor_signer": self._get_actor_signer
            },
            "action": {
                "requires": self._get_requires
            },
            "environment": {
                "current_date": self._get_current_date,
                "current_time": self._get_current_time
            }
        }
        self.node = node
        self.request = request
        self.actorstore = GlobalStore(node=node)
        self.actor_desc = None

    def get_attribute_value(self, attribute_type, attribute):
        """Return the specified attribute if it exists in attributes dictionary"""
        value = self.attributes[attribute_type][attribute]
        if hasattr(value, '__call__'):
            # The value is a function, call the function.
            func_value = value()
            # Cache the value (replace function) since same value should be used for future tests when handling this request.
            self.attributes[attribute_type][attribute] = func_value
            return func_value
        return value

    def _get_actor_signer(self):
        return self.actor_desc["signer"]

    def _get_requires(self):
        return ["runtime"] + self.actor_desc["requires"]

    def _get_current_date(self):
        return datetime.now().strftime('%Y-%m-%d')

    def _get_current_time(self):
        return datetime.now().strftime('%H:%M')

    def actor_desc_lookup(self, actorstore_signature, callback):
        _log.debug("actor_desc_lookup:\n\t actorstore_signature={}\n\tcallback={}".format(actorstore_signature, callback))
        desc_iter = self.actorstore.global_lookup_iter(actorstore_signature, node_id=self.request["resource"]["node_id"])
        desc_iter.set_cb(self._set_actor_desc, desc_iter, callback)
        self._set_actor_desc(desc_iter, callback)

    def _set_actor_desc(self, desc_iter, callback):
        while True:
            try:
                desc = desc_iter.next()
            except StopIteration:
                callback(pip=self)
                return
            except dynops.PauseIteration:
                return
            self.actor_desc = desc
