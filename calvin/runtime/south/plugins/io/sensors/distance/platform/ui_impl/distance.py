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
from calvin.runtime.south.plugins.async import async
import calvin.runtime.south.plugins.ui.uicalvinsys as ui


class Distance(base_distance.DistanceBase):

    """
        Virtual distance sensor
    """
    def __init__(self, node, actor, data_callback):
        super(Distance, self).__init__(node, actor, data_callback)
        self.periodic = None
        ui_def = {"image":"Distance", "control":{"sensor":True,  "type":"float", "min":0.0, "max":4.0, "default":4.0}}
        # Don't register this as a callback sensor since we use periodic callbacks
        ui.register_sensor(actor, None, ui_def=ui_def)

    def _periodic_callback(self):
        value = ui.sensor_state(self._actor)
        self._new_measurement(value)
        # Reload timer
        self.periodic = async.DelayedCall(self.delay, self._periodic_callback)

    def start(self, period):
        # Args: delay, dc_callback, *args, **kwargs
        try:
            self.delay = period
        except ZeroDivisionError:
            self.delay = 1.0
        self.periodic = async.DelayedCall(self.delay, self._periodic_callback)

    def stop(self):
        if self.periodic is None:
            return
        self.periodic.cancel()
