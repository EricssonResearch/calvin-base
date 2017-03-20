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
from calvin.actorstore.store import DocumentationStore


def main():

    long_description = """
    Provide documentation for modules, actors, and components.
    """

    default_format = 'compact' if sys.argv[0].endswith('csdocs') else 'detailed'

    argparser = argparse.ArgumentParser(description=long_description)
    group = argparser.add_mutually_exclusive_group()
    group.add_argument('what', metavar='<actor or module>', type=str, nargs='?', default=None,
                       help='What to look up documentation for, if empty show top level documentation')
    group.add_argument('--all', action='store_const', const=True, default=False,
                       help='Generate complete actor documentation in Markdown format')
    argparser.add_argument('--format', default=default_format, choices=['detailed', 'compact', 'raw'],
                           help='Options "detailed" and "compact" returns pretty-printed text,'
                                ' while "raw" returns a JSON-formatted representation that can be'
                                ' used to generated the documentation in other formats.')
    argparser.add_argument('--prettyprinter', default='plain', choices=['plain', 'md'],
                           help='When "--format detailed" is in use, this options allows a choice between plain text and markdown')

    args = argparser.parse_args()
    store = DocumentationStore()

    if args.all:
        print store.documentation()
    else:
        if args.format == 'raw':
            print store.help_raw(args.what)
        else:
            compact = bool(args.format == 'compact')
            print store.help(args.what, compact=compact, formatting=args.prettyprinter)

if __name__ == '__main__':
    main()
