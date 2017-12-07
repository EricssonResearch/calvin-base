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
import json
from calvin.actorstore import store
from calvin.utilities import certificate
from calvin.utilities import certificate_authority
from calvin.utilities import runtime_credentials
from calvin.utilities import code_signer
from calvin.utilities.utils import get_home
from calvin.utilities.attribute_resolver import AttributeResolver
from calvin.utilities import calvinuuid
from calvin.actorstore.store import ActorStore, install_component
from calvin.csparser.codegen import calvin_components

def parse_args():
    long_desc = """Manage the host's actor store and credentials"""
    # top level arguments
    argparser = argparse.ArgumentParser(description=long_desc)
    cmdparsers = argparser.add_subparsers(help="command help")

    ######################
    # parser for install cmd
    ######################
    install_commands = ['component', 'actor']

    install_parser = cmdparsers.add_parser('install', help='install components and actors')
    install_parser.add_argument('--issue-fmt', dest='fmt', type=str,
                       default='{type!c}: {reason} {script} {line}:{col}',
                       help='custom format for issue reporting.')

    install_parser = install_parser.add_subparsers(help='sub-command help', dest='cmd')

    ######################
    # Parser for install component cmd
    ######################
    cmd_install_comp = install_parser.add_parser('component', help='Install components')
    # Arguments
    cmd_install_comp.add_argument('--force', dest='force', action='store_true',
                           help='overwrite components or actor that exists at destination')
    cmd_install_comp.add_argument('--org', metavar='<name>', dest='org', type=str,
                           help='Code Signer org name used, assumes default location when no calvin.conf')
    cmd_install_comp.add_argument('--namespace', metavar='<ns.sub-ns>', type=str, required=True,
                           help='namespace to install actor or components under')
    cmd_install_comp.add_argument('--script', metavar='<path>', type=str, required=True,
                           help='script file with component definitions')
    whichcomp = cmd_install_comp.add_mutually_exclusive_group(required=True)
    whichcomp.add_argument('--all', dest='component', action='store_const', const=[],
                       help='install all components found in script')
    whichcomp.add_argument('--component', metavar='<component>', type=str, nargs='+',
                       help='name of component(s) to install')

    cmd_install_comp.set_defaults(func=manage_install_components)

    ######################
    # Parser for install actor cmd
    ######################
    cmd_install_actor = install_parser.add_parser('actor', help='Install actors')
    # Arguments
    cmd_install_actor.add_argument('--force', dest='force', action='store_true',
                           help='overwrite components or actor that exists at destination')
    cmd_install_actor.add_argument('--org', metavar='<name>', dest='org', type=str,
                           help='Code Signer org name used, assumes default location when no calvin.conf')
    cmd_install_actor.add_argument('--namespace', metavar='<ns.sub-ns>', type=str, required=True,
                           help='namespace to install actor or components under')

    cmd_install_actor.add_argument('--path', metavar='<path>', action='append', type=str, nargs='+', required=True,
                           help='actor file (or files) to install')

    cmd_install_actor.set_defaults(func=manage_install_actors)



    ########################################################################################
    # parser for CS cmd
    ########################################################################################
    cs_commands = ['create', 'remove', 'export', 'sign']

    cs_parser = cmdparsers.add_parser('cs', help='manage CS')
    cs_parser = cs_parser.add_subparsers(help='sub-command help', dest='cs_subparser_name')

    ######################
    #parser for cs create cmd
    ######################
    cmd_cs_create = cs_parser.add_parser('create', help='Create a Certificate Signer (CS) for signing application and actors')
    #required arguments
    cmd_cs_create.add_argument('name', metavar='<name>', type=str,
                           help='Name of the code signer')
    #optional arguments
    cmd_cs_create.add_argument('--dir', metavar='<dir>', type=str,
                           help='Path to create the cs at')
    cmd_cs_create.add_argument('--force', dest='force', action='store_true',
                           help='overwrite file that exists at destination')

    cmd_cs_create.set_defaults(func=manage_cs_create)

    ######################
    #parser for cs export cmd
    ######################
    cmd_cs_export = cs_parser.add_parser('export', help='Export the CS\'s certificate as <fingerprint>.0 in pem format')
    #required arguments
    cmd_cs_export.add_argument('name', metavar='<name>', type=str,
                           help='Name of the code signer')
    cmd_cs_export.add_argument('path', metavar='<path>', type=str,
                           help='export to directory')
    #optional arguments
    cmd_cs_export.add_argument('--force', dest='force', action='store_true',
                           help='overwrite file that exists at destination')
    cmd_cs_export.add_argument('--dir', metavar='<dir>', type=str, default="",
                           help='security directory, defaults to ~/.calvin/security')

    cmd_cs_export.set_defaults(func=manage_cs_export)


    ######################
    #parser for cs sign cmd
    ######################
    cmd_cs_sign = cs_parser.add_parser('sign', help='Sign an application or actor')
    #required arguments
    cmd_cs_sign.add_argument('name', metavar='<name>', type=str,
                           help='name of the code signer to use when signing the application/actor')
