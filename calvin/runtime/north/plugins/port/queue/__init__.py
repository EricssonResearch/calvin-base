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
            'scheduled_fifo': 'ScheduledFIFO'}
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


for module in _MODULES.keys():
    module_obj = __import__(module, globals=globals())
    globals()[module] = module_obj

def get(port, peer_port=None, peer_port_meta=None):
    #TODO implement more logic based on port and peer port properties
    if 'routing' in port.properties and ('round-robin' == port.properties['routing'] or
                                         'random' == port.properties['routing']):
        selected_queue = "scheduled_fifo"
    else:
        selected_queue = "fanout_fifo"
    try:
        class_ = getattr(globals()[selected_queue], _MODULES[selected_queue])
        return class_(port.properties)
    except:
        _log.exception("get_queue FAILED")
        return None