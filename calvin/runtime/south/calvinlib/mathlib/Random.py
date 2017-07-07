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

from calvin.runtime.south.calvinlib import base_calvinlib_object
import random

class Random(base_calvinlib_object.BaseCalvinlibObject):
    """
    Some simple random number functions
    """

    init_schema = {
            "description": "Initialize (pseudo) RNG",
            "type": "object",
            "properties": {
                "seed": { "type": "integer" }
            }
    }

    random_integer_schema = {
        "description": "return random integer in range [lower, upper)",
        "type": "object",
        "properties": {
            "lower": { "type": "integer" },
            "upper": { "type": "integer" }
        }
        
    }
    
    random_number_schema = {
        "description": "return random number in range [lower, upper) (rounding may cause upper to be included)",
        "type": "object",
        "properties": {
            "lower": { "type": "number" },
            "upper": { "type": "number" }
        }
    }

    def init(self, seed=None):
        self.rand = random.Random()
        if seed:
            self.rand.seed(seed)
    
    def random_integer(self, lower, upper):
        return self.rand.randrange(lower, upper)

    def random_number(self, lower, upper):
        return self.rand.uniform(lower, upper)

