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

from calvin.actor.actor import Actor, ActionResult, guard, condition
from calvin.utilities.calvinlogger import get_logger

import datetime

def now():
    return datetime.datetime.now()
    
def elapsed(t):
    diff = now() - t
    return diff.total_seconds()
    
_log = get_logger(__name__)


class RFIDReader(Actor):

    """
    RFIDReader - read MIFare Classic/ultralight when present, write incoming data to it.
    
    Inputs:
        data : {"data": <data>}
    Outputs:
        data : {"cardno": uid, "data": <data>, "timestamp": <timestamp>}
    """

    def init(self):
        self.setup()

    def setup(self):
        self.use("calvinsys.events.timer", shorthand="timer")
        self.timeout_timer = self['timer'].once(0.0)
        self.use("calvinsys.sensors.rfid", shorthand="rfid")
        self.rfid = self["rfid"]
        self._state = "idle"
        self.active_uid = None
        self.active_uid_string = None
        self.active_type = None
        self.latest_activity = now()
        self.timeout = 0.5

    def did_migrate(self):
        self.setup()

    def will_migrate(self):
        self.timeout_timer.cancel()
        
    @condition()
    @guard(lambda self: self._state == "idle" and self.timeout_timer.triggered)
    def is_idle(self):
        _log.debug("is_idle")
        self.timeout_timer.ack()
        self.timeout_timer.cancel()
        
        if self.rfid.request_idl():
            uid = self.rfid.anti_collision()
            if uid is not None:
                self.active_uid = uid
                self.active_uid_string = self.rfid.uid_to_string(uid)
                _log.info("active card: %r" % (self.active_uid_string,))
                self._state = "card present"
            else :
                self._state = "reset"
        else :
            self.timeout_timer = self['timer'].once(0.01)
        return ActionResult()
        
    @condition()
    @guard(lambda self: self._state == "card present")
    def card_present(self):
        _log.info("card_present")
        active_type = self.rfid.select_tag(self.active_uid)
        if self.rfid.card_type(active_type) != "unknown":
            self.active_type = active_type
            self.latest_activity = now()
            if self.rfid.card_type(active_type) == "classic" and not self.rfid.authenticate_classic(self.active_uid):
                self._state = "reset"
            else :
                self._state = "card active"
        else :
            self._state = "reset"
        return ActionResult()

    @condition([], ["data"])
    @guard(lambda self: self._state == "card active")
    def read_card(self):
        _log.info("read_card")
        result = {"status": False, "cardno": self.active_uid_string}
        value = self.rfid.read_value(self.active_type)
        _log.info("Read: %r" % (value,))
        if value is not None:
            self.latest_activity = now()
            result["data"] = value
            result["status"] = True
            result["timestamp"] = str(now())
            self.timeout_timer = self['timer'].repeat(0.05)
            self._state = "check card"
        else :
            _log.info("could not read card %r" % (self.active_uid,))
            self._state = "reset"
        return ActionResult(production=(result,))
    
    @condition()
    @guard(lambda self: self._state == "check card" and self.timeout_timer.triggered)
    def check_card(self):
        _log.info("check_card")
        self.timeout_timer.ack()
        if self.rfid.read_value(self.active_type) is None:
            self.timeout_timer.cancel()
            self._state = "card gone"
        return ActionResult()

    @condition(["data"], [])
    @guard(lambda self, _: self._state == "check card")
    def write_card(self, incoming):
        _log.info("write_card")
        data = incoming["data"]
        if not self.rfid.write_value(self.active_type, data):
            _log.info("could not write")
            self._state = "card gone"
        else :
            _log.info("write successful")
        return ActionResult()
        # Code goes here
        
    @condition([], ["data"])
    @guard(lambda self: self._state == "card gone")
    def card_gone(self):
        _log.info("card_gone")
        result = {"status": False, "data": None, "cardno": self.active_uid_string, "timestamp": str(now())}
        self._state = "reset"
        return ActionResult(production=(result,))

    @condition()
    @guard(lambda self: self._state == "reset")
    def reset(self):
        _log.info("reset")
        self.rfid.initialize()
        self._state = "idle"
        self.timeout_timer = self['timer'].once(self.timeout)
        return ActionResult()
        
    action_priority = (reset, write_card, read_card, card_present, check_card, card_gone, is_idle, )
    requires = ["calvinsys.sensors.rfid", "calvinsys.events.timer"]
