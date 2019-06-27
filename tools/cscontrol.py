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
import argparse
import json

from calvin.common.calvinlogger import get_logger
from calvin.common.attribute_resolver import format_index_string
from .toolsupport.control_client import ControlAPI, ConnectionError

_log = get_logger(__name__)


def requirements_file(path):
    """ Reads in a requirements file of JSON format with the structure:
        {<actor_name>: [(<req_op>, <req_args>), ...], ...}

        Needs to be called after the initial add_argument to get the actor_ids
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


# Core
def control_id(args):
    req_handler = ControlAPI()
    status, response = req_handler.get_node_id(args.node)
    return status, response['id']

# Core
def control_deploy(args):
    req_handler = ControlAPI()
    with open(args.app, 'r') as fd:
        deployable = json.load(fd)
    return req_handler.deploy(args.node, deployable)

# Core
def control_actors(args):
    req_handler = ControlAPI()
    if args.cmd == 'list':
        return req_handler.get_actors(args.node)
    if args.cmd == 'info':
        if not args.id:
            raise Exception("No actor id given")
        return req_handler.get_actor(args.node, args.id)
    elif args.cmd == 'migrate':
        if not args.id or not args.peer_node:
            raise Exception("No actor or peer given")
        return req_handler.migrate(args.node, args.id, args.peer_node)

# Core
def control_applications(args):
    req_handler = ControlAPI()
    if args.cmd == 'info':
        if not args.id:
            raise Exception("No application id given")
        return req_handler.get_application(args.node, args.id)
    elif args.cmd == 'list':
        return req_handler.get_applications(args.node)
    elif args.cmd == 'delete':
        if not args.id:
            raise Exception("No application id given")
        return req_handler.delete_application(args.node, args.id)
    elif args.cmd == 'migrate':
        if not args.id:
            raise Exception("No application id given")
        deploy_info = requirements_file(args.reqs) if args.reqs else None
        return req_handler.migrate_app_use_req(rt=args.node, application_id=args.id, deploy_info=deploy_info)

# Core
def control_nodes(args):
    req_handler = ControlAPI()
    if args.cmd == 'info':
        if not args.id:
            raise Exception("No node id given")
        return req_handler.get_node(args.node, args.id)
    elif args.cmd == 'list':
        return req_handler.get_nodes(args.node)
    elif args.cmd == 'stop':
        try:
            return req_handler.quit(args.node)
        except ConnectionError:
            # If the connection goes down before response that is OK
            return 200, None


# Core
def control_storage(args):
    req_handler = ControlAPI()
    if args.cmd == 'get_index':
        try:
            index = json.loads(args.index)
        except:
            raise Exception("Malformed JSON index string:\n%s" % args.index)
        formated_index = format_index_string(index)
        return req_handler.get_index(args.node, formated_index)
    elif args.cmd == 'raw_get_index':
        try:
            index = json.loads(args.index)
        except:
            raise Exception("Malformed JSON index string:\n%s" % args.index)
        return req_handler.get_index(args.node, index)


def parse_args():
    long_desc = """Send control commands to calvin runtime"""
    # top level arguments
    argparser = argparse.ArgumentParser(description=long_desc)
    argparser.add_argument('node', metavar="<control uri>",
                           help="control uri of node")
    # argparser.add_argument('--credentials', metavar='<credentials>', type=str,
    #                        help='Supply credentials to run program under '
    #                             'e.g. \'{"user":"ex_user", "password":"passwd"}\'',
    #                        dest='credentials', default=None)
    # argparser.add_argument('--security_dir', metavar='<security_dir>', type=str,
    #                        help='Path to the runtimes credentials dir if not using the default location',
    #                        dest='security_dir', default=None)
    cmdparsers = argparser.add_subparsers()

    # parser for id cmd
    cmd_id = cmdparsers.add_parser('id', help="get id of node", description="Get id of node")
    cmd_id.set_defaults(func=control_id)

    # parser for nodes cmd
    node_commands = ['info', 'list', 'stop']

    cmd_nodes = cmdparsers.add_parser('nodes', help='handle node peers')
    cmd_nodes.add_argument('cmd', metavar='<command>', choices=node_commands, type=str,
                           help="one of %s" % ", ".join(node_commands))
    info_group = cmd_nodes.add_argument_group('info')
    info_group.add_argument('id', metavar='<node id>', nargs='?', help="id of node to get info about")
    cmd_nodes.set_defaults(func=control_nodes)


    # parser for deploy
    cmd_deploy = cmdparsers.add_parser('deploy', help="deploy app to node")
    cmd_deploy.add_argument("app", metavar="<calvin app>", type=str,
                            help="compiled app to be deployed")
    cmd_deploy.set_defaults(func=control_deploy)


    # parsers for actor commands
    actor_commands = ['info', 'list', 'migrate']
    cmd_actor = cmdparsers.add_parser('actor', help="handle actors on node")
    cmd_actor.add_argument('cmd', metavar="<command>", choices=actor_commands, type=str,
                           help="one of %s" % (", ".join(actor_commands)))
    cmd_actor.add_argument('id', metavar="<actor id>", type=str, nargs='?', default=None,
                           help="id of actor")
    cmd_actor.add_argument('peer_node', metavar="<peer node id>", type=str, nargs='?', default=None,
                           help="id of destination peer")
    cmd_actor.set_defaults(func=control_actors)

    # parser for applications
    app_commands = ['info', 'list', 'delete', 'migrate']
    cmd_apps = cmdparsers.add_parser('applications', help="handle applications deployed on node")
    cmd_apps.add_argument("cmd", metavar="<command>", choices=app_commands, type=str,
                          help="one of %s" % (", ".join(app_commands)))
    cmd_apps.add_argument("id", metavar="<app id>", type=str, nargs='?')
    cmd_apps.add_argument('--reqs', metavar='<reqs>', type=str,
                            help='deploy script, currently JSON coded data file (when migrating)',
                            dest='reqs')
    
    cmd_apps.set_defaults(func=control_applications)

    # parser for applications
    storage_commands = ['get_index', 'raw_get_index']
    cmd_storage = cmdparsers.add_parser('storage', help="handle storage")
    cmd_storage.add_argument("cmd", metavar="<command>", choices=storage_commands, type=str,
                             help="one of %s" % (", ".join(storage_commands)))
    cmd_storage.add_argument("index", metavar="<index>",
                             help="An index e.g. '[\"owner\", {\"personOrGroup\": \"Me\"}]'", type=str, nargs='?')
    cmd_storage.set_defaults(func=control_storage)

    return argparser.parse_args()


def main():
    args = parse_args()
    try:
        status, retval =  args.func(args)
        if status < 200 or status > 206:
            print("Error status: {} with response:\n{}".format(status, response))
        else:
            print("OK" if retval is None else json.dumps(retval, indent=2))
    except Exception as e:
        print("Error {}".format(e))
if __name__ == '__main__':
    main()
