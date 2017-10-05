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

from calvin.actor.actor import Actor, condition, calvinlib


class FaceDetect(Actor) :
    """
    Detect faces in a jpg-image

    Inputs:
        image: Image to analyze
    Outputs:
        faces: non-zero if face detected
    """

    def init(self):
        self.setup()

    def setup(self):
        self.use("calvinsys.media.image", shorthand="image")
        self.base64 = calvinlib.use('base64')
        self.image = self["image"]

    def did_migrate(self):
        self.setup()

    @condition(['image'], ['faces'])
    def detect(self, image):
        found = self.image.detect_face(self.base64.decode(image))
        return (found, )

    action_priority = (detect, )
    requires = ['calvinsys.media.image', 'base64']


    test_set = [
        {
            'inports': {'image': []},
            'outports': {'faces': []}
        }
    ]
