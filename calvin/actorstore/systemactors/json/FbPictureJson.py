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

# encoding: utf-8

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard

class FbPictureJson(Actor):

    """
    Create a json for a photo status on Facebook


    Inputs:
      message: just a string
      picture: string path
    Outputs:
      json: the relative json file
    """


    @manage([''])
    def init(self):
        self.message = None
        self.picture = None


    @condition(['picture', 'message'], ['json'])
    def produce_json(self, picture, message):

        res = {'picture' : picture, 'message' : message}
        return ActionResult(production=(res, ))

    action_priority = (produce_json,)


