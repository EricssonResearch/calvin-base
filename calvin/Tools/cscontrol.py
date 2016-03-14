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

import argparse
import json
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.security import Security
from calvin.utilities import certificate

_log = get_logger(__name__)
_request_handler = None


def get_request_handler():
    from calvin.requests.request_handler import RequestHandler
    return _request_handler if _request_handler else RequestHandler()


def control_id(args):
    return get_request_handler().get_node_id(args.node)


def get_node_info(control_uri, node_id):
    try:
        return get_request_handler().get_node(control_uri, node_id)
    except:
        raise Exception("No node with id {} found".format(node_id))


def get_node_control_uri(control_uri, node_id):
    nodeinfo = get_node_info(control_uri, node_id)
    return nodeinfo.get("control_uri")


def requirements_file(path):
    """ Reads in a requirements file of JSON format with the structure:
        {<actor_name>: [(<req_op>, <req_args>), ...], ...}

        Needs to be called after the initial deployment to get the actor_ids
    """
    reqs = None
    try:
        reqs = json.load(open(path, 'r'))
    except:
        _log.exception("Failed JSON file")
    if not reqs or not isinstance(reqs, dict):
        _log.error("Failed loading deployment requirements file %s" % path)
        return {}
    return reqs


def control_deploy(args):
    response = None
    print args
    reqs = requirements_file(args.reqs) if args.reqs else None
    if args.signer:
        conf = certificate.Config(configfile=None, domain=args.signer, readonly=True)
        certificate.sign_file(conf, args.script.name)
    sourceText = args.script.read()
    credentials_ = None
    content = None
    if args.credentials:
        try:
            credentials_ = json.loads(args.credentials)
        except Exception as e:
            print "Credentials not JSON:\n", e
            return -1
        if credentials_:
            content = Security.verify_signature_get_files(args.script.name, skip_file=True)
            if content:
                content['file'] = sourceText
    try:
        response = get_request_handler().deploy_application(args.node, args.script.name, sourceText, reqs,
                                            credentials=credentials_, content=content, check=args.check)
    except Exception as e:
        print e
    return response


def control_actors(args):
    if args.cmd == 'list':
        return get_request_handler().get_actors(args.node)
    if args.cmd == 'info':
        if not args.id:
            raise Exception("No actor id given")
        return get_request_handler().get_actor(args.node, args.id)
    elif args.cmd == 'delete':
        if not args.id:
            raise Exception("No actor id given")
        return get_request_handler().delete_actor(args.node, args.id)
    elif args.cmd == 'migrate':
        if not args.id or not args.peer_node:
            raise Exception("No actor or peer given")
        return get_request_handler().migrate(args.node, args.id, args.peer_node)


def control_applications(args):
    if args.cmd == 'info':
        if not args.id:
            raise Exception("No application id given")
        return get_request_handler().get_application(args.node, args.id)
    elif args.cmd == 'list':
        return get_request_handler().get_applications(args.node)
    elif args.cmd == 'delete':
        if not args.id:
            raise Exception("No application id given")
        return get_request_handler().delete_application(args.node, args.id)


def control_nodes(args):
    from requests.exceptions import ConnectionError
    if args.cmd == 'info':
        if not args.id:
            raise Exception("No node id given")
        return get_request_handler().get_node(args.node, args.id)
    elif args.cmd == 'list':
        return get_request_handler().get_nodes(args.node)
    elif args.cmd == 'add':
        return get_request_handler().peer_setup(args.node, *args.peerlist)
    elif args.cmd == 'stop':
        try:
            return get_request_handler().quit(args.node)
        except ConnectionError:
            # If the connection goes down before response that is OK
            return None


def control_storage(args):
    from calvin.utilities.attribute_resolver import format_index_string
    import json
    request_handler = get_request_handler()
    if args.cmd == 'get_index':
        try:
            index = json.loads(args.index)
        except:
            raise Exception("Malformed JSON index string:\n%s" % args.index)
        formated_index = format_index_string(index)
        return request_handler.get_index(args.node, formated_index)
    elif args.cmd == 'raw_get_index':
        try:
            index = json.loads(args.index)
        except:
            raise Exception("Malformed JSON index string:\n%s" % args.index)
        return request_handler.get_index(args.node, index)


