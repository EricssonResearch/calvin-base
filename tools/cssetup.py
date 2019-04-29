#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2019 Ericsson AB
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
import sys
import json
import yaml
import random
from datetime import datetime
import argparse

from tools.toolsupport.orchestration import SystemManager

def parse_arguments():

    long_description = """
    Set up a Calvin system based on a system config file.
    """

    argparser = argparse.ArgumentParser(description=long_description)
    argparser.add_argument('-v', '--verbose', action='store_true', default=False, help='Verbose output')
    group = argparser.add_mutually_exclusive_group(required=True)
    group.add_argument('-s', '--setup', type=str, metavar='<filename>', help='System description file')
    group.add_argument('-l', '--list', action='store_true', help='List running systems\' names')
    group.add_argument('-t', '--teardown', type=str, metavar='<name>', help='Tear down named system')

    args = argparser.parse_args()
    return args

def unique_name(exclude):
    adj = ['shiny', 'dull', 'dark', 'light', 'smooth', 'ragged', 'red', 'green', 'blue', 'black', 'white']
    noun = ['tiger', 'monkey', 'yak', 'mountain', 'valley', 'operator', 'quark', 'diamond', 'water', 'hammer', 'giant']
    if len(exclude) >= len(adj)*len(noun):
        raise IndexError("Too many systems in use")
    while True:
        name = "{}-{}".format(random.choice(adj), random.choice(noun))
        if name not in exclude:
            break
    return name  
     
def _status_file():
    return os.path.expanduser('~/.cs_status')

def read_status():
    try:
        with open(_status_file(), 'r') as fp:
            status = json.load(fp)
    except FileNotFoundError:
        status = []
    return status

def write_status(status):
    with open(_status_file(), 'w') as fp:
        json.dump(status, fp)

def _system_setup(setup_file, verbose):
    # Actual setup
    sm = SystemManager(setup_file, verbose=verbose)
    # sm.teardown()
    return sm.info

def system_setup(setup_file, verbose):
    # Start system, write info to ~/.cs_status
    with open(setup_file, 'r') as fp:
        system_setup = yaml.load(fp, Loader=yaml.SafeLoader)
    try:
        info = _system_setup(system_setup, verbose)
    except Exception as err:
       print(err, file=sys.stderr)
       return 1
    status = read_status()
    exclude = [x['name'] for x in status]
    name = unique_name(exclude)
    ts = datetime.now().isoformat(sep=' ', timespec='milliseconds')
    status.append({'name':name, 'ts':ts, 'config':setup_file, 'info':info})
    write_status(status)
    return 0
    
def system_list(verbose):
    status = read_status()
    if status:
        print("{:<16}{:<26}{}\n{}".format('Name', 'Started', 'Config file', '-'*53))    
        for s in status:
            print("{name:<16}{ts}   {config}".format(**s))
    else:
        print("No running systems")
    return 0
              

def _system_teardown(info, verbose):
    # Actual teardown
    for name, proc in info.items():
        pid = proc['pid']
        if not pid:
            continue
        if verbose:
            print("Terminating {}".format(name))
        try:        
            os.kill(pid, 9)
        except ProcessLookupError:
            print("Process {} ({}) does not exist".format(pid, name), file=sys.stderr)

def system_teardown(name, verbose):
    status = read_status()
    for entry in status:
        if entry['name'] == name:
            _system_teardown(entry['info'], verbose)
            status.remove(entry)
            write_status(status)
            break
    else:
        print("No system named {}".format(name), file=sys.stderr)
    return 0

def main():            
    args = parse_arguments()

    if args.setup:
        status = system_setup(args.setup, args.verbose)        
    elif args.teardown:
        status = system_teardown(args.teardown, args.verbose)       
    else:
        status = system_list(args.verbose)
    return status

if __name__ == '__main__':
    sys.exit(main())
        