#    cmd_cs_sign.add_argument('file', metavar='<file>', type=str,
    cmd_cs_sign.add_argument('file', metavar='<file>', action='append', default=[],
                           help='path to file to be signed')
    #optional arguments
    cmd_cs_sign.add_argument('--force', dest='force', action='store_true',
                           help='overwrite file that exists at destination')
    cmd_cs_sign.add_argument('--dir', metavar='<dir>', type=str, default="",
                           help='security directory, defaults to ~/.calvin/security')
    cmd_cs_sign.add_argument('--nsfile', metavar='<ns.sub-ns.actor>', action='append', default=[],
                           help='namespaced store path to actor or components, can be repeated')

    cmd_cs_sign.set_defaults(func=manage_cs_sign)

    ########################################################################################
    # parser for CA cmd
    ########################################################################################
    ca_commands = ['create', 'export', 'enrollment_password','signCSR']

    ca_parser = cmdparsers.add_parser('ca', help='manage CA')
    ca_parser = ca_parser.add_subparsers(help='sub-command help', dest='ca_subparser_name')

    #parser for CA create cmd
    cmd_ca_create = ca_parser.add_parser('create', help='Create a Certificate Authority (CA) for transport security')
    #required arguments
    cmd_ca_create.add_argument('domain', metavar='<domain>', type=str,
                           help='Name of the domain')
    #optional arguments
    cmd_ca_create.add_argument('--dir', metavar='<dir>', type=str,
                           help='Path to create the CA at')
    cmd_ca_create.add_argument('--force', dest='force', action='store_true',
                           help='overwrite file that exists at destination')

    cmd_ca_create.set_defaults(func=manage_ca_create)


    ######################
    #parser for CA export cmd
    ######################
    cmd_ca_export = ca_parser.add_parser('export', help='Export the CA\'s root certificate as <fingerprint>.0 in pem format')
    #required arguments
    cmd_ca_export.add_argument('domain', metavar='<domain>', type=str,
                           help='Name of the domain')
    cmd_ca_export.add_argument('path', metavar='<path>', type=str,
                           help='export to directory')
    #optional arguments
    cmd_ca_export.add_argument('--force', dest='force', action='store_true',
                           help='overwrite file that exists at destination')
    cmd_ca_export.add_argument('--dir', metavar='<dir>', type=str, default="",
                           help='security directory, defaults to ~/.calvin/security')

    cmd_ca_export.set_defaults(func=manage_ca_export)

    ######################
    #parser for CA get enrollment password
    ######################
    cmd_ca_export = ca_parser.add_parser('enrollment_password',
                                         help='Get an enrollment password used for authorization when sending a CSR for a runtime')
    #required arguments
    cmd_ca_export.add_argument('domain', metavar='<domain>', type=str,
                           help='Name of the domain')
    cmd_ca_export.add_argument('node_name', metavar='<node_name>', type=str,
                           help='Name of the runtime')
    #optional arguments
    cmd_ca_export.add_argument('--force', dest='force', action='store_true',
                           help='overwrite file that exists at destination')
    cmd_ca_export.add_argument('--dir', metavar='<dir>', type=str, default="",
                           help='security directory, defaults to ~/.calvin/security')

    cmd_ca_export.set_defaults(func=manage_ca_get_enrollment_password)


    ######################
    #parser for CA signCSR cmd
    ######################
    cmd_ca_sign_csr = ca_parser.add_parser('signCSR', help='Sign a Certificate Signing Request and create certificate')
    #required arguments
    cmd_ca_sign_csr.add_argument('domain', metavar='<domain>', type=str,
                           help='name of domain for which the certificate is to be signed')
    cmd_ca_sign_csr.add_argument('CSR', metavar='<CSR>', type=str,
                           help='path to CSR to be signed')
    #optional arguments
    cmd_ca_sign_csr.add_argument('--force', dest='force', action='store_true',
                           help='overwrite file that exists at destination')
    cmd_ca_sign_csr.add_argument('--dir', metavar='<dir>', type=str, default="",
                           help='security directory, defaults to ~/.calvin/security')

    cmd_ca_sign_csr.set_defaults(func=manage_ca_sign_csr)

    ########################################################################################
    # parser for runtime cmds
    ########################################################################################
    runtime_commands = ['create', 'export', 'import', 'trust', 'c_rehash', 'get_name']

    runtime_parser = cmdparsers.add_parser('runtime', help='manage runtime certificates and keys')
    runtime_parser = runtime_parser.add_subparsers(help='sub-command help', dest='runtime_subparser_name')

    ######################
    #parser for runtime create cmd
    ######################
    cmd_runtime_create = runtime_parser.add_parser('create', help='Create a runtime keypair and a Certificate Signing Request (CSR) for transport security')
    #required arguments
    cmd_runtime_create.add_argument('domain', metavar='<domain>', type=str,
                           help='Name of the domain')
    cmd_runtime_create.add_argument('attr', metavar='<attr>', type=str,
                           help='runtime attributes, at least name and organization of node_name needs to be supplied, e.g. \'{"indexed_public":{"node_name":{"name":"testName", "organization":"testOrg"}}}\'')
    #optional arguments
    cmd_runtime_create.add_argument('--hostnames', metavar='<hostnames>', type=lambda s: [str(item) for item in s.split(',')],
                           help='Comma separated list of hostnames of the runtime where the runtime '
                                    'will execute, e.g., "examplehostname,examplehostname.localdomain.com"')
    cmd_runtime_create.add_argument('--dir', metavar='<dir>', type=str,
                           help='Path to create the runtime at')
    cmd_runtime_create.add_argument('--force', dest='force', action='store_true',
                           help='overwrite file that exists at destination')

    cmd_runtime_create.set_defaults(func=manage_runtime_create)


    ##############################
    #parser for runtime export cmd
    ##############################
    cmd_runtime_export = runtime_parser.add_parser('export', help='exports a CSR in pem format from a generated key pair')
    #required arguments
    cmd_runtime_export.add_argument('dir', metavar='<dir>', type=str,
                           help='export to directory')
    #optional arguments
    cmd_runtime_export.add_argument('--force', dest='force', action='store_true',
                           help='overwrite file that exists at destination')

    cmd_runtime_export.set_defaults(func=manage_runtime_export)

    ##############################
    #parser for runtime import cmd
    ##############################
    cmd_runtime_import = runtime_parser.add_parser('import', help='import a runtime certificate signed by the CA (generated from the CSR)')
    #required arguments
    cmd_runtime_import.add_argument('node_name', metavar='<node_name>', type=str,
                           help='Name of the runtime to configure, e.g. org.testorg----testNode1')
    cmd_runtime_import.add_argument('certificate', metavar='<certificate>', type=str,
                           help='a path to a CA signed certificate for the runtime')
    #optional arguments
    cmd_runtime_import.add_argument('--force', dest='force', action='store_true',
                           help='overwrite file that exists at destination')
    cmd_runtime_import.add_argument('--dir', metavar='<directory>', type=str, default="",
                           help='security directory, defaults to ~/.calvin/security')

    cmd_runtime_import.set_defaults(func=manage_runtime_import)


    ##############################
    # parser for runtime trust cmd
    ##############################

    cmd_runtime_trust = runtime_parser.add_parser('trust', help='manage the runtime\'s trusted certificates')
    #required arguments
    cmd_runtime_trust.add_argument('cacert', metavar='<cacert>', type=str,
                           help='path to CA certificate to trust')
    cmd_runtime_trust.add_argument('type', metavar='<type>', type=str,
                           help='flag indicating if the certificate is to be used for verification of application/actor '
                                'signatures or as root of trust for transport security. Accepted values are {"transport","code_authenticity"}')
    #optional arguments
    cmd_runtime_trust.add_argument('--dir', metavar='<directory>', type=str, default="",
                           help='security directory, defaults to ~/.calvin/security')

    cmd_runtime_trust.set_defaults(func=manage_runtime_trust)


    ##############################
    # parser for runtime c_rehash cmd
    ##############################
    cmd_runtime_c_rehash = runtime_parser.add_parser('c_rehash', help='Create symbolic links to trusted certificates')
    #required arguments
    cmd_runtime_c_rehash.add_argument('type', metavar='<type>', type=str,
                           help='Type of trust store to rehash, supported are {CA, CS}')
    #optional arguments
    cmd_runtime_c_rehash.add_argument('--dir', metavar='<directory>', type=str, default="",
                           help='security directory, defaults to ~/.calvin/security')

    cmd_runtime_c_rehash.set_defaults(func=manage_runtime_c_rehash)

    ##############################
    # parser for runtime get_name
    ##############################
    cmd_runtime_c_rehash = runtime_parser.add_parser('get_name', help='Create symbolic links to trusted certificates')
    #required arguments
    #optional arguments
    cmd_runtime_c_rehash.add_argument('--attr', metavar='<attr>', type=str,
                           help='JSON coded attributes for started node '
                                'e.g. \'{"indexed_public": {"owner": {"personOrGroup": "Me"}}}\''
                                ', see documentation',
                           dest='attr', default=None)

    cmd_runtime_c_rehash.add_argument('--attr-file', metavar='<attr>', type=str,
                           help='File with JSON coded attributes for started node '
                                'e.g. \'{"indexed_public": {"owner": {"personOrGroup": "Me"}}}\''
                                ', see documentation',
                           dest='attr_file', default=None)
    cmd_runtime_c_rehash.set_defaults(func=manage_runtime_get_name)




    return argparser.parse_args()

