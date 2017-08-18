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

from calvin.runtime.south.plugins.io.sensors.rfid import base_rfid

import mfrc522

def get_attributes(obj, prefix):
    return { a[len(prefix):] : getattr(obj, a) for a in dir(obj)}

class RFIDHandler(base_rfid.RFIDHandlerBase):
    
    OK = getattr(mfrc522.MFRC522, 'MI_OK')
    ERROR = getattr(mfrc522.MFRC522, 'MI_ERR')

    PICC = get_attributes(mfrc522.MFRC522, 'PICC_')
    PCD = get_attributes(mfrc522.MFRC522, 'PCD_')

    DEFAULT_KEY = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
    
    def __init__(self):        
        self._reader = mfrc522.MFRC522()

    def request(self, command):
        return self._reader.MFRC522_Request(command)

    def request_idl(self):
        return self.request(RFIDHandler.PICC['REQIDL'])
        
    def anti_collision(self):
        return self._reader.MFRC522_Anticoll()

    def select_tag(self, active_uid):
        return self._reader.MFRC522_SelectTag(active_uid)
        
    def authenticate_classic(self, active_uid):
        return self._reader.MFRC522_Auth(RFIDHandler.PICC['AUTHENT1A'], 0x08,
                                         RFIDHandler.DEFAULT_KEY, active_uid)

    def _picc_type_to_block_address(self, picc_type):
        if picc_type == 8:
            # Classic
            return 0x08
        elif picc_type == 4:
            # Ultralight
            return 0x04

    def read_value(self, picc_type):
        try:
            block_address = self._picc_type_to_block_address(picc_type)            
            status, data = self._reader.MFRC522_Read(block_address)
            if status != RFIDHandler.OK :
                return status, 0
            #It worked, return result and remove request
        
            value = 0
            value += data[0] << 24
            value += data[1] << 16
            value += data[2] << 8
            value += data[3]
        except :
            return RFIDHandler.ERROR, 0
        return RFIDHandler.OK, value
        
    def write_value(self, picc_type, value):        
        block_address = self._picc_type_to_block_address(picc_type)
        data = 16 * [0]
        data[0] = value >> 24
        data[1] = value >> 16
        data[2] = value >> 8
        data[3] = value
        
        return self._reader.MFRC522_Write(block_address, data)

    def initialize(self):
        return self._reader.MFRC522_Init()
        
