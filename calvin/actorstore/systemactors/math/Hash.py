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

from calvin.actor.actor import Actor, manage, condition, calvinlib
from calvin.utilities.calvinlogger import get_actor_logger
from calvin.runtime.north.calvin_token import ExceptionToken


_log = get_actor_logger(__name__)


class Hash(Actor):
    """
    documentation:
    - Produce a hash hex-digest of input string.
    - Allowed values for algorithm are at least 'sha1', 'sha224', 'sha384', 'sha256',
      'sha512', 'md5'
    ports:
    - direction: in
      help: a string
      name: string
    - direction: out
      help: hex-digest of input string
      name: result
    requires:
    - math.hash
    """
    @manage(['algorithm'])
    def init(self, algorithm):
        self.algorithm = algorithm
        self.setup()

    def setup(self):
        self.hash = calvinlib.use("math.hash")

    def did_migrate(self):
        self.setup()

    @condition(['string'], ['result'])
    def compute(self, string):
        try:
            alg = self.hash.new(self.algorithm)
            alg.update(string)
            res = alg.hexdigest()
        except Exception as e:
            res = ExceptionToken(str(e))
        return (res, )

    action_priority = (compute, )
    

    test_args = ['md5']
    test_set = [
        {
            'inports': {'string': ["dfgdfgdfsdfsdfsdfsdfsdfg", "d"]},
            'outports': {'result': ['178d6e19d06e0d255709bc2bb25994b7', '8277e0910d750195b448797616e091ad']},
        },
    ]
