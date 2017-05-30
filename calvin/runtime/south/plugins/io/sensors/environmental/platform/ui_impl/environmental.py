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

from calvin.runtime.south.plugins.io.sensors.environmental import base_environmental
import calvin.runtime.south.plugins.ui.uicalvinsys as ui


class Environmental(base_environmental.EnvironmentalBase):
    """
    UI implementation of Environmental temperature
    """
    def __init__(self, node, actor):
        super(Environmental, self).__init__(node, actor)
        ui_def = {"image":"KY-013", "control":{"sensor":True, "type":"float", "min":-20.0, "max":80.0, "default":20.0}}
        ui.register_sensor(actor, None, ui_def=ui_def)

    def get_temperature(self):
        return ui.sensor_state(self._actor)