def parse_args():
    long_desc = """Send control commands to calvin runtime"""
    # top level arguments
    argparser = argparse.ArgumentParser(description=long_desc)
    argparser.add_argument('node', metavar="<control uri>",
                           help="control uri of node")
    cmdparsers = argparser.add_subparsers(help="command help")

    # parser for id cmd
    cmd_id = cmdparsers.add_parser('id', help="get id of node", description="Get id of node")
    cmd_id.set_defaults(func=control_id)

    # parser for nodes cmd
    node_commands = ['info', 'list', 'add', 'stop']

    cmd_nodes = cmdparsers.add_parser('nodes', help='handle node peers')
    cmd_nodes.add_argument('cmd', metavar='<command>', choices=node_commands, type=str,
                           help="one of %s" % ", ".join(node_commands))
    info_group = cmd_nodes.add_argument_group('info')
    info_group.add_argument('id', metavar='<node id>', nargs='?', help="id of node to get info about")
    list_group = cmd_nodes.add_argument_group('add')
    list_group.add_argument('peerlist', metavar='<peerlist>', nargs='*', default=[],
                            help="list of peers of the form calvinip://<address>:<port>")
    cmd_nodes.set_defaults(func=control_nodes)

    # parser for deploy
    cmd_deploy = cmdparsers.add_parser('deploy', help="deploy script to node")
    cmd_deploy.add_argument("script", metavar="<calvin script>", type=argparse.FileType('r'),
                            help="script to be deployed")
    cmd_deploy.add_argument('-c', '--no-check', dest='check', action='store_false', default=True,
                           help='Don\'t verify if actors or components are correct, ' +
                                'allows deployment of actors not known on the node')
    cmd_deploy.add_argument('--credentials', metavar='<credentials>', type=str,
                           help='Supply credentials to run program under '
                                'e.g. \'{"user":"ex_user", "password":"passwd"}\'',
                           dest='credentials', default=None)

    cmd_deploy.add_argument('--sign-org', metavar='<signer>', type=str,
                           help='Sign the app before deploy, using this code signing organization name supplied',
                           dest='signer', default=None)

    cmd_deploy.add_argument('--reqs', metavar='<reqs>', type=str,
                            help='deploy script, currently JSON coded data file',
                            dest='reqs')
    cmd_deploy.set_defaults(func=control_deploy)

    # parsers for actor commands
    actor_commands = ['info', 'list', 'delete', 'migrate']
    cmd_actor = cmdparsers.add_parser('actor', help="handle actors on node")
    cmd_actor.add_argument('cmd', metavar="<command>", choices=actor_commands, type=str,
                           help="one of %s" % (", ".join(actor_commands)))
    cmd_actor.add_argument('id', metavar="<actor id>", type=str, nargs='?', default=None,
                           help="id of actor")
    cmd_actor.add_argument('peer_node', metavar="<peer node id>", type=str, nargs='?', default=None,
                           help="id of destination peer")
    cmd_actor.set_defaults(func=control_actors)

    # parser for applications
    app_commands = ['info', 'list', 'delete']
    cmd_apps = cmdparsers.add_parser('applications', help="handle applications deployed on node")
    cmd_apps.add_argument("cmd", metavar="<command>", choices=app_commands, type=str,
                          help="one of %s" % (", ".join(app_commands)))
    cmd_apps.add_argument("id", metavar="<app id>", type=str, nargs='?')
    cmd_apps.set_defaults(func=control_applications)

    # parser for applications
    storage_commands = ['get_index', 'raw_get_index']
    cmd_storage = cmdparsers.add_parser('storage', help="handle storage")
    cmd_storage.add_argument("cmd", metavar="<command>", choices=storage_commands, type=str,
                             help="one of %s" % (", ".join(storage_commands)))
    cmd_storage.add_argument("index", metavar="<index>",
                             help="An index e.g. '[\"owner\", {\"personOrGroup\": \"Me\"}}]'", type=str, nargs='?')
    cmd_storage.set_defaults(func=control_storage)

    return argparser.parse_args()


def main():
    args = parse_args()
    try:
        r =  args.func(args)
        print "OK" if r is None else r
    except Exception as e:
        print "Error {}".format(e)
if __name__ == '__main__':
    main()
