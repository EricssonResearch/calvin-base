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

from calvin.runtime.south.plugins.async import async
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.plugins.io.sensors.kubectl import kubectl

_log = get_logger(__name__)


class KubeCtl(object):
    """
        A calvinsys module for getting statistics from kubectl 
    """
    
    INTERVAL = 10.0 # Interval to use in fetching data

    def __init__(self, node, actor):
        _log.info("new kube")
        self._node = node
        self._actor = actor
        self._metrics = {}
        self._active_metrics= {}
        
        if self._node.attributes.has_private_attribute("/io/sensor/kubectl"):
            # Use runtime specific kubectl configuration
            config = self._node.attributes.get_private("/io/sensor/kubectl")
        else :
            config = None
        
        self.kubectl = kubectl.KubeCtl(config)

    def _trigger(self):
        _log.info("trigger")
        self._node.sched.trigger_loop(actor_ids=[self._actor])

    def has_metric(self, metric):
        return self._metrics[metric] is not None

    def get_metric(self, metric):
        _log.debug("fetching metric '%s" % (metric,))
        assert self._metrics[metric] is not None
        return self._metrics[metric]

    def ack_metric(self, metric, immediately=False):
        _log.debug("acking metric '%s'" % (metric,))
        self._metrics[metric] = None
        self._active_metrics[metric] = async.DelayedCall(self.INTERVAL if not immediately else 0, self.kubectl.get_metric, metric, self._receive_metric)

    def _receive_metric(self, status, metric, result):
        _log.debug("receiving metric '%s' w/ status %s" % (metric, status))
        if status == 200:
            self._metrics[metric] = result
        else:
            _log.warning("Error reading '%s' metric" % (metric,))
        self._trigger()

    def _enabled_cb(self):
        _log.info("metrics enabled: '%r'" % (self._metrics,))
        for metric in self._metrics:
            if not self._active_metrics.get(metric):
                self.ack_metric(metric, immediately=True)
        self._trigger()
   
    def enable(self, metric):
        _log.info("enabling metric '%s'" % (metric))
        self._metrics[metric] = None
        self.kubectl.connect(self._enabled_cb)

    def disable(self, metric=None):
        if not metric:
            # disable all
            for metric in self._metrics:
                self._active_metrics[metric].cancel()
            self.enclosure.disconnect()
        else :
            self._active_metrics[metric].cancel()
            


def register(node, actor):
    return KubeCtl(node, actor)
