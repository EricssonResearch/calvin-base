#!/usr/bin/env python

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *
from calvin.runtime.north.calvincontrol import control_api_doc

lines = control_api_doc.split("\n")

block = []

print("# Calvin Control API")
for line in lines:
    if not line and block:
        print('- __' + block.pop(1).strip().replace('_', '\_') + '__' + "\n")
        print("```\n" + "\n".join(s for s in block) + "\n```")
        block =  []
    elif line:
        # same block
        block.append(line)
