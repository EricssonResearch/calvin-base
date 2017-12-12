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

from calvin.actor.actor import Actor, manage, condition
from calvin.runtime.north.calvin_token import ExceptionToken
from calvin.utilities.calvinlogger import get_actor_logger


_log = get_actor_logger(__name__)


class TestProcess(Actor):
    """
    This is only intended to be used for testing.
    Perform processing on input token and send out.

    Inputs:
      data : a token
    Outputs:
      result : result of processing
    """
    @manage(['eval_str', 'replicate_str', 'kwargs', 'last', 'dump'])
    def init(self, eval_str, replicate_str=None, kwargs=None, dump=False):
        self.eval_str = eval_str
        self.replicate_str = replicate_str
        self.kwargs = {} if kwargs is None else kwargs
        self.last = None
        self.dump = dump

    @condition(['data'], ['result'])
    def process(self, data):
        try:
            res = eval(self.eval_str, {}, {"kwargs": self.kwargs, "data": data})
            if self.dump:
                _log.info("TestProcessing (%s, %s, %s) data:%s, result:%s" % (self._name, self._id, self.inports['data'].id, str(data), str(res)))
        except Exception as e:
            _log.exception("Test processing failed %s" % self.eval_str)
            res = ExceptionToken(value=str(e))
        self.last = res
        return (res, )

    def did_replicate(self, index):
        if self.replicate_str is None:
            return
        try:
            exec(self.replicate_str)
        except Exception:
            _log.exception("Test processing will_replicate failed %s" % self.replicate_str)

    def report(self, **kwargs):
        if 'cmd_str' in kwargs:
            try:
                return eval(kwargs['cmd_str'])
            except Exception as e:
                return str(e)
        return self.last

    action_priority = (process, )


