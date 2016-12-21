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

from calvin.runtime.south.plugins.io.sensors.enclosure import base_enclosure
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.plugins.async import threads

import paramiko
import re

_log = get_logger(__name__)


class Enclosure(base_enclosure.BaseEnclosure):

    """
    Onboard Administrator based enclosure readings
    """

    def __init__(self, config):
        super(Enclosure, self).__init__(config)
        self.username = self.config.get('oa_username', None)
        self.password = self.config.get('oa_password', None)
        self.address = self.config.get('oa_address', None)
        self.num_fans = self.config.get('oa_fans', 10)
        self.num_power_supplies = self.config.get('oa_power_supplies', 6)
        self.num_severs = self.config.get('oa_servers', 16)
        self.client = None
        self.num_clients = 0
        self.connected = False
        
        if self.address is None:
            _log.error("No address given, cannot start Enclosure plugin")
            raise Exception("Open Administrator plugin requires address")
            
        if self.username is None or self.password is None:
            _log.error("No username or password supplied, cannot start Enclosure plugin")
            raise Exception("Open Administrator plugin requires username and password")

    def identity(self):
        return self.address
        
    def _connect(self, connected_cb):
        if not self.connected:
            self.client = paramiko.SSHClient()
            self.client.load_system_host_keys()
            self.client.connect(hostname=self.address, username=self.username, password=self.password)
            self.connected = True
            self.num_clients = 1
        else :
            self.num_clients += 1
        connected_cb()
    
    def connect(self, connected_cb):
        threads.defer_to_thread(self._connect, connected_cb)
        
    def _disconnect(self):
        if self.connected:
            self.num_clients -= 1
        if self.num_clients == 0:
            self.client.close()
            self.connected = False
    
    def _get_fan_cpu_data(self, things, thing_type, thing_marker):
        sin, sout, serr = self.client.exec_command("SHOW ENCLOSURE %s ALL" % (thing_type,))
        errors = [ line for line in serr ]
        if errors:
            raise "".join(errors)

        data = {}
        for line in sout:
            if line.startswith("%s #" % (thing_marker,)):
                # found new thing
                current = int(re.findall(r'\d+', line)[0])
                data[current] = {}
            else:
                l = line.strip()
                if ':' in l:
                    key, value = l.split(':')
                    key, value = key.strip(), value.strip()
                    data[current][key] = value
                else:
                    pass  # junk or diagnostics data

        return {key:value for key, value in data.items() if key in things}
        
    def _get_fan_data(self, fans):
        return self._get_fan_cpu_data(fans, "FANS", "Fan")
    
    def _get_power_supply_data(self, supplies):
        return self._get_fan_cpu_data(supplies, "POWERSUPPLY", "Power Supply")
        
    def _get_full_fan_info(self, fans, result_cb):
        result = self._get_fan_data(fans)
        result_cb(result)
    
    def _get_fan_speed_rpm(self, fans, result_cb):
        result = self._get_fan_data(fans)
        speeds = {}
        for fan, data in result.items():
            percentage = data['Speed'].split(' ')[0]  # should be percentage of max speed
            percentage = int(percentage)/100.0
            maxrpm = int(data['Maximum speed'])
            speeds["Fan-%d" % (fan,)] = int(percentage*maxrpm)
        result_cb(speeds)

    def _get_fan_speed_percent(self, fans, result_cb):
        result = self._get_fan_data(fans)
        speeds = {}
        for fan, data in result.items():
            percentage = data['Speed'].split(' ')[0]  # should be percentage of max speed
            speeds[fan] = int(percentage)
        result_cb(speeds)
    
    def _get_power_usage(self, supplies, result_cb):
        result = self._get_power_supply_data(supplies)
        usage = {}
        for supply, data in result.items():
            output = data["Current Power Output"]
            usage["PSU-%d" % (supply,)] = int(re.findall(r'\d+', output)[0])
        result_cb(usage)

    def get_fan_speed(self, fans, result_cb):
        threads.defer_to_thread(self._get_fan_speed_rpm, fans, result_cb)
    
    def get_power_usage(self, supplies, result_cb):
        threads.defer_to_thread(self._get_power_usage, supplies, result_cb)
        
    def get_full_fan_info(self, fans, result_cb):
        threads.defer_to_thread(self._get_full_fan_info, fans, result_cb)

    def _parse_server_data(self, data):
        data = data[3:13]
        result = {}
        for line in data:
            l = line.split()
            zone = l[0].lower()
            result[zone] = result.setdefault(zone, 0) + int(l[3].split("C")[0])

        result["system"] /= 3.0
        result["memory"] /= 3.0
        result["cpu"] /= 2.0
        return result

    def _split_server_data(self, data):
        servers = {}
        idx = 7
        s = 0
        while idx < len(data) and s < 16:
            servers[s] = data[idx:idx+17]
            s += 1
            idx += 16
        return servers

    def _get_cpu_temps(self, servers, result_cb):
        sin, sout, serr = self.client.exec_command("SHOW SERVER TEMP ALL")
        errors = [line for line in serr]
        if errors:
            raise "".join(errors)
        data = [line.strip() for line in sout if line]
        server_data = self._split_server_data(data)
        servers_temps = {}
        for i in server_data:
            servers_temps[i+1] = self._parse_server_data(server_data[i])
        result = {"server-%02d" % (s,): servers_temps[s]["cpu"] for s in servers_temps if s in servers }
        result_cb(result)

    def get_cpu_temps(self, servers, result_cb):
        threads.defer_to_thread(self._get_cpu_temps, servers, result_cb)
        
    def _get_ambient_temp(self, result_cb):
        sin, sout, serr = self.client.exec_command("SHOW SERVER TEMP 1")
        errors = [line for line in serr]
        if errors:
            raise "".join(errors)
        result = [line.strip() for line in sout if line]
        ambient_temp = self._parse_server_data(result[7:])["ambient"]
        result_cb(ambient_temp)

    def get_ambient_temp(self, result_cb):
        threads.defer_to_thread(self._get_ambient_temp, result_cb)
