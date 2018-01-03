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

from calvin.runtime.south.calvinlib import base_calvinlib_object
import pystache


class Pystache(base_calvinlib_object.BaseCalvinlibObject):
    """
    Module for formatting strings using Mustache-style templates.
    """

    render_schema = {
        "description": "Return template string rendered using given dictionary",
        "type": "object",
        "properties": {
            "template": {"type": "string"},
            "dictionary": {"type": "dict"}
        }
    }

    def init(self):
        pass

    def render(self, template, dictionary):
        return pystache.render(template, **dictionary)
