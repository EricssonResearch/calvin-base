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

# create two nodes, named node-1 and node-2, respectively
node_1 = dispatch_node(uri="calvinip://localhost:5000", control_uri="http://localhost:5001",
                       attributes={'indexed_public':
                            {'owner':{'organization': 'org.testexample', 'personOrGroup': 'me'},
                             'node_name': {'organization': 'org.testexample', 'name': 'node-1'}}})
node_2 = dispatch_node(uri="calvinip://localhost:5002", control_uri="http://localhost:5003",
                       attributes={'indexed_public':
                            {'owner':{'organization': 'org.testexample', 'personOrGroup': 'me'},
                             'node_name': {'organization': 'org.testexample', 'name': 'node-2'}}})

# send 'new actor' command to node_2
counter_id = request_handler.new_actor(node_2, 'std.Counter', 'counter')

# send 'new actor' command to node_1
output_id = request_handler.new_actor(node_1, 'io.StandardOut', 'output')

# inform node_1 about peers
request_handler.peer_setup(node_1, ["calvinip://localhost:5002"])

# allow network to stabilize
time.sleep(1.0)

# send connect command to node_1
request_handler.connect(node_1, output_id, 'token', node_2.id, counter_id, 'integer')

# run app for 3 seconds
time.sleep(3.0)

# send quit to nodes
request_handler.quit(node_1)
request_handler.quit(node_2)
