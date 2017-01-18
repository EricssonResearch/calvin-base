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

from calvin.actor.actor import Actor, condition, manage


class SetLimits(Actor):
    """
    SetLimits
    Inputs:
        dict: dictionary
    Outputs:
        dict: dictionary with fields "upper" and "lower" set as configured
    """

    @manage(['lower', 'upper'])
    def init(self, lower, upper):
        self.lower = lower
        self.upper = upper

    @condition(action_input=["dict"], action_output=["dict"])
    def set_limits(self, container):
        container["upper"] = self.upper
        container["lower"] = self.lower
        return (container,)

    action_priority = (set_limits, )
