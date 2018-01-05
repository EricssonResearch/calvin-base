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

from calvin.actor.actor import Actor, stateguard, condition, calvinsys, calvinlib
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class RFIDReader(Actor):

    """
    RFIDReader - read MIFare Classic/ultralight when present.

    Outputs:
        data : {"cardno": uid, "data": <data>, "timestamp": <timestamp>}
    """


    def init(self):
        self.time = calvinlib.use('time')
        self.rfid = calvinsys.open(self, "io.rfid")

    @stateguard(lambda actor: calvinsys.can_read(actor.rfid))
    @condition([], ["data"])
    def read_card(self):
        result = calvinsys.read(self.rfid)
        result['timestamp'] = self.time.timestamp()
        return (result,)

    action_priority = (read_card,)

    requires = ['time', 'io.rfid']


#    TBD: Reenable test after updating to use new calvinsys API
#    test_set = [
#        {
#            'inputs': {'data': []},
#            'outports': {'data': []}
#        }
#    ]
