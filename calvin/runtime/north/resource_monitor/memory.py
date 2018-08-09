# -*- coding: utf-8 -*-

from calvin.runtime.south.async import async
from calvin.runtime.north.resource_monitor.helper import ResourceMonitorHelper
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class MemMonitor(object):
    def __init__(self, node_id, storage):
        self.storage = storage
        self.node_id = node_id
        self.acceptable_avail = [0, 25, 50, 75, 100]
        self.helper = ResourceMonitorHelper(node_id, storage)

    def set_avail(self, avail, cb=None):
        """
        Sets the RAM availability of a node.
        Acceptable range: [0, 25, 50, 75, 100]
        """
        if avail not in self.acceptable_avail:
            _log.error("Invalid RAM avail value: " + str(avail))
            if cb:
                async.DelayedCall(0, cb, avail, False)
            return

        self.helper.set("nodeMemAvail-", "memAvail", avail, cb)

    def stop(self):
        """
        Stops monitoring, cleaning storage
        """
        # get old value to cleanup indexes
        self.helper.set("nodeMemAvail-", "memAvail", value=None, cb=None)
        self.storage.delete(prefix="nodeMemAvail-", key=self.node_id, cb=None)
