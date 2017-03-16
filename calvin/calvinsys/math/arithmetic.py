# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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

import operator
from calvin.utilities.calvinlogger import get_logger


_log = get_logger(__name__)


class Arithmetic(object):

    def operation(self, op):
        try:
            return {
                '+': operator.add,
                '-': operator.sub,
                '*': operator.mul,
                '/': operator.div,
                'div': operator.floordiv,
                'mod': operator.mod,
            }[op]
        except KeyError:
            _log.warning('Invalid operator %s, will always produce NULL as result' % str(op))
            return lambda x,y: None

def register(node=None, actor=None):
    return Arithmetic()
