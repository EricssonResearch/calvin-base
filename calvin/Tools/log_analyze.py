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
import re
import textwrap

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

    argparser.add_argument('-w', '--width', dest='width', type=int, default=80,
                           help='Width of node column')

    argparser.add_argument('-c', '--text-width', dest='text_width', type=int, default=None,
                           help='Width of text in node column')

    argparser.add_argument('-f', '--first', dest='first', type=str, default=None,
                           help='A node id that should be in first column')

    argparser.add_argument('-x', '--exclude', dest='excludes', action='append', default=[],
                           help="Exclude logged module, can be repeated")

    return argparser.parse_args()

re_pid = re.compile("^[0-9,\-,\,, ,:]*[A-Z]* *([0-9]*)-.*")


class MyPrettyPrinter(pprint.PrettyPrinter):
    def format(self, object, context, maxlevels, level):
        # Pretty print strings unescaped
        if isinstance(object, basestring):
            return (object.decode('string_escape'), True, False)
        return pprint.PrettyPrinter.format(self, object, context, maxlevels, level)

def main():
    global WIDTH
    args = parse_arguments()
    WIDTH = args.width or WIDTH
    text_width = args.text_width or WIDTH + 20
    print "Analyze", args.files
    files = []
    for name in set(args.files):
        files.append(open(name, 'r'))

    log = []
    pid_to_node_id = {}
    pids = set([])

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
                        if log:
                            try:
                                log[-1]['param'] += line
                            except:
                                # Did not have a previous non ANALYZE log line for some reason, skip it
                                pass
                    try:
                        pid = re.match(re_pid, line).group(1)
                        if pid:
                            log[-1]['pid'] = pid
                            pids.add(pid)
                    except:
                        pass
                continue
            try:
                lineparts = line.split('[[ANALYZE]]',1)
                logline = json.loads(lineparts[1])
                logline['match_exclude'] = lineparts[0]
            except:
                # For some reason could not handle it, treat it as a normal other log level line
                logline = {'func': 'OTHER', 'param': line, 'node_id': None}
            if logline['node_id']:
                try:
                    pid = re.match(re_pid, line).group(1)
                    if int(pid) != logline['node_id']:
                        pid_to_node_id[pid] = logline['node_id']
                except:
                    pass
            logline['time'] = t
            #pprint.pprint(logline)
            log.append(logline)

    pprint.pprint(pid_to_node_id)
    int_pid_to_node_id = {int(k): v for k,v in pid_to_node_id.iteritems()}
    pids = list(pids)
    print "PIDS", pids

    for l in log:
        if l['node_id'] in int_pid_to_node_id:
            l['node_id'] = int_pid_to_node_id[l['node_id']]

    if len(files)>1:
        log = sorted(log, key=lambda k: k['time'])

    # Collect all node ids and remove "TESTRUN" string as node id since it is used when logging py.test name
    nodes = list(set([l['node_id'] for l in log] + [l.get('peer_node_id', None)  for l in log]) - set([None, "TESTRUN"]))
    if not nodes:
        nodes = pids
        pid_to_node_id = {p: p for p in pids}
    if args.first in nodes:
        nodes.remove(args.first)
        nodes.insert(0, args.first)
    line = ""
    for n in nodes:
        line += str(n) + " "*(WIDTH-len(n))
    print line
    for l in log:
        if 'match_exclude' in l:
            exclude_line = l['match_exclude']
        else:
            exclude_line = l['param']
        if any([exclude_line.find(excl) > -1 for excl in args.excludes]):
            continue
        if l['node_id'] == "TESTRUN":
            print l['func'] + "%"*(len(nodes)*WIDTH-len(l['func']))
            if 'param' in l and l['param']:
                pprint.pprint(l['param'])
            continue
        if l['func'] == "OTHER" and l['node_id'] is None:
            try:
                if 'pid' in l:
                    ind = nodes.index(pid_to_node_id[l['pid']])*WIDTH
                else:
                    ind = nodes.index(pid_to_node_id[re.match(re_pid, l['param']).group(1)])*WIDTH
            except Exception as e:
                ind = 0
                pass
            lines = str.splitlines(l['param'].rstrip())
            pre = "<>"
            for line in lines:
                wrapped_lines = textwrap.wrap(line, width=text_width,
                                              replace_whitespace=False, drop_whitespace=False)
                for wl in wrapped_lines:
                    print " "*ind + pre + wl
                    pre = ""
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
            pp = pprint.pformat(l['param'], indent=1, width=text_width)
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
            pp = MyPrettyPrinter(indent=1, width=WIDTH).pformat(l['param'])
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
