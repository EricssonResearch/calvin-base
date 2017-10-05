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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys
from calvin.utilities.calvinlogger import get_actor_logger

_log = get_actor_logger(__name__)


class RegistryAttribute(Actor):
    """
    Fetch given registry attribute of runtime given as a section.subsection.subsubsection. Will only work for locally known attributes.

    Input:
        trigger: Any token will trigger a read
    Output:
      value : The given attribute of this runtime, or null
    """

    @manage(["attribute", "registry"])
    def init(self, attribute):
        self.attribute = attribute
        self.registry = calvinsys.open(self, "sys.attribute.indexed")
        # select attribute to read
        calvinsys.write(self.registry, self.attribute)


    @stateguard(lambda self: calvinsys.can_read(self.registry))
    @condition(action_input=['trigger'], action_output=['value'])
    def read(self, _):
        value = calvinsys.read(self.registry)
        return (value,)

    action_priority = (read,)
    requires = ["sys.attribute.indexed"]


    test_kwargs = {'attribute': "runtime.attribute"}
    test_calvinsys = {'sys.attribute.indexed': {'read': ["runtime.attribute"],
                                                'write': ["runtime.attribute"]}}
    test_set = [
        {
            'inports': {'trigger': [True]},
            'outports': {'value': ["runtime.attribute"]}
        }
    ]
