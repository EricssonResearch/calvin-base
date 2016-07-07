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


import sys
import textwrap
import argparse

from calvin.csparser.visualize import visualize_script, visualize_deployment, visualize_component

def main():
    long_description = """
    Generate a DOT output for use with GraphViz to generate a vizualization
    of the Calvin application graph.

    Typical usage would be something like (Linux):
    csviz --script foo.calvin | dot -Tpdf | pdfviewer -
    or (Mac OS X):
    csviz --script foo.calvin | dot -Tpdf | open -f -a Preview
    """

    argparser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(long_description)
    )
    argparser.add_argument('--script', type=str, required=True,
                           help='script file to visualize.')
    group = argparser.add_mutually_exclusive_group()
    group.add_argument('--deployment', action='store_true',
                       help='expand all components into constituent parts.')
    group.add_argument('--component', type=str,
                       help='show internals of a component in script.')

    args = argparser.parse_args()

    with open(args.script, 'r') as f:
        source_text = f.read()

    if args.deployment:
        dot, issuetracker = visualize_deployment(source_text)
    elif args.component:
        dot, issuetracker = visualize_component(source_text, args.component)
    else:
        dot, issuetracker = visualize_script(source_text)

    issue_format = '{type!c}: {reason} {script}:{line}'
    for issue in issuetracker.formatted_issues(sort_key='line', custom_format=issue_format, script=args.script, line=0):
        sys.stderr.write(issue + "\n")

    print(dot)

    if issuetracker.error_count:
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())
