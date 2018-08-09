# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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

from calvinextras.calvinsys.io.rfid.BaseRFID import BaseRFID
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.async import async

import MFRC522

_log = get_logger(__name__)

class PIGPIORFID(BaseRFID):
    """
    Calvinsys object handling RFID device
    """
    def init(self, **kwargs):
        self.reader = MFRC522.MFRC522(callback=self._readout_cb)
        self.has_readout = False
        self.reader.MFRC522_DetectCard()

    def _readout_cb(self):
        self.has_readout = True
        self.scheduler_wakeup()

    def can_read(self):
        return self.has_readout

    def read(self):
        self.has_readout = False
        card = {"cardno":self.reader.uid, "data":self.reader.readout}
        self.reader.MFRC522_DetectCard()
        return card

    def close(self):
        pass

