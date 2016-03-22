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
import os
import glob
import shutil
from calvin.csparser.parser import calvin_parser
from calvin.csparser.checker import check
from calvin.actorstore import store
from calvin.utilities import certificate
from calvin.utilities.utils import get_home
from calvin.actorstore.store import ActorStore


def check_script(file):
    try:
        with open(file, 'r') as source:
            source_text = source.read()
    except:
        return {}, [{'reason': 'File not found', 'line': 0, 'col': 0}], []
    # Steps taken:
    # 1) parser .calvin file -> IR. May produce syntax errors/warnings
    # 2) checker IR -> IR. May produce syntax errors/warnings
    ir, errors, warnings = calvin_parser(source_text, file)
    # If there were errors during parsing no IR will be generated
    if not errors:
        c_errors, c_warnings = check(ir)
        errors.extend(c_errors)
        warnings.extend(c_warnings)
    return ir, errors, warnings


def install_component(namespace, name, definition, overwrite):
    astore = store.ActorStore()
    return astore.add_component(namespace, name, definition, overwrite)


def parse_args():
    long_desc = """Manage the host's actor store and credentials"""
    # top level arguments
    argparser = argparse.ArgumentParser(description=long_desc)
    cmdparsers = argparser.add_subparsers(help="command help")

    # parser for install cmd
    install_commands = ['component', 'actor']

    cmd_install = cmdparsers.add_parser('install', help='install components and actors')
    cmd_install.add_argument('cmd', metavar='<command>', choices=install_commands, type=str,
                           help="one of %s" % ", ".join(install_commands))
    cmd_install.add_argument('--force', dest='force', action='store_true',
                           help='overwrite components or actor that exists at destination')
    cmd_install.add_argument('--sign', dest='sign', action='store_true',
                           help='sign actor or component')
    cmd_install.add_argument('--org', metavar='<name>', dest='org', type=str,
                           help='Code Signer org name used, assumes default location when no calvin.conf')
    cmd_install.add_argument('--namespace', metavar='<ns.sub-ns>', type=str, required=True,
                           help='namespace to install actor or components under')
    aargs = cmd_install.add_argument_group("actor")
    aargs.add_argument('--actor', metavar='<path>', action='append', default=[], required=True,
                           help='actor file to install, can be repeated')
    gargs = cmd_install.add_argument_group("component")
    gargs.add_argument('--script', metavar='<path>', type=str, required=True,
                           help='script file with component definitions')
    whichcomp = gargs.add_mutually_exclusive_group(required=True)
    whichcomp.add_argument('--all', dest='component', action='store_const', const=[],
                       help='install all components found in script')
    whichcomp.add_argument('--component', metavar='<component>', type=str, nargs='+',
                       help='name of component(s) to install')
    gargs.add_argument('--issue-fmt', dest='fmt', type=str,
                           default='{issue_type}: {reason} {script} [{line}:{col}]',
                           help='custom format for issue reporting.')

    cmd_install.set_defaults(func=manage_install)

    # parser for trust cmd
    trust_commands = ['trust']

    cmd_trust = cmdparsers.add_parser('trust', help='manage trusted certificates')
    etargs = cmd_trust.add_argument_group("mandatory argument")
    etargs.add_argument('--path', metavar='<path>', type=str,
                           help='certificate to trust')
    cmd_trust.add_argument('--dir', metavar='<directory>', type=str, default="",
                           help='security directory, defaults to ~/.calvin/security')

    cmd_trust.set_defaults(func=manage_trust)

    # parser for sign cmd
    # Might later need to specify what is signed to add extra verification
    # sign_commands = ['app', 'component', 'actor']

    cmd_sign = cmdparsers.add_parser('sign', help='sign a file')
    # cmd_sign.add_argument('cmd', metavar='<command>', choices=sign_commands, type=str,
    #                        help="one of %s" % ", ".join(sign_commands))
    cmd_sign.add_argument('--org', metavar='<name>', dest='org', type=str, required=True,
                           help='Code Signer org name used')
    cmd_sign.add_argument('--dir', metavar='<directory>', type=str, default="",
                           help='security directory, defaults to ~/.calvin/security')
    cmd_sign.add_argument('--file', metavar='<path>', action='append', default=[],
                           help='file to sign, can be repeated')
    storeargs = cmd_sign.add_argument_group("actor and component")
    storeargs.add_argument('--nsfile', metavar='<ns.sub-ns.actor>', action='append', default=[],
                           help='namespaced store path to actor or components, can be repeated')

    cmd_sign.set_defaults(func=manage_sign)

     # parser for CA cmd
    ca_commands = ['create', 'remove', 'export']

    cmd_ca = cmdparsers.add_parser('ca', help='manage CA')
    cmd_ca.add_argument('cmd', metavar='<command>', choices=ca_commands, type=str,
                           help="one of %s" % ", ".join(ca_commands))
    etargs = cmd_ca.add_argument_group("export and trust")
    etargs.add_argument('--path', metavar='<path>', type=str,
                           help='export to directory')
    cargs = cmd_ca.add_argument_group("create")
    cmd_ca.add_argument('--force', dest='force', action='store_true',
                           help='overwrite file that exists at destination')
    cmd_ca.add_argument('--domain', metavar='<name>', dest='domain', type=str, required=True,
                           help='CA domain name used')
    cargs.add_argument('--name', metavar='<commonName>', type=str,
                           help='common name of Certificate Authority')
    cmd_ca.add_argument('--dir', metavar='<directory>', type=str, default="",
                           help='security directory, defaults to ~/.calvin/security')

    cmd_ca.set_defaults(func=manage_ca)

    # parser for code_signer cmd
    cs_commands = ['create', 'remove', 'export']

    cmd_cs = cmdparsers.add_parser('code_signer', help='manage Code Signer')
    cmd_cs.add_argument('cmd', metavar='<command>', choices=cs_commands, type=str,
                           help="one of %s" % ", ".join(cs_commands))
    etargs = cmd_cs.add_argument_group("export")
    etargs.add_argument('--path', metavar='<path>', type=str,
                           help='export to directory')
    cargs = cmd_cs.add_argument_group("create")
    cmd_cs.add_argument('--force', dest='force', action='store_true',
                           help='overwrite file that exists at destination')
    cmd_cs.add_argument('--org', metavar='<name>', dest='org', type=str, required=True,
                           help='Organizational name used')
    cargs.add_argument('--name', metavar='<commonName>', type=str,
                           help='common name of Code Signer')
    cmd_cs.add_argument('--dir', metavar='<directory>', type=str, default="",
                           help='security directory, defaults to ~/.calvin/security')

    cmd_cs.set_defaults(func=manage_cs)

    return argparser.parse_args()

