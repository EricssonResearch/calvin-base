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

import time

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


# FIXME: Fold into scehduler?
class Event_Monitor(object):

    def __init__(self):
        super(Event_Monitor, self).__init__()
        """docstring for __init__"""

        self.endpoints = []
        self._backoff = {}

    def set_backoff(self, endpoint):
        _, bo = self._backoff.get(endpoint, (0, 0))
        bo = min(1.0, 0.1 if bo < 0.1 else bo * 2.0)
        self._backoff[endpoint] = (time.time() + bo, bo)

    def clear_backoff(self, endpoint):
        self._backoff.pop(endpoint, None)

    def next_slot(self):
        if self._backoff:
            val = min(self._backoff.values(), key=lambda x : x[0])
            return val[0]
        return None

    def _check_backoff(self):
        current = time.time()
        for ep in self._backoff.keys():
            tc = self._backoff[ep][0]
            if tc < current:
                self.clear_backoff(ep)

    def register_endpoint(self, endpoint):
        self.endpoints.append(endpoint)

    def unregister_endpoint(self, endpoint):
        self.endpoints.remove(endpoint)
        self.clear_backoff(endpoint)

    # FIXME: supply a list of endpoints
    def communicate(self, endpoints):
        """Communicate over all endpoints, return True if at least one send something."""
        # Update the backoff dictionary containing endpoints that should NOT communicate.
        self._check_backoff()
        did_comm = False
        # Loop over supplied endpoints, skip those in backoff dictionary
        for endp in endpoints:
            if not endp in self._backoff:
                did_comm |= endp.communicate()

        return did_comm

class VisualizingMonitor(Event_Monitor):
    
    def communicate(self, endpoints):
        
        # Helper function
        def visualize(ports):
            for port in ports:
                actor = port.owner
                queue = port.queue
                wp = queue.write_pos if type(queue.write_pos) is int else max(queue.write_pos.values())
                try:
                    rp = queue.read_pos if type(queue.read_pos) is int else min(queue.read_pos.values())
                except:
                    # Might not have a read pos yet
                    rp = 0
                n = wp - rp
                _log.debug("    {}.{} {}".format(actor.name, port.name, n))

        # Grab all ports
        outports = [e.port for e in endpoints]
        inports = [e.peer_port for p in outports for e in p.endpoints if hasattr(e, 'peer_port')]        
        ports = outports + inports
        _log.debug("------------------------")
        _log.debug("Before commmunicate")
        visualize(ports)
        # Call the actual communication method        
        super(VisualizingMonitor, self).communicate(endpoints)
        _log.debug("After communicate")
        visualize(ports)
        _log.debug("------------------------")
