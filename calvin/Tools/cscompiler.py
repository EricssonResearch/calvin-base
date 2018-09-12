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
from cspreprocess import Preprocessor
from calvin.csparser.dscodegen import calvin_dscodegen
from calvin.csparser.codegen import calvin_codegen
from calvin.csparser.parser import printable_ir

def appname_from_filename(filename):
    appname = os.path.splitext(os.path.basename(filename))[0]
    # Dot . is invalid in application names (interpreted as actor path separator),
    # so replace any . with _
    appname = appname.replace('.', '_')
    return appname

def preprocess(filename, include_paths):
    pp = Preprocessor(include_paths)
    sourceText, it = pp.process(filename)
    return (sourceText, it)

def main():
    long_description = """
  Compile a CalvinScript source file, <filename> into a deployable JSON representation.
  By default, the output will be written to file with the same name as the input file,
  but with the extension replaced by 'json'.
  """
    # FIXME: Add credentials and verify arguments
    argparser = argparse.ArgumentParser(description=long_description)

    argparser.add_argument('file', metavar='<filename>', type=str,
                           help='source file to compile')
    argparser.add_argument('--compact', dest='indent', action='store_const', const=None, default=4,
                           help='use compact JSON format instead of readable (default)')
    argparser.add_argument('--sorted', dest='sorted', action='store_true', default=False,
                           help='sort resulting JSON output by keys')
    argparser.add_argument('--issue-fmt', dest='fmt', type=str,
                           default='{type!c}: {reason} {script} {line}:{col}',
                           help='custom format for issue reporting.')
    argparser.add_argument('--verbose', action='store_true',
                           help='informational output from the compiler')
    argparser.add_argument('-i', '--include', dest='include_paths', action='append', default=[],
                           metavar='<include_path>',
                           help='add search paths for include statements. Use multiple times for multiple include paths.')
    output_type = argparser.add_mutually_exclusive_group()
    output_type.add_argument('--deployscript', action='store_true', default=False,
                           help='generate deployjson file')
    output_type.add_argument('--intermediate', action='store_true', default=False,
                           help='generate intermediate representation file')
    outgroup = argparser.add_mutually_exclusive_group()
    outgroup.add_argument('--stdout', dest='outfile', action='store_const', const="/dev/stdout",
                           help='send output to stdout instead of file (default)')
    outgroup.add_argument('--output', dest='outfile', type=str, default='', metavar='<filename>',
                           help='Output file, default is filename.json')


    args = argparser.parse_args()
    exit_code = 0

    source, issuetracker = preprocess(args.file, args.include_paths)
    if issuetracker.error_count == 0:
        appname = appname_from_filename(args.file)
        if args.deployscript:
            result, issuetracker = calvin_dscodegen(source, appname)
        elif args.intermediate:
            result, issuetracker = printable_ir(source)
        else:
            result, issuetracker = calvin_codegen(source, appname, verify=True)
    if issuetracker.error_count:
        for issue in issuetracker.formatted_errors(sort_key='line', custom_format=args.fmt, script=args.file, line=0, col=0):
            sys.stderr.write(issue + "\n")
        exit_code = 1
    if issuetracker.warning_count and args.verbose:
        for issue in issuetracker.formatted_warnings(sort_key='line', custom_format=args.fmt, script=args.file, line=0, col=0):
            sys.stderr.write(issue + "\n")
    if exit_code != 0:
        # Don't produce output if there were errors
        return exit_code
    if args.intermediate is True:
        string_rep = result
    else:
        string_rep = json.dumps(result, indent=args.indent, sort_keys=args.sorted)
    if args.outfile:
        dst = args.outfile
    else:
        path, ext = os.path.splitext(args.file)
        dst = path + ".json"
    with open(dst, 'w') as f:
        f.write(string_rep)

    return exit_code

if __name__ == '__main__':
    sys.exit(main())
