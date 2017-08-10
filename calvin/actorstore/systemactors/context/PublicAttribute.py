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


class PublicAttribute(Actor):
    """
    Fetch given public attribute of runtime given as a section.subsection.subsubsection
    
    Input:
        trigger: Any token will trigger a read
    Output:
      value : The given attribute of this runtime, or null
    """

    @manage(["attr"])
    def init(self, attribute):
        self.attr = attribute
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.public_attribute = calvinsys.open(self, "sys.attribute.public")
        # select attribute to read
        calvinsys.write(self.public_attribute, self.attr)
        

    @stateguard(lambda self: calvinsys.can_read(self.public_attribute))
    @condition(action_input=['trigger'], action_output=['value'])
    def attribute(self, _):
        
        attr = calvinsys.read(self.public_attribute)
        return (attr,)

    action_priority = (attribute,)

    requires = ["sys.attribute.public"]