################################
# manage Component Installation
################################

def manage_install(args):

    if args.cmd == 'actor':
        manage_install_actors(args)
    else:
        manage_install_components(args)

def manage_install_actors(args):
    sys.stderr.write("Installing actors not yet supported\n")
    return 1


def manage_install_components(args):

    def get_components(filename, names):
        try:
            with open(filename, 'r') as source:
                source_text = source.read()
        except:
            from calvin.utilities.issuetracker import IssueTracker
            it = IssueTracker()
            it.add_error('File not found', {'script': filename})
            return [], it
        return calvin_components(source_text, names)

    comps, issuetracker = get_components(args.script, args.component)


    if issuetracker.error_count:
        issuetracker.add_warning('Nothing installed', {'script': args.script})
    else:
        for comp in comps:
            if not install_component(args.namespace, comp, args.force):
                if args.force:
                    issuetracker.add_error('Failed to install "{0}"'.format(comp.name))
                else:
                    issuetracker.add_error("Failed to install '{0}', use '--force' to replace existing components".format(comp.name))

    for issue in issuetracker.formatted_errors(sort_key='line', custom_format=args.fmt, script=args.script, line=0, col=0):
        sys.stderr.write(issue + "\n")
    for issue in issuetracker.formatted_warnings(sort_key='line', custom_format=args.fmt, script=args.script, line=0, col=0):
        sys.stderr.write(issue + "\n")

    if issuetracker.error_count:
        return 1


