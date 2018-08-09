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

from calvinextras.calvinsys.io.dht11temphumidity.BaseDHT11 import BaseDHT11
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.async import async
import pigpio

# FIXME: Allow faster operation by queing results and don't wait for readout
#        before resetting _in_progress flag?

_log = get_logger(__name__)

class DHT11(BaseDHT11):
    """
    Calvinsys object handling DHT11 temperature and humidity sensor
    The temparature readout is not used.
    """
    def init(self, pin, **kwargs):
        self._pin = pin
        self._in_progress = False
        self._humidity = None
        self._gpio = pigpio.pi()
        self._gpio.set_pull_up_down(self._pin, pigpio.PUD_OFF)
        self._gpio.set_mode(self._pin, pigpio.INPUT)
        self._read_data_handle = None
        self._edge_ticks = None
        self._listen_timeout = 1.0
        self._listen_in_progress = None
        self._humidity_last_reading = 0.0

    def can_write(self):
        return self._in_progress is False

    def write(self, measure):
        # self._in_progress = async.DelayedCall(0.0, self._read_temp)
        # 0 Switch to OUT               ___   18000   ___
        # 1. Pull down for 20ms trigger    \___ //___/
        # 2. Switch to IN               ___  80  ____
        # 3. Wait for 80us ack             \____/
        # 4. Read 40 bits               ___  50  ____________  50  ____ ....
        #    Format is                     \____/ 27=0, 70=1 \____/
        #                                  +----+------------+
        #    and stop bit               ___  50  ___ ....
        #                                  \____/
        #    (just read 41 falling edges...)
        self._in_progress = True
        self._gpio.set_mode(self._pin, pigpio.OUTPUT)
        self._gpio.write(self._pin, 0)
        async.DelayedCall(0.025, self._switch_to_listen_cb)
        self._listen_in_progress = async.DelayedCall(self._listen_timeout, self._listen_failed)

    def _switch_to_listen_cb(self):
        self._gpio.write(self._pin, 1)
        self._edge_ticks = []
        self._gpio.set_mode(self._pin, pigpio.INPUT)
        self._read_data_handle = self._gpio.callback(self._pin, pigpio.FALLING_EDGE, self._read_data_cb)

    def _listen_failed(self):
        _log.info("DHT11 read timeout, returning {}".format(self._humidity_last_reading))
        self._read_data_handle.cancel()
        self._read_data_handle = None
        self._humidity = self._humidity_last_reading
        self.scheduler_wakeup()

    def _read_data_cb(self, pin, edge, tick):
        self._edge_ticks.append(tick)
        if len(self._edge_ticks) < 41:
            return
        async.call_from_thread(self._listen_in_progress.cancel)
        self._read_data_handle.cancel()
        self._read_data_handle = None
        self._parse_ticks()

    def _parse_ticks(self):
        res = []
        t0 = self._edge_ticks.pop(0)
        for t in self._edge_ticks:
            res.append("1" if t-t0 > 99 else "0")
            t0 = t
        longbin = ''.join(res)
        rhint = int(longbin[0:8], 2)
        # rhdec = int(longbin[8:16], 2)  # Decimal part is always 0, see DHT11 docs (resolution)
        tint = int(longbin[16:24], 2)
        # tdec = int(longbin[24:32], 2)  # Decimal part is always 0, see DHT11 docs (resolution)
        chksum = int(longbin[32:40], 2)
        bytesum = rhint + tint
        # print "RH={}.{}, T={}.{}, CS={}, BS={}, OK={}".format(rhint, 0, tint, 0, chksum, bytesum, chksum == bytesum)
        self._humidity = rhint
        async.call_from_thread(self.scheduler_wakeup)

    def can_read(self):
        return self._humidity is not None

    def read(self):
        self._in_progress = False
        humidity = self._humidity
        self._humidity_last_reading = humidity
        self._humidity = None
        return humidity

    def close(self):
        if self._read_data_handle:
            self._read_data_handle.cancel()
        del self._gpio
        self._gpio = None

