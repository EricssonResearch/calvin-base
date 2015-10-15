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
import traceback
from datetime import datetime

WIDTH = 80
def parse_arguments():
    long_description = """
Analyze calvin log.
  """

    argparser = argparse.ArgumentParser(description=long_description)

    argparser.add_argument('files', metavar='<filenames>', type=str, nargs='+',
                           default=[], help='logfiles to display')

    argparser.add_argument('-i', '--interleaved', dest='interleave', action='store_true',
                           help='The none analyze log messages are printed interleaved')

    argparser.add_argument('-l', '--limit', dest='limit', type=int, default=0,
                           help='Limit stack trace print to specified nbr of frames')

    return argparser.parse_args()

def main():
    args = parse_arguments()
    print "Analyze", args.files
    files = []
    for name in args.files:
        files.append(open(name, 'r'))

    log = []

    for file in files:
        for line in file:
            try:
                t=datetime.strptime(line[:23], "%Y-%m-%d %H:%M:%S,%f")
            except:
                t=None
            if line.find('[[ANALYZE]]')==-1:
                if args.interleave:
                    # None ANALYZE log lines might contain line breaks, then following lines (without time) need to 
                    # be sorted under the first line, hence combine them
                    if t:
                        log.append({'time': t, 
                                    'func': 'OTHER', 'param': line, 'node_id': None})
                    else:
                        log[-1]['param'] += line
                continue
            try:
                logline = json.loads(line.split('[[ANALYZE]]',1)[1])
            except:
                # For some reason could not handle it, treat it as a normal other log level line
                logline = {'func': 'OTHER', 'param': line, 'node_id': None}
            logline['time'] = t
            #pprint.pprint(logline)
            log.append(logline)

    if len(files)>1:
        log = sorted(log, key=lambda k: k['time'])

    # Collect all node ids and remove "TESTRUN" string as node id since it is used when logging py.test name
    nodes = list(set([l['node_id'] for l in log] + [l.get('peer_node_id', None)  for l in log]) - set([None, "TESTRUN"]))
    line = ""
    for n in nodes:
        line += n + " "*(WIDTH-35)
    print line
    for l in log:
        if l['node_id'] == "TESTRUN":
            print l['func'] + "%"*(len(nodes)*WIDTH-len(l['func']))
            continue
        if l['func'] == "OTHER" and l['node_id'] is None:
            print l['param'].rstrip()
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
            if l['stack'] and args.limit >= 0:
                tb = traceback.format_list(l['stack'][-(args.limit+2):-1])
                for s in tb:
                    for sl in s.split("\n"):
                        if sl:
                            print " "*ind + ">" + sl.rstrip()

if __name__ == '__main__':
    main()
