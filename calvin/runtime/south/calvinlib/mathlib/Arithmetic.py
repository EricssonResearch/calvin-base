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
from calvin.utilities.calvinlogger import get_logger
import operator

_log = get_logger(__name__)


class Arithmetic(base_calvinlib_object.BaseCalvinlibObject):

    """
    Operations on numbers 
    """

    init_schema = {
            "description": "Initialize module",
    }

    relation_schema = {
        "description": "Get corresponding relation: >, <, =, !=, >=, <= (with obvious interpretation.)",
        "type": "object",
        "properties": {
            "rel": { "type": "string" }
        }
        
    }

    operator_schema = {
        "description": "Get corresponding operator: +, -, /, *, div, mod (with obvious interpretation.)",
        "type": "object",
        "properties": {
            "op": { "type": "string" }
        }
    }

    eval_schema = {
        "description": "Evaluate expression, returning result. Bindings should be a dictionary of variable mappings to use in evaluation",
        "type": "object",
        "properties": {
            "expr": { "type": "string" },
            "bindings": { "type": "object" }
        }
    }

    def init(self):
        pass
    
    def relation(self, rel):
        try:
            return {
                        '<': operator.lt,
                        '<=': operator.le,
                        '=': operator.eq,
                        '!=': operator.ne,
                        '>=': operator.ge,
                        '>': operator.gt,
                    }[rel]
        except KeyError:
            _log.warning("Invalid operator '{}', will always return 'false'".format(rel))
            return lambda x,y: False

    def operator(self, op):
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
            _log.warning("Invalid operator '{}', will always produce 'null'".format(op))
            return lambda x,y: None
        
    def eval(self, expr, bindings):
        try:
            return eval(expr, {}, bindings)
        except Exception as e:
            return str(e)