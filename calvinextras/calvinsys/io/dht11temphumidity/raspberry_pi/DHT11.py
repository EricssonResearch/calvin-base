# i*- coding: utf-8 -*-

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
from calvin.runtime.south.async import async as async_impl  # noqa: W606
import pigpio

_log = get_logger(__name__)


class SensorReader(object):

    def __init__(self, pin, ready_callback):
        super(SensorReader, self).__init__()
        self._references = {"humidity": 0, "temperature": 0}
        self._callback = ready_callback

        # Current read (or previous read if read failed)
        self._value = {"humidity": None, "temperature": None}

        self._listen_in_progress = None

        self._pin = pin
        self._gpio = pigpio.pi()
        self._gpio.set_pull_up_down(self._pin, pigpio.PUD_OFF)
        self._gpio.set_mode(self._pin, pigpio.INPUT)
        self._read_data_handle = None
        self._edge_ticks = None

        # Multiple sources report a max frequency of 1Hz for DHT11 readings.
        # We set it to update the reading every second and let the actor
        # decide the frequency with which the value is actually read.
        self._update_interval = 1.0
        self._listen_timeout = 1.0

    def value_ready(self, mode):
        return self._value[mode] is not None

    def get_value(self, mode):
        return self._value[mode]

    def start(self):
        self._running = True
        self._measure()

    def stop(self):
        # Will likely report one more measurement before stopping
        self._running = False

    def _measure(self):
        # self._in_progress = async_impl.DelayedCall(0.0, self._read_temp)
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
        if not self._running:
            _log.info("Stopping measurement readings")
            return
        self._gpio.set_mode(self._pin, pigpio.OUTPUT)
        self._gpio.write(self._pin, 0)
        self._listen_in_progress = async_impl.DelayedCall(self._listen_timeout, self._listen_failed)
        async_impl.DelayedCall(0.025, self._switch_to_listen_cb)

    def _switch_to_listen_cb(self):
        self._gpio.write(self._pin, 1)
        self._edge_ticks = []
        self._gpio.set_mode(self._pin, pigpio.INPUT)
        self._read_data_handle = self._gpio.callback(self._pin, pigpio.FALLING_EDGE, self._read_data_cb)

    def _listen_failed(self):
        _log.info("DHT11 read timeout, using old values: {}".format(self._value))
        self._read_data_handle.cancel()
        self._read_data_handle = None
        self._listen_in_progress = None
        self._callback()
        async_impl.DelayedCall(self._update_interval, self._measure)

    def _read_data_cb(self, pin, edge, tick):
        self._edge_ticks.append(tick)
        if len(self._edge_ticks) < 41:
            return
        async_impl.call_from_thread(self._listen_in_progress.cancel)
        self._read_data_handle.cancel()
        self._read_data_handle = None
        self._parse_ticks()

    def _parse_ticks(self):
        global sensor_readings
        res = []
        t0 = self._edge_ticks.pop(0)
        for t in self._edge_ticks:
            res.append("1" if t - t0 > 99 else "0")
            t0 = t
        longbin = ''.join(res)
        rhint = int(longbin[0:8], 2)
        # rhdec = int(longbin[8:16], 2)  # Decimal part is always 0, see DHT11 docs (resolution)
        tint = int(longbin[16:24], 2)
        # tdec = int(longbin[24:32], 2)  # Decimal part is always 0, see DHT11 docs (resolution)
        chksum = int(longbin[32:40], 2)
        bytesum = rhint + tint

        _log.debug("RH={}.{}, T={}.{}, CS={}, BS={}, OK={}".format(rhint, 0, tint, 0, chksum,
                                                                   bytesum, chksum == bytesum))

        if chksum != bytesum:
            _log.info("Error in checksum, ignoring read {} / {}".format(rhint, tint))
        else:
            self._value = {"temperature": tint, "humidity": rhint}

        self._listen_in_progress = None
        async_impl.call_from_thread(self._callback)
        async_impl.call_from_thread(async_impl.DelayedCall, self._update_interval, self._measure)

    def ref(self, mode):
        self._references[mode] += 1
        return self

    def unref(self, mode):
        self._references[mode] -= 1
        return sum(self._references.values())


_sensor_reader = None


def ref_sensor_reader(pin, ready_callback, mode):
    global _sensor_reader
    if _sensor_reader is None:
        _log.info("Init sensor reading")
        _sensor_reader = SensorReader(pin, ready_callback)
        _sensor_reader.start()
    return _sensor_reader.ref(mode)


def unref_sensor_reader(mode):
    global _sensor_reader
    if _sensor_reader.unref(mode) == 0:
        _log.info("No more references to sensor reader, finalizing")
        _sensor_reader.stop()
        _sensor_reader = None


class DHT11(BaseDHT11):
    """
    Calvinsys object handling DHT11 temperature and humidity sensor

    Implements resource sharing using a primitive reference counting
    """
    def init(self, pin, mode="humidity", **kwargs):
        _log.info("Setting up {} sensor".format(mode))
        self._sensor = ref_sensor_reader(pin, self.scheduler_wakeup, mode)
        self._mode = mode
        self._next_value = None

    def can_write(self):
        return self._sensor.value_ready(self._mode)

    def write(self, _):
        self._next_value = self._sensor.get_value(self._mode)

    def can_read(self):
        return self._next_value is not None

    def read(self):
        val = self._next_value
        self._next_value = None
        return val

    def close(self):
        unref_sensor_reader(self._mode)
