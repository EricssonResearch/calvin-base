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


class ObjectCounter(Actor) :
    """
    Counts objects in a base64 encoded jpg image

    Inputs:
        b64image: Image to analyze
    Outputs:
        objects: number of objects found in image
    """

    @manage([])
    def init(self):
        self.setup()

    def setup(self):
        self._object_counter = calvinsys.open(self, "image.objectdetection")

    def did_migrate(self):
        self.setup()

    @stateguard(lambda self: calvinsys.can_write(self._object_counter))
    @condition(action_input=['b64image'])
    def analyze(self, b64image):
        calvinsys.write(self._object_counter, b64image)

    @stateguard(lambda self: calvinsys.can_read(self._object_counter))
    @condition(action_output=['objects'])
    def report(self):
        objects = calvinsys.read(self._object_counter)
        return (objects, )

    action_priority = (analyze, report )
    requires = ['image.objectdetection']


    test_calvinsys = {'image.objectdetection': {'read': ["dummy_data_read"],
                                                'write': ["dummy_data_write"]}}
    test_set = [
        {
            'inports': {'b64image': ["dummy_data_write"]},
            'outports': {'objects': ["dummy_data_read"]}
        }
    ]
