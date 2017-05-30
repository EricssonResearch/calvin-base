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
import calvin.runtime.south.plugins.ui.uicalvinsys as ui


class Distance(base_distance.DistanceBase):

    """
        Virtual distance sensor
    """
    def __init__(self, node, actor, data_callback):
        super(Distance, self).__init__(node, actor, data_callback)
        ui_def = {"image":"Distance", "controls":[{"sensor":True,  "type":"float", "min":0.0, "max":4.0}]}
        ui.register_sensor(actor, data_callback, ui_def=ui_def)

    def start(self, frequency):
        pass

    def stop(self):
        pass
