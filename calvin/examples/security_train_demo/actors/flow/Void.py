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

from calvin.actor.actor import Actor, manage, condition, stateguard


class Void(Actor):
    """
    Acts like a source but will never generate tokens.

    This behaviour is useful if an actor has inputs that will never be used
    in a particular application. Because of how the runtime works, all input
    ports must be connected before the application can run, so leaving a port
    unconnected is not an option.

    Outputs:
      void : A port that will never produce tokens
    """
    @manage()
    def init(self):
        pass

    @stateguard(lambda self: False)
    @condition([], ['void'])
    def null(self):
        return (0, )

    action_priority = (null, )

    test_set = [
        {
            'out': {'void': []},
        },
    ]
