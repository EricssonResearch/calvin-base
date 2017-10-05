# -*- coding: utf-8 -*-

# Copyright (c) 2016-17 Ericsson AB
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

class ImageSource(Actor):

    """
    When token on input, get an image.

    Inputs:
      trigger: anything
    Outputs:
      b64image: generated image
    """

    @manage(exclude=["_cam"])
    def init(self):
        self.setup()

    def setup(self):
        self._cam = calvinsys.open(self, "image.source")

    def did_migrate(self):
        self.setup()

    def will_end(self):
        calvinsys.close(self._cam)

    @stateguard(lambda self: calvinsys.can_read(self._cam))
    @condition(action_output=['b64image'])
    def send_image(self):
        image = calvinsys.read(self._cam)
        return (image, )

    @stateguard(lambda self: calvinsys.can_write(self._cam))
    @condition(action_input=['trigger'])
    def fetch_image(self, trigger):
        calvinsys.write(self._cam, None)

    action_priority = (fetch_image, send_image)
    requires = ['image.source']


    test_calvinsys = {'image.source': {'read': [1,0,1,0,0,1,0,1],
                                       'write': [None, None, None, None]}}
    test_set = [
        {
            'inports': {'trigger': [True, 1, "a", 0]},
            'outports': {'b64image': [1,0,1,0,0,1,0,1]}
        }
    ]
