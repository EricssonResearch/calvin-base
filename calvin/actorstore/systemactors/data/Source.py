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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class Source(Actor):
    """
    Data source.
    {
        "id": "ns=2;s=/Channel/Parameter/rpa[u1,115]",
        "tag": "R115",
        "type": "Double",
        "value": 0.0,
        "serverts": "2017-03-20 15:42:41.600000",
        "sourcets": "2017-03-20 15:42:41.542000",
        "calvints": 1490021096110,
        "status": 0
        "info": "description given for parameter"
    }
    Output:
        parameter : description of parameter as shown above
    """

    @manage([])
    def init(self, tags=None):
        if isinstance(tags, basestring):
            tags = [tags]
        self.source= calvinsys.open(self, "data.source", tags=tags)

    @stateguard(lambda self: calvinsys.can_read(self.source))
    @condition([], ["parameter"])
    def send_data(self):
        param = calvinsys.read(self.source)
        return (param, )

    action_priority = (send_data,)
    requires = ['data.source']

