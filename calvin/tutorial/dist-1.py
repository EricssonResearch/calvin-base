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

from calvin.utilities.nodecontrol import dispatch_node
from calvin.requests.request_handler import RequestHandler
import time

# Get the handler for sending the API requests
request_handler = RequestHandler()

# create one node
node_1 = dispatch_node(uri="calvinip://localhost:5000", control_uri="http://localhost:5001",
                       attributes={'indexed_public':
                            {'owner':{'organization': 'org.testexample', 'personOrGroup': 'me'},
                             'node_name': {'organization': 'org.testexample', 'name': 'node-1'}}})

# send 'new actor' command to node
counter_id = request_handler.new_actor(node_1, 'std.Counter', 'counter')

# send 'new actor' command to node
output_id = request_handler.new_actor(node_1, 'io.StandardOut', 'output')

# send 'connect' command to node
request_handler.connect(node_1, output_id, 'token', node_1.id, counter_id, 'integer')

# runt app for 3 seconds
time.sleep(3)

# send quite to node
request_handler.quit(node_1)