################################
# manage Certificate Authority
################################

def manage_ca_create(args):
    if not args.domain:
        raise Exception("No domain supplied")
    certificate_authority.CA(domain=args.domain, commonName=args.domain+" CA", security_dir=args.dir, force=args.force)

def manage_ca_remove(args):
    if not args.domain:
        raise Exception("No domain supplied")
    domaindir = os.path.join(args.dir, args.domain) if args.dir else None
    certificate.remove_domain(args.domain, domaindir)

def manage_ca_export(args):
    if not args.domain:
        raise Exception("No domain supplied")
    if not args.path:
        raise Exception("No out path supplied")
    ca = certificate_authority.CA(domain=args.domain, security_dir=args.dir, readonly=True)
    out_file = ca.export_ca_cert(args.path)
    print "exported to:" + out_file

def manage_ca_get_enrollment_password(args):
    if args.domain and args.node_name:
        if not args.domain:
            raise Exception("No domain supplied")
        if not args.node_name:
            raise Exception("supply node name")
        ca = certificate_authority.CA(domain=args.domain, security_dir=args.dir, force=args.force)
        enrollment_password = ca.cert_enrollment_add_new_runtime(args.node_name)
        print "enrollment_password_start<{}>enrollment_password_stop".format(enrollment_password)

def manage_ca_sign_csr(args):
    if not args.domain:
        raise Exception("No domain supplied")
    if not args.CSR:
        raise exception("supply path to CSR")
    exist = os.path.isfile(args.CSR)
    if not exist:
        raise Exception("The CSR path supplied is not an existing file")
    ca = certificate_authority.CA(domain=args.domain, security_dir=args.dir, force=args.force)
    cert_path = ca.sign_csr(args.CSR)
    print "signed_cert_path_start<{}>signed_cert_path_stop".format(cert_path)

