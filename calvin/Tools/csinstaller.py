#! /usr/bin/env python
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
import argparse
from calvin.csparser.cscompile import get_components_in_script
from calvin.actorstore.store import install_component

def get_components(filename, names):
    try:
        with open(filename, 'r') as source:
            source_text = source.read()
    except:
        return [], [{'reason': 'File not found', 'line': 0, 'col': 0}], []
    return get_components_in_script(source_text, names)


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--script', type=str, required=True,
                           help='script file with component definitions')
    argparser.add_argument('--namespace', type=str, required=True,
                           help='namespace to install components under')
    group = argparser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', dest='component', action='store_const', const=None,
                       help='install all components found in script')
    group.add_argument('--component', type=str, nargs='+',
                       help='name of component(s) to install')
    argparser.add_argument('--force', dest='overwrite', action='store_true',
                           help='overwrite components that exists at destination')
    argparser.add_argument('--issue-fmt', dest='fmt', type=str,
                           default='{issue_type}: {reason} {script} [{line}:{col}]',
                           help='custom format for issue reporting.')

    args = argparser.parse_args()

    def report_issues(issues, issue_type, filename=''):
        sorted_issues = sorted(issues, key=lambda k: k.get('line', 0))
        for issue in sorted_issues:
            sys.stderr.write(args.fmt.format(script=filename, issue_type=issue_type, **issue) + '\n')

    comps, errors, warnings = get_components(args.script, args.component)


    if errors:
        warnings.append({'reason': 'Nothing installed', 'line': 0, 'col': 0})
    else:
        for comp in comps:
            if not install_component(args.namespace, comp, args.overwrite):
                errors.append({'reason': 'Failed to install "{0}"'.format(comp.name), 'line': 0, 'col': 0})

    if warnings:
        report_issues(warnings, 'Warning', args.script)
    if errors:
        report_issues(errors, 'Error', args.script)
        return 1


if __name__ == '__main__':
    sys.exit(main())
