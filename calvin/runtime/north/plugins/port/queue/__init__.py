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

# Queues
_MODULES = {'fanout_fifo': 'FanoutFIFO',
            'collect_unordered': 'CollectUnordered',
            'collect_tagged': "CollectTagged",
            'collect_synced': 'CollectSynced',
            'collect_any': 'CollectAny',
            'fanout_ordered_fifo': 'FanoutOrderedFIFO',
            'fanout_round_robin_fifo': "FanoutRoundRobinFIFO",
            'fanout_random_fifo': "FanoutRandomFIFO",
            'fanout_balanced_fifo': "FanoutBalancedFIFO",
            'fanout_mapped_fifo': 'FanoutMappedFIFO'}

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


for module in _MODULES.keys():
    module_obj = __import__(module, globals=globals())
    globals()[module] = module_obj

def get(port, peer_port=None, peer_port_meta=None):
    #TODO implement more logic based on port and peer port properties

    if 'routing' in port.properties:
        routing_prop = port.properties['routing']
        if isinstance(routing_prop, (tuple, list)):
            routing_prop = routing_prop[0]
        
        if 'round-robin' == routing_prop:
            selected_queue = "fanout_round_robin_fifo"
        elif 'random' == routing_prop:
            selected_queue = "fanout_random_fifo"
        elif 'dispatch-ordered' == routing_prop:
            selected_queue = 'fanout_ordered_fifo'
        elif 'dispatch-mapped' == routing_prop:
            selected_queue = 'fanout_mapped_fifo'
        elif 'balanced' == routing_prop:
            selected_queue = "fanout_balanced_fifo"
        elif routing_prop == 'collect-unordered':
            selected_queue = "collect_unordered"
        elif routing_prop == 'collect-tagged':
            selected_queue = 'collect_tagged' 
        elif routing_prop == 'collect-all-tagged':
            selected_queue = "collect_synced"
        elif routing_prop == 'collect-any-tagged':
            selected_queue = "collect_any"
        else:
            selected_queue = "fanout_fifo"
    try:
        class_ = getattr(globals()[selected_queue], _MODULES[selected_queue])
        peer_port_properties = {}
        if peer_port is not None:
            peer_port_properties = peer_port.properties
        if peer_port_meta is not None and not peer_port_properties:
            peer_port_properties = peer_port_meta.properties
        return class_(port.properties, peer_port_properties=peer_port_properties)
    except:
        _log.exception("get_queue FAILED")
        return None