######################
# manage Code Signer
######################

def manage_cs_create(args):
    if not args.name:
        raise Exception("No name of code signer supplied")
    code_signer.CS(organization=args.name, commonName=args.name+"CS", security_dir=args.dir, force=args.force)

def manage_cs_remove(args):
    if not args.name:
        raise Exception("No code signer name supplied")
    code_signer.remove_cs(args.nane, security_dir=args.dir)

def manage_cs_export(args):
    if not args.name:
        raise Exception("No code signer name supplied")
    if not args.path:
        raise Exception("No out path supplied")
    cs = code_signer.CS(organization=args.name, commonName=args.name+"CS", security_dir=args.dir, force=args.force)
    out_file = cs.export_cs_cert(args.path)
    print "exported to:" + out_file

def manage_cs_sign(args):
    if not args.name:
        raise Exception("No code signer name supplied")
    if not args.file:
        raise Exception("supply path to a file(s) to sign")
    cs = code_signer.CS(organization=args.name, commonName=args.name+"CS", security_dir=args.dir, force=args.force)
    # Collect files to sign
    files = []
    if args.file:
        for f in args.file:
            exist = os.path.isfile(f)
            if not exist:
                raise Exception("The file path supplied is not an existing file")
            files.extend(glob.glob(f))
    if args.nsfile:
        store = ActorStore()
        for m in args.nsfile:
            files.extend(store.actor_paths(m))
    # Filter out any files not *.calvin, *.py
    files = [f for f in files if f.endswith(('.calvin', '.py')) and not f.endswith('__init__.py')]
    if not files:
        raise Exception("No (*.calvin, *.py) files supplied")
    exceptions = []
    for f in files:
        try:
            cs.sign_file(f)
        except Exception as e:
            exceptions.append(e)
    for e in exceptions:
        print "Error {}".format(e)



