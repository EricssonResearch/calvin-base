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

import os
from calvin.actor.actor import Actor, ActionResult, manage, condition, guard


class Append(Actor):
    """Append 'append' to 'base'.

    If inside_base is non-zero, generate an error status if
    resulting path is not inside 'base' directory.

    Inputs:
      base : Base path
      append : Relative path
    Outputs:
      path : Absolute path formed from 'base' + 'append', or 'base' on error
      error : 1 if checking enabled and not inside 'base' (error), 0 otherwise
    """

    @manage()
    def init(self, inside_base):
        self.inside_base = bool(inside_base)

    def gen_path(self, base, append):
        base = os.path.abspath(base)
        path = base +'/'+ append
        path = os.path.abspath(path)
        inside = int(self.inside_base and not (base in path))
        return (path, inside)

    @condition(['base', 'append'], ['path', 'error'])
    def path(self, base, append):
        prod = self.gen_path(base, append)
        return ActionResult(production=prod)

    action_priority = (path, )

