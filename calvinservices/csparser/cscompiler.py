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
from .cspreprocess import Preprocessor
from .dscodegen import calvin_dscodegen
from .codegen import calvin_codegen
from calvin.common import code_signer

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

def compile_source(source, appname, actorstore_uri):
    app_info, issuetracker = calvin_codegen(source, appname, actorstore_uri, verify=True)
    deploy_info, issuetracker2 = calvin_dscodegen(source, appname)
    issuetracker.merge(issuetracker2)
    deployable = {
        'app_info': app_info,
        'app_info_signature': None,
        'deploy_info': deploy_info
    }
    return (deployable, issuetracker)

def compile_file(filepath, include_paths, actorstore_uri):
    source, issuetracker = preprocess(filepath, include_paths)
    if issuetracker.error_count > 0:
        return ({}, issuetracker)
    appname = appname_from_filename(filepath)
    return compile_source(source, appname, actorstore_uri)

def sign_deployable(deployable, organization, common_name):
    signer = code_signer.CS(organization=organization, commonName=common_name)
    deployable['app_info_signature'] = signer.sign_deployable(deployable['app_info'])


def main():
    long_description = """
  Compile a CalvinScript source file, <filename> into a deployable JSON representation.
  By default, the output will be written to file with the same name as the input file,
  but with the extension replaced by 'json'.
  """
    # FIXME: Add credentials and verify arguments
    argparser = argparse.ArgumentParser(description=long_description)

    argparser.add_argument('--actorstore', dest='actorstore_uri', default="http://127.0.0.1:4999", type=str, help='URI of actorstore')
    argparser.add_argument('file', metavar='<filename>', type=str,
                           help="source file to compile, use '-' to read from stdin")
    argparser.add_argument('--compact', dest='indent', action='store_const', const=None, default=4,
                           help='use compact JSON format instead of readable (default)')
    argparser.add_argument('--sorted', dest='sorted', action='store_true', default=False,
                           help='sort resulting JSON output by keys')
    argparser.add_argument('--signed', dest='signed', action='store_true', default=False,
                           help='sign deployable')
    argparser.add_argument('--issue-fmt', dest='fmt', type=str,
                           default='{type!c}: {reason} {script} {line}:{col}',
                           help='custom format for issue reporting.')
    argparser.add_argument('--verbose', action='store_true',
                           help='informational output from the compiler')
    argparser.add_argument('-i', '--include', dest='include_paths', action='append', default=[],
                           metavar='<include_path>',
                           help='add search paths for include statements. Use multiple times for multiple include paths.')
    outgroup = argparser.add_mutually_exclusive_group()
    outgroup.add_argument('--stdout', dest='outfile', action='store_const', const="/dev/stdout",
                           help='send output to stdout instead of file (default)')
    outgroup.add_argument('--output', dest='outfile', type=str, default='', metavar='<filename>',
                           help='Output file, default is filename.json')

    args = argparser.parse_args()
    exit_code = 0

    # Compile
    infile = '/dev/stdin' if args.file == '-' else args.file
    deployable, issuetracker = compile_file(infile, args.include_paths, args.actorstore_uri)

    # Report errors and (optionally) warnings
    if issuetracker.error_count:
        for issue in issuetracker.formatted_errors(sort_key='line', custom_format=args.fmt, script=infile, line=0, col=0):
            sys.stderr.write(issue + "\n")
        exit_code = 1
    if issuetracker.warning_count and args.verbose:
        for issue in issuetracker.formatted_warnings(sort_key='line', custom_format=args.fmt, script=infile, line=0, col=0):
            sys.stderr.write(issue + "\n")
    if exit_code != 0:
        # Don't produce output if there were errors
        return exit_code

    # If compilation has no errors, generate output 
    if args.signed:
        sign_deployable(deployable, organization="com.ericsson", common_name="com.ericssonCS")

    string_rep = json.dumps(deployable, indent=args.indent, sort_keys=args.sorted)
    
    # Write to destination
    if args.outfile:
        dst = args.outfile
    else:
        path, ext = os.path.splitext(infile)
        if path == '/dev/stdin':
            path = appname
        dst = path + ".json"
    with open(dst, 'w') as f:
        f.write(string_rep)

    return exit_code

if __name__ == '__main__':
    sys.exit(main())
