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

from calvin.runtime.south.plugins.io.sensors.rfid import rfid
   
class RFIDHandler(object):

    def __init__(self, node, actor):
        self._node = node
        self._actor = actor
        self._rfidhandler = rfid.RFIDHandler()
        self._has_data = False
        
    def uid_to_string(self, uid):
        return "".join( format(u, "02x") for u in uid[:5])
    
    def string_to_uid(self, uid_string):
        return bytearray.fromhex(uid_string)

    def request_idl(self):
        status, _ = self._rfidhandler.request_idl()
        return status == rfid.RFIDHandler.OK
        
    def anti_collision(self):
        status, uid = self._rfidhandler.anti_collision()
        if status == rfid.RFIDHandler.OK :
            return uid
        else :
            return None
            
    def card_type(self, active_type):
        if active_type == 0x08 :
            return "classic"
        elif active_type == 0x04:
            return "ultralight"
        else:
            return "unknown"
            
    def select_tag(self, uid):
        return self._rfidhandler.select_tag(uid)
        
    def authenticate_classic(self, uid):
        status = self._rfidhandler.authenticate_classic(uid)
        return status == rfid.RFIDHandler.OK
        
    def read_value(self, active_type):
        status, value = self._rfidhandler.read_value(active_type)
        if status == rfid.RFIDHandler.OK:
            return value
        else :
            return None
        
    def write_value(self, active_type, value):
        return rfid.RFIDHandler.OK == self._rfidhandler.write_value(active_type, value)
        
    def initialize(self):
        return self._rfidhandler.initialize()
        
def register(node=None, actor=None):
    return RFIDHandler(node, actor)
