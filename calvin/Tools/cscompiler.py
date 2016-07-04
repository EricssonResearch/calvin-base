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
from calvin.csparser.parser import calvin_parser
# from calvin.csparser.checker import check
# from calvin.csparser.analyzer import generate_app_info
from calvin.csparser.codegen import CodeGen
from calvin.utilities.security import Security, security_enabled
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


def compile(source_text, filename, credentials=None, verify=True, node=None, cb=None):
    # Steps taken:
    # 1) Authenticate subject, verify signature and check security policy if security is enabled
    # 2) parser .calvin file -> IR. May produce syntax errors/warnings
    # 3) checker IR -> IR. May produce syntax errors/warnings
    # 4) analyzer IR -> app. Should not fail. Sets 'valid' property of IR to True/False
    content = None
    if credentials:
        content = Security.verify_signature_get_files(filename, skip_file=True)
        # content is ALWAYS a dict if skip_file is True
        content['file'] = source_text

    deployable = {'valid': False, 'actors': {}, 'connections': {}}
    errors = [] # TODO: fill in something meaningful
    warnings = []
    if node is not None and security_enabled():
        sec = Security(node)
        sec.authenticate_subject(credentials, callback=CalvinCB(_compile_cont1, source_text,
                                                filename, verify, security=sec, org_cb=cb, content=content))
    else:
        if cb:
            _compile_cont2(source_text, filename, verify, True, org_cb=cb)
        else:
            return _compile_cont2(source_text, filename, verify, True)

def _compile_cont1(source_text, filename, verify, authentication_decision, security, org_cb=None, content=None):
    deployable = {'valid': False, 'actors': {}, 'connections': {}}
    errors = [] # TODO: fill in something meaningful
    warnings = []
    if not authentication_decision:
        _log.error("Authentication failed")
        # This error reason is detected in calvin control and gives proper REST response
        errors.append({'reason': "401: UNAUTHORIZED", 'line': None, 'col': None})
        if org_cb:
            org_cb(deployable, errors, warnings)
            return
        else:
            return deployable, errors, warnings

    verified, signer = security.verify_signature_content(content, "application")
    if not verified:
        # Verification not OK if sign or cert not OK.
        _log.error("Failed application verification")
        # This error reason is detected in calvin control and gives proper REST response
        errors.append({'reason': "401: UNAUTHORIZED", 'line': None, 'col': None})
        if org_cb:
            org_cb(deployable, errors, warnings)
            return
        else:
            return deployable, errors, warnings
    security.check_security_policy(CalvinCB(_compile_cont2, source_text, filename, verify,
                                       security=security, org_cb=org_cb), "application", signer=signer)

def _compile_cont2(source_text, filename, verify, access_decision, security=None, org_cb=None):
    deployable = {'valid': False, 'actors': {}, 'connections': {}}
    errors = [] # TODO: fill in something meaningful
    warnings = []
    if not access_decision:
        _log.error("Access denied")
        # This error reason is detected in calvin control and gives proper REST response
        errors.append({'reason': "401: UNAUTHORIZED", 'line': None, 'col': None})
        if org_cb:
            org_cb(deployable, errors, warnings)
            return
        else:
            return deployable, errors, warnings
    _log.debug("Parsing...")
    ir, errors, warnings = calvin_parser(source_text, filename)
    _log.debug("Parsed %s, %s, %s" % (ir, errors, warnings))

    app_name = os.path.splitext(os.path.basename(filename))[0]
    codegen = CodeGen(ir, app_name, verify=verify)
    codegen.run()
    deployable = codegen.app_info
    errors.extend([issue for issue in codegen.issues if issue['type'] == 'error'])
    warnings.extend([issue for issue in codegen.issues if issue['type'] == 'warning'])


    _log.debug("Compiled %s, %s, %s" % (deployable, errors, warnings))
    if org_cb:
        org_cb(deployable, errors, warnings, security=security)
    else:
        return deployable, errors, warnings




def compile_file(file, credentials=None):
    with open(file, 'r') as source:
        sourceText = source.read()
        return compile(sourceText, file, credentials=credentials)

def compile_generator(files):
    for file in files:
        deployable, errors, warnings = compile_file(file)
        yield((deployable, errors, warnings, file))

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

    def report_issues(issues, issue_type, file=''):
        sorted_issues = sorted(issues, key=lambda k: k.get('line', 0))
        for issue in sorted_issues:
            sys.stderr.write(args.fmt.format(script=file, issue_type=issue_type, **issue) + '\n')

    exit_code = 0
    for deployable, errors, warnings, file in compile_generator(args.files):
        if errors:
            report_issues(errors, 'Error', file)
            exit_code = 1
        if warnings and args.verbose:
            report_issues(warnings, 'Warning', file)
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
            path, ext = os.path.splitext(file)
            dst = path + ".json"
            with open(dst, 'w') as f:
                f.write(string_rep)

    return exit_code

if __name__ == '__main__':
    sys.exit(main())
