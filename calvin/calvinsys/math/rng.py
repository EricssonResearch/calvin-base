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

from calvin.runtime.north.calvin_token import ExceptionToken
import random


# cannot use random as filename - sometimes python is just plain silly.

class Random(object):

    def randrange(self, lower, upper):
        try:
            return random.randrange(lower, upper)
        except Exception as e:
            return ExceptionToken(str(e))
    
    def uniform(self, lower, upper):
        try:
            return random.uniform(lower, upper)
        except Exception as e:
            return ExceptionToken(str(e))

def register(node=None, actor=None):
    return Random()
