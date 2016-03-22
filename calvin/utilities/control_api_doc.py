#!/usr/bin/env python

from calvin.runtime.north.calvincontrol import control_api_doc

lines = control_api_doc.split("\n")

block = []

print "# Calvin Control API"
for line in lines:
    if not line and block:
        print '- __' + block.pop(1).strip().replace('_', '\_') + '__' + "\n"
        print "```\n" + "\n".join(s for s in block) + "\n```"
        block =  []
    elif line:
        # same block
        block.append(line)