######################
# manage runtime
######################

def manage_runtime_create(args):
    if not args.attr:
        raise Exception("No runtime attributes supplied")
    if not args.domain:
        raise Exception("No domain name supplied")
    if args.hostnames and len(args.hostnames)>4:
        raise Exception("At most 3 hostnames can be supplied")
    attr = json.loads(args.attr)
    if not all (k in attr['indexed_public']['node_name'] for k in ("organization","name")):
        raise Exception("please supply name and organization of runtime")
    attributes=AttributeResolver(attr)
    node_name=attributes.get_node_name_as_str()
    nodeid = calvinuuid.uuid("NODE")
    rt_cred = runtime_credentials.RuntimeCredentials(node_name, domain=args.domain, security_dir=args.dir, nodeid=nodeid, hostnames=args.hostnames)
    print "node_name_start<{}>node_name_stop".format(rt_cred.get_node_name())

def manage_runtime_export(args):
    raise Exception("manage_runtime_export is not yet implemented")

def manage_runtime_remove(args):
    if not args.domain:
        raise Exception("No domain supplied")
    domaindir = os.path.join(args.dir, args.domain) if args.dir else None
    runtime = runtime_credentials.RuntimeCredentials(args.node_name, security_dir=args.dir)
    runtime.remove_runtime(args.node_name, domaindir)

def manage_runtime_import(args):
    if not args.node_name:
        raise Exception("No node name supplied")
    if not args.certificate:
        raise Exception("No certificate supplied")
    runtime = runtime_credentials.RuntimeCredentials(args.node_name, security_dir=args.dir)
    cert_path = runtime.store_own_cert(certpath=args.certificate)
    print "cert_path_start<{}>cert_path_stop".format(cert_path)

def manage_runtime_trust(args):
    if not args.cacert:
        raise Exception("No path to CA cert supplied")
    if not args.type:
        raise Exception("No type supplied")
    if args.type=="transport":
        certificate.store_trusted_root_cert(args.cacert, "truststore_for_transport", security_dir=args.dir)
    elif args.type=="code_authenticity":
        certificate.store_trusted_root_cert(args.cacert, "truststore_for_signing", security_dir=args.dir)

def manage_runtime_c_rehash(args):
    if args.type=="CA":
        certificate.c_rehash(type=certificate.TRUSTSTORE_TRANSPORT, security_dir=args.dir)
    elif args.type=="CS":
        certificate.c_rehash(type=certificate.TRUSTSTORE_SIGN, security_dir=args.dir)
    else:
        print "Error, only type={CA, CS} are suppored"

def manage_runtime_get_name(args):
    from calvin.utilities.attribute_resolver import AttributeResolver
    # Attributes
    runtime_attr = {}

    if args.attr_file:
        try:
            runtime_attr = json.load(open(args.attr_file))
        except Exception as e:
            print "Attribute file not JSON:\n", e
            return -1
    elif args.attr:
        try:
            runtime_attr = json.loads(args.attr)
        except Exception as e:
            print "Attributes not JSON:\n", e
            return -1
    else:
        print "Error, either supply the attributes of the runtime, or the path to the file containg the attributes"
        return -1

    attributes = AttributeResolver(runtime_attr)
    print "node_name_start<{}>node_name_stop\n".format(attributes.get_node_name_as_str())



def main():
    args = parse_args()

    try:
        args.func(args)
    except Exception as e:
        print "Error {}".format(e)

if __name__ == '__main__':
    sys.exit(main())
