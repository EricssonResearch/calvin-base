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

# import os
from calvin.actor.actor import Actor, ActionResult, manage, condition


def test_helper_join(*args):
    import os.path
    return os.path.join(*args)


def test_helper_abspath(path):
    import os.path
    return os.path.abspath(path)


class Append(Actor):
    """Append 'append' to 'base'.

    If inside_base is true, generate an error status if
    resulting path is not inside 'base' directory.

    Inputs:
      base : Base path
      append : Relative path
    Outputs:
      path : Absolute path formed from 'base' + 'append', or 'base' on error
      error : True if checking enabled and not inside 'base' (error), false otherwise
    """

    @manage()
    def init(self, inside_base):
        self.inside_base = bool(inside_base)
        self.use('calvinsys.native.python-os-path', shorthand='path')

    def gen_path(self, base, append):
        base = self['path'].abspath(base)

        if self['path'].isabs(append):
            # concatenate
            path = base + append
        else:
            # joine
            path = self['path'].join(base, append)
        path = self['path'].abspath(path)
        invalid_path = False
        if self.inside_base:
            if not path.startswith(base):
                path = base
                invalid_path = True
        return (path, invalid_path)

    @condition(['base', 'append'], ['path', 'error'])
    def path(self, base, append):
        prod = self.gen_path(base, append)
        return ActionResult(production=prod)

    action_priority = (path, )
    require = ['calvinsys.native.python-os-path']

    def test_set_inside_base(self):
        self.inside_base = 1

    def test_clear_inside_base(self):
        self.inside_base = 0

    test_args = [0]

    test_set = [
        {'in': {'base': ["./path"], 'append': ["relpath"]},
         'out': {'path': ["%s" % (test_helper_abspath(test_helper_join("./path", "relpath")),)], 'error': [0]}
         }
    ]

    test_set += [
        {'setup': [test_set_inside_base],
         'in': {'base': ["./path"], 'append': ["relpath/../../../"]},
         'out': {'path': ["%s" % (test_helper_abspath("./path"),)], 'error': [1]}
         }
    ]
