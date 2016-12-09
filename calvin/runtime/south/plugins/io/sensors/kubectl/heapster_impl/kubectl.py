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

from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.plugins.async import http_client
from calvin.utilities.calvin_callback import CalvinCB
import json

_log = get_logger(__name__)


def iso8601_to_timestamp(timestring):
    import time
    import datetime
    return time.mktime(datetime.datetime.strptime(timestring, "%Y-%m-%dT%H:%M:%SZ").timetuple())
    
class KubeCtl(object):

    """
    Get some basic statistics on kubernetes cluster
    """

    def __init__(self, config):
        super(KubeCtl, self).__init__()
        self._config = config
        self._api_base = str(config["api-base"])
        if not self._api_base.endswith("/"):
            self._api_base += "/"
        self._httpclient = http_client.HTTPClient({'receive_headers' : [CalvinCB(self._receive_headers)],
                                                   'receive-body': [CalvinCB(self._receive_body)]})
        self._requests = {}
        # _log.info("new kube created")

    def identity(self):
        raise NotImplemented
    
    def connect(self, connected_cb):
        # connectionless api, just call back
        # _log.info("connecting")
        connected_cb()

    def get_metric(self, metric, result_cb):
        _log.debug("get_metric '%s'" % (metric,))
        try:
            request = self._httpclient.request("GET", url=self._api_base + "metrics/" + metric, params=None, headers={}, data=None)
            # _log.info("request\n'%s'" % (self._api_base + "/metrics/" + metric))
            request._metric_name = metric
        except Exception as e:
            _log.exception(e)
        self._requests[request] = result_cb
    
    def _receive_headers(self, request):
        # _log.info("receive headers")
        if request.status() != 200:
            result_cb = self._request.pop(request)
            result_cb(request.status(), None, None)

    def _receive_body(self, request):
        # _log.info("receive body")
        result_cb = self._requests.pop(request)
        metric = json.loads(request.body())
        # convert time string to timestamps
        for item in metric["metrics"]:
            item["timestamp"] = iso8601_to_timestamp(item["timestamp"])
            # item["timestamp"] = time.mktime(datetime.datetime.strptime(item["timestamp"], "%Y-%m-%dT%H:%M:%SZ").timetuple()) 
        result_cb(request.status(), request._metric_name, {"metrics": metric["metrics"]})
        del request
        