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

import os
import sys
import json
import argparse
from calvin.csparser.cscompile import compile_script

def _appname_from_filename(filename):
    return os.path.splitext(os.path.basename(filename))[0]

def compile_file(filename, credentials=None):
    with open(filename, 'r') as source:
        sourceText = source.read()
        appname = _appname_from_filename(filename)
        return compile_script(sourceText, appname, credentials=credentials)

def compile_generator(files):
    for filename in files:
        deployable, errors, warnings = compile_file(filename)
        yield((deployable, errors, warnings, filename))

def remove_debug_info(deployable):
    pass
    # if type(d)==type({}):
    #     d.pop('dbg_line', None)
    #     for item in d:
    #         _remove_debug_symbols(d[item])
    # elif type(d)==type([]):
    #     for item in d:
    #         _remove_debug_symbols(item)

def main():
    long_description = """
  Compile a CalvinScript source file, <filename> into a deployable JSON representation.
  By default, the output will be written to file with the same name as the input file,
  but with the extension replaced by 'json'.
  """

    argparser = argparse.ArgumentParser(description=long_description)

    argparser.add_argument('files', metavar='<filename>', type=str, nargs='+',
                           help='source file to compile')
    argparser.add_argument('-d', '--debug', dest='debug', action='store_true', default=False,
                           help='leave debugging information in output')
    argparser.add_argument('--stdout', dest='to_stdout', action='store_true',
                           help='send output to stdout instead of file (default)')
    argparser.add_argument('--compact', dest='indent', action='store_const', const=None, default=4,
                           help='use compact JSON format instead of readable (default)')
    argparser.add_argument('--sorted', dest='sorted', action='store_true', default=False,
                           help='sort resulting JSON output by keys')
    argparser.add_argument('--issue-fmt', dest='fmt', type=str,
                           default='{issue_type}: {reason} {script} [{line}:{col}]',
                           help='custom format for issue reporting.')
    argparser.add_argument('--verbose', action='store_true',
                           help='informational output from the compiler')

    args = argparser.parse_args()

    def report_issues(issues, issue_type, filename=''):
        print issues
        sorted_issues = sorted(issues, key=lambda k: k.get('line', 0))
        for issue in sorted_issues:
            sys.stderr.write(args.fmt.format(script=filename, issue_type=issue_type, **issue) + '\n')

    exit_code = 0
    for deployable, errors, warnings, filename in compile_generator(args.files):
        if errors:
            report_issues(errors, 'Error', filename)
            exit_code = 1
        if warnings and args.verbose:
            report_issues(warnings, 'Warning', filename)
        if exit_code == 1:
            # Don't produce output if there were errors
            continue
        if not args.debug:
            # FIXME: Debug information is not propagated from IR to deployable by Analyzer.
            #        When it is, this is the place to remove it
            remove_debug_info(deployable)
        string_rep = json.dumps(deployable, indent=args.indent, sort_keys=args.sorted)
        if args.to_stdout:
            print(string_rep)
        else:
            path, ext = os.path.splitext(filename)
            dst = path + ".json"
            with open(dst, 'w') as f:
                f.write(string_rep)

    return exit_code

if __name__ == '__main__':
    sys.exit(main())
