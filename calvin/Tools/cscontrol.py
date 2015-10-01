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
import calvin.utilities.utils as utils
import os
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import calvinresponse
import logging

_log = get_logger(__name__)


def control_id(args):
    return utils.get_node_id(args.node)


def get_node_info(control_uri, node_id):
    try:
        return utils.get_node(control_uri, node_id)
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
        reqs = json.load(open(path,'r'))
    except:
        _log.exception("Failed JSON file")
    if not reqs or not isinstance(reqs, dict):
        _log.error("Failed loading deployment requirements file %s" % path)
        return {}
    return reqs

def control_deploy(args):
    response = None
    print args
    try:
        response = utils.deploy_application(args.node, args.script.name, args.script.read())
    except Exception as e:
        print e
    if isinstance(response, dict) and "application_id" in response and args.reqs:
        reqs = requirements_file(args.reqs)
        if reqs:
            try:
                result = utils.add_requirements(args.node, response["application_id"], reqs)
                _log.debug("Succeeded with applying deployment requirements %s\n" % result['placement'])
            except:
                _log.error("Applying deployment requirement from file %s failed" % args.reqs)
                print ("Applying deployment requirement from file %s failed" % args.reqs)
    return response

def control_actors(args):
    if args.cmd == 'list':
        return utils.get_actors(args.node)
    if args.cmd == 'info':
        if not args.id:
            raise Exception("No actor id given")
        return utils.get_actor(args.node, args.id)
    elif args.cmd == 'delete':
        if not args.id:
            raise Exception("No actor id given")
        return utils.delete_actor(args.node, args.id)
    elif args.cmd == 'migrate':
        if not args.id or not args.peer_node:
            raise Exception("No actor or peer given")
        return utils.migrate(args.node, args.id, args.peer_node)


def control_applications(args):
    if args.cmd == 'list':
        return utils.get_applications(args.node)
    elif args.cmd == 'delete':
        if not args.id:
            raise Exception("No application id given")
        return utils.delete_application(args.node, args.id)


def control_nodes(args):
    if args.cmd == 'list':
        return utils.get_nodes(args.node)
    elif args.cmd == 'add':
        return utils.peer_setup(args.node, *args.peerlist)
    elif args.cmd == 'stop':
        return utils.quit(args.node)


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
    node_commands = ['list', 'add', 'stop']

    cmd_nodes = cmdparsers.add_parser('nodes', help='handle node peers')
    cmd_nodes.add_argument('cmd', metavar='<command>', choices=node_commands, type=str,
                           help="one of %s" % ", ".join(node_commands))
    cmd_nodes.add_argument('peerlist', metavar='<peer>', nargs='*', default=[],
                           help="list of peers of the form calvinip://<address>:<port>")
    cmd_nodes.set_defaults(func=control_nodes)

    # parser for deploy
    cmd_deploy = cmdparsers.add_parser('deploy', help="deploy script to node")
    cmd_deploy.add_argument("script", metavar="<calvin script>", type=argparse.FileType('r'),
                            help="script to be deployed")
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
    app_commands = ['list', 'delete']
    cmd_apps = cmdparsers.add_parser('applications', help="handle applications deployed on node")
    cmd_apps.add_argument("cmd", metavar="<command>", choices=app_commands, type=str,
                          help="one of %s" % (", ".join(app_commands)))
    cmd_apps.add_argument("id", metavar="<app id>", type=str, nargs='?')
    cmd_apps.set_defaults(func=control_applications)

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
