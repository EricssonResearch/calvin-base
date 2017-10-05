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

from calvin.actor.actor import Actor, condition, manage, stateguard, calvinsys


class ObjectFinder(Actor) :
    """
    Finds and marks objects in a base64 encoded jpg image function

    Inputs:
        b64image: Image to analyze
    Outputs:
        b64image: New image with all detected objects marked
    """

    @manage([])
    def init(self):
        self.setup()

    def setup(self):
        self._object_counter = calvinsys.open(self, "image.objectfinding")

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: calvinsys.can_write(self._object_counter))
    @condition(action_input=['b64image'])
    def analyze(self, b64image):
        calvinsys.write(self._object_counter, b64image)

    @stateguard(lambda self: calvinsys.can_read(self._object_counter))
    @condition(action_output=['b64image'])
    def report(self):
        image = calvinsys.read(self._object_counter)
        return (image, )

    action_priority = (analyze, report)
    requires = ['image.objectfinding']


    test_calvinsys = {'image.objectfinding': {'read': ["dummy_data_read"],
                                              'write': ["dummy_data_write"]}}
    test_set = [
        {
            'inports': {'b64image': ["dummy_data_write"]},
            'outports': {'b64image': ["dummy_data_read"]}
        }
    ]
