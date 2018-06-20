# -*- coding: utf-8 -*-

# Copyright (c) 2018 Ericsson AB
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

import json
from calvin.requests import calvinresponse
import calvin.runtime.south.plugins.ui.uicalvinsys as ui
from routes import handler

@handler(method="GET", path="/uicalvinsys/{uuid}")
def handle_get_uicalvinsys(self, handle, connection, match, data, hdr):
    """
    GET /uicalvinsys/<uuid>
    Get UI definitions
    Response status code: UI definitions
    """
    self.send_response(handle, connection, json.dumps(ui.ui_definitions()), status=calvinresponse.OK)

@handler(method="POST", path="/uicalvinsys")
def handle_post_uicalvinsys(self, handle, connection, match, data, hdr):
    """
    POST /uicalvinsys
    Update UICalvinSys state
    Body:
    {
        "actor_id" : <actor_id>
        "state": value
    }
    Response status code: OK or BAD_REQUEST
    """
    status = ui.update(data)
    self.send_response(handle, connection, None, status=calvinresponse.OK)

