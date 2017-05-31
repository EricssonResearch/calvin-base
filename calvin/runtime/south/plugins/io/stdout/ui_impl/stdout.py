# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
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

from calvin.runtime.south.plugins.io.stdout import base_stdout
import calvin.runtime.south.plugins.ui.uicalvinsys as ui


class StandardOut(base_stdout.BaseStandardOut):

    """
        Virtual console
    """
    def __init__(self, node, actor, config):
        super(StandardOut, self).__init__(node, actor, config)
        ui_def = {"image":"Console", "control":{"sensor":False, "type":"console"}}
        ui.register_actuator(actor, ui_def=ui_def)

    def write(self, text):
        ui.update_ui(self._actor, text)

    def writeln(self, text):
        self.write(text +  "\n")


