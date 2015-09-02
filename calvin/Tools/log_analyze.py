#!/usr/bin/env python
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

import argparse
import json
import pprint
WIDTH = 80
def parse_arguments():
    long_description = """
Analyze calvin log.
  """

    argparser = argparse.ArgumentParser(description=long_description)

    argparser.add_argument('file', metavar='<filename>', type=str, nargs='?',
                           help='source file to compile')

    return argparser.parse_args()

def main():
    args = parse_arguments()
    print "Analyze", args.file
    file = None
    if args.file:
        file = open(args.file, 'r')

    log = []

    for line in file:
        if line.find('[[ANALYZE]]')==-1:
            continue
        logline = json.loads(line.split('[[ANALYZE]]',1)[1])
        #pprint.pprint(logline)
        log.append(logline)

    nodes = list(set([l['node_id'] for l in log]))
    try:
        # We have "TESTRUN" string in node id if logging py.test names
        nodes.remove("TESTRUN")
    except:
        pass
    line = ""
    for n in nodes:
        line += n + " "*(WIDTH-35)
    print line
    for l in log:
        if l['node_id'] == "TESTRUN":
            print l['func'] + "%"*(len(nodes)*WIDTH-len(l['func']))
            continue

        ind = nodes.index(l['node_id'])*WIDTH
        if l['func']=="SEND":
            ends = nodes.index(l['param']['to_rt_uuid'])*WIDTH
            if ind < ends:
                print " "*ind + "-"*(ends-1-ind) + ">"
            else:
                print " "*ends + "<" + "-"*(ind - ends-1)
            if l['param']['cmd'] == "REPLY":
                id_ = l['param']['msg_uuid']
                print (" "*ind + [c['param']['cmd'] for c in log 
                                 if c['func'] == "SEND" and "msg_uuid" in c['param'] and c['param']['msg_uuid'] == id_][0] +
                                 " reply")
            pp = pprint.pformat(l['param'], indent=1, width=WIDTH)
            for p in pp.split("\n"):
                print " "*ind + p
        elif l['func']!="RECV":
            if l['peer_node_id']:
                ends = nodes.index(l['peer_node_id'])*WIDTH
                if ind < ends:
                    print " "*ind + "# " + l['func'] + " #" + "="*(ends-4-ind-len(l['func'])) + "*"
                else:
                    print " "*ends + "*" + "="*(ind - ends-1) + "# " + l['func'] + " #"
            else:
                print " "*ind + "# " + l['func'] + " #"
            pp = pprint.pformat(l['param'], indent=1, width=WIDTH)
            for p in pp.split("\n"):
                print " "*ind + p

if __name__ == '__main__':
    main()
