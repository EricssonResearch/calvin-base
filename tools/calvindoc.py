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


import json
import sys
import argparse
from tools import toolsupport         

def main():

    long_description = """
    Provide documentation for modules, actors, and components.
    """

    default_format = 'compact' if sys.argv[0].endswith('csdocs') else 'detailed'

    argparser = argparse.ArgumentParser(description=long_description)
    group = argparser.add_mutually_exclusive_group()
    group.add_argument('--actorstore', dest='actorstore_uri', default="http://127.0.0.1:4999", type=str, help='URI of actorstore')
    group.add_argument('--local', dest='actorstore_uri', action='store_const', const='local', help='Use locally installed actorstore')
    group = argparser.add_mutually_exclusive_group()
    # group.add_argument('--actor', dest='target', action='store_const', const='actor', default='actor', help='Show actor help')
    group.add_argument('--lib', dest='target', action='store_const', const='lib', default='actor', help='Show calvinlib help')
    group.add_argument('--libimpl', dest='target', action='store_const', const='libimpl', default='actor', help='Show calvinlib help')
    group.add_argument('--sys', dest='target', action='store_const', const='sys', default='actor', help='Show calvinsys help')
    group.add_argument('--sysimpl', dest='target', action='store_const', const='sysimpl', default='actor', help='Show calvinsys help')
    argparser.add_argument('--format', default=default_format, choices=['detailed', 'compact', 'raw'],
                           help='Options "detailed" and "compact" returns pretty-printed text,'
                                ' while "raw" returns a JSON-formatted representation that can be'
                                ' used to generated the documentation in other formats.')
    argparser.add_argument('--prettyprinter', default='plain', choices=['plain', 'md'],
                           help='When "--format detailed" is in use, this options allows a choice between plain text and markdown')
    argparser.add_argument('what', metavar='<actor or module>', type=str, nargs='?', default='',
                       help='What to look up documentation for, if empty show top level documentation')

    args = argparser.parse_args()
    ts = toolsupport.ToolSupport(args.actorstore_uri)

    if args.target == 'actor':
        if args.format == 'raw':
            print(ts.help_raw(args.what))
        else:
            compact = bool(args.format == 'compact')
            print(ts.help(args.what, compact=compact, formatting=args.prettyprinter))
    else:
        # Calvinsys/Calvinlib
        print(ts.help_for_calvin_internals(args.what, args.target, formatting=args.prettyprinter))

if __name__ == '__main__':
    main()