def manage_install(args):
    def report_issues(issues, issue_type, file=''):
        sorted_issues = sorted(issues, key=lambda k: k.get('line', 0))
        for issue in sorted_issues:
            sys.stderr.write(args.fmt.format(script=file, issue_type=issue_type, **issue) + '\n')

    ir, errors, warnings = check_script(args.script)
    if warnings:
        report_issues(warnings, 'Warning', args.script)
    if errors:
        report_issues(errors, 'Error', args.script)
        return 1

    errors = []
    for comp_name, comp_def in ir['components'].items():
        if args.component and comp_name not in args.component:
            continue
        ok = install_component(args.namespace, comp_name, comp_def, args.overwrite)
        if not ok:
            errors.append({'reason': 'Failed to install "{0}"'.format(comp_name),
                          'line': comp_def['dbg_line'], 'col': 0})

    if errors:
        report_issues(errors, 'Error', args.script)
        return 1

def manage_trust(args):
    if not args.path:
        raise Exception("No path supplied")
    cert_name = os.path.basename(args.path)
    if args.dir:
        truststore_cert = os.path.join(args.dir, "trustStore", cert_name)
    else:
        homefolder = get_home()
        truststore_cert = os.path.join(homefolder, ".calvin", "security", "trustStore", cert_name)
    if not os.path.isdir(os.path.dirname(truststore_cert)):
        os.makedirs(os.path.dirname(truststore_cert), 0700)
    shutil.copy(args.path, truststore_cert)

def manage_sign(args):
    # Collect files to sign
    files = []
    if args.file:
        for f in args.file:
            files.extend(glob.glob(f))
    if args.nsfile:
        store = ActorStore()
        for m in args.nsfile:
            files.extend(store.actor_paths(m))
    # Filter out any files not *.calvin, *.comp, *.py
    files = [f for f in files if f.endswith(('.calvin', '.comp', '.py')) and not f.endswith('__init__.py')]
    if not files:
        raise Exception("No (*.calvin, *.comp, *py) files supplied")
    if not args.org:
        raise Exception("No org supplied")
    configfile = os.path.join(args.dir, args.org, "openssl.conf") if args.dir else None
    # When conf missing the exception is printed by main
    conf = certificate.Config(configfile=configfile, domain=args.org, readonly=True)
    exceptions = []
    for f in files:
        try:
            certificate.sign_file(conf, f)
        except Exception as e:
            exceptions.append(e)
    for e in exceptions:
        print "Error {}".format(e)

def manage_ca(args):
    if args.cmd == 'create' and args.domain and args.name:
        if not args.domain:
            raise Exception("No domain supplied")
        configfile = os.path.join(args.dir, args.domain, "openssl.conf") if args.dir else None
        conf = certificate.Config(configfile=configfile, domain=args.domain, commonName=args.name, force=args.force)
        certificate.new_domain(conf)
    elif args.cmd == 'remove':
        if not args.domain:
            raise Exception("No domain supplied")
        domaindir = os.path.join(args.dir, args.domain) if args.dir else None
        certificate.remove_domain(domaindir, args.domain)
    elif args.cmd == 'export':
        if not args.domain:
            raise Exception("No domain supplied")
        if not args.path:
            raise Exception("No path supplied")
        configfile = os.path.join(args.dir, args.domain, "openssl.conf") if args.dir else None
        conf = certificate.Config(configfile=configfile, domain=args.domain, readonly=True)
        certificate.copy_cert(conf, args.path)

def manage_cs(args):
    if args.cmd == 'create' and args.org and args.name:
        if not args.org:
            raise Exception("No organization supplied")
        configfile = os.path.join(args.dir, args.org, "openssl.conf") if args.dir else None
        conf = certificate.Config(configfile=configfile, domain=args.org, commonName=args.name, force=args.force)
        certificate.new_domain(conf)
    elif args.cmd == 'remove':
        if not args.org:
            raise Exception("No organization supplied")
        orgdir = os.path.join(args.dir, args.org) if args.dir else None
        certificate.remove_domain(orgdir, args.org)
    elif args.cmd == 'export':
        if not args.org:
            raise Exception("No organization supplied")
        if not args.path:
            raise Exception("No path supplied")
        configfile = os.path.join(args.dir, args.org, "openssl.conf") if args.dir else None
        conf = certificate.Config(configfile=configfile, domain=args.org, readonly=True)
        certificate.copy_cert(conf, args.path)

def main():
    args = parse_args()

    try:
        args.func(args)
    except Exception as e:
        print "Error {}".format(e)

if __name__ == '__main__':
    sys.exit(main())
