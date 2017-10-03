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

from calvin.runtime.south.plugins.io.sensors.distance import base_distance
from calvin.runtime.south.plugins.async import async, threads
from calvin.runtime.south.plugins.io.gpio import gpiopin
from time import sleep, time

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class Distance(base_distance.DistanceBase):

    """
        SR04 Ultrasonic distance sensor
    """
    def __init__(self, node, actor, data_callback):
        super(Distance, self).__init__(node, actor, data_callback)
        self._running = False
        self.distance = None
        self._node = node
        self._new_measurement = data_callback
        self.t_0 = time()
        self.retry = None

        config = self._node.attributes.get_private("/hardware/sr04_ultrasonic")
        trig_pin = config.get('trig_pin', None)
        echo_pin = config.get('echo_pin', None)
        self._period = None

        self.trig_pin = gpiopin.GPIOPin(None, trig_pin, "o", None)
        self.echo_pin = gpiopin.GPIOPin(self._echo_callback, echo_pin, "i", None)

    def start(self, period=2):
        self._period = period
        try :
            self.echo_pin.detect_edge("f")
            self._running = True
            # gpio.add_event_detect(self.echo_pin,
            #                      gpio.FALLING,
            #                      callback=self._echo_callback)
        except Exception as e:
            _log.error("Could not setup event detect: %r" % (e, ))

        # Start measuring
        self._next_measurement()

    def cb_error(self, *args, **kwargs):
        _log.error("%r: %r" % (args, kwargs))


    def _setup_next(self):
        if self.retry and self.retry.active():
            # retry in progress, skip
            return
        self.retry = async.DelayedCall(self._period, self._next_measurement)

    def _next_measurement(self):
        # self.in_progress = async.DelayedCall(self._delay, self._measure)
        self.in_progress = threads.defer_to_thread(self._measure)
        self.in_progress.addErrback(self.cb_error)

    def _measure(self):
        self.trig_pin.set_state(1)
        # gpio.output(self.trig_pin, 1)
        sleep(0.00001)
        self.t_0 = time()
        # gpio.output(self.trig_pin, 0)
        self.trig_pin.set_state(0)

    def _echo_callback(self):
        t_1 = time()
        # Round to nearest 10 cm, convert to m
        self.distance = (t_1 - self.t_0)*17150 # cm, w/ decimals
        self.distance = round(self.distance/10.0, 0)*10.0 # cm, nearest 10
        self.distance = self.distance / 100.0 # m
        async.call_from_thread(self._new_measurement, self.distance)
        async.call_from_thread(self._setup_next)


    def stop(self):
        if self._running :
            if self.retry and self.retry.iactive() :
                self.retry.cancel()
            try:
                self.echo_pin.stop_detect()
                # gpio.remove_event_detect(self.echo_pin)
            except Exception as e:
                _log.warning("Could not remove event detect: %r" % (e,))
            self._running = False
        # gpio.cleanup()
