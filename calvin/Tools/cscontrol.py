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
import requests
import json


def jsonprint(s):
    print(json.dumps(json.loads(s), indent=2))


def control_id(args):
    return requests.get(args.node + "/id")


def get_nodes_with_attribute(control_uri, attribute):
    req = requests.get(control_uri + "/index/" + attribute)
    print("reply: %s" % (req.text))
    nodes = json.loads(req.text)
    if not nodes or not isinstance(nodes.get("result"), list):
        raise Exception("No node with attribute {} found".format(attribute))
    return nodes.get("result")


def get_node_info(control_uri, node_id):
    req = requests.get(control_uri + "/node/" + node_id)
    nodeinfo = json.loads(req.text)
    if isinstance(nodeinfo, dict):
        return nodeinfo
    raise Exception("No node with id {} found".format(node_id))


def get_node_control_uri(control_uri, node_id):
    nodeinfo = get_node_info(control_uri, node_id)
    return nodeinfo.get("control_uri")


def get_node_with_attribute(control_uri, attribute):
    import random
    nodes = get_nodes_with_attribute(control_uri, attribute)

    node = None
    # pick one (with a control uri)
    while nodes:
        node_id = random.choice(nodes)
        nodes.remove(node_id)
        other_control_uri = get_node_control_uri(control_uri, node_id)
        if other_control_uri:
            node = other_control_uri
            break
    return node


def control_deploy(args):
    data = {"name": args.script.name, "script": args.script.read()}
    if args.attr:
        node = get_node_with_attribute(args.node, args.attr)
    else:
        node = args.node
    return requests.post(node + "/deploy", data=json.dumps(data))


def control_actors(args):
    if args.cmd == 'list':
        return requests.get(args.node + "/actors")
    if args.cmd == 'info':
        if not args.id:
            raise Exception("No actor id given")
        return requests.get(args.node + "/actor/" + args.id)
    elif args.cmd == 'delete':
        if not args.id:
            raise Exception("No actor id given")
        return requests.delete(args.node + "/actor/" + args.id)
    elif args.cmd == 'migrate':
        if not args.id or not args.peer_node:
            raise Exception("No actor or peer given")
        data = {"peer_node_id": args.peer_node}
        return requests.post(args.node + "/actor/" + args.id + "/migrate", data=json.dumps(data))


def control_applications(args):
    if args.cmd == 'list':
        return requests.get(args.node + "/applications")
    elif args.cmd == 'delete':
        if not args.id:
            raise Exception("No application id given")
        return requests.delete(args.node + "/application/" + args.id)


def control_nodes(args):
    if args.cmd == 'list':
        return requests.get(args.node + "/nodes")
    elif args.cmd == 'add':
        data = {"peers": args.peerlist}
        return requests.post(args.node + "/peer_setup", data=json.dumps(data))
    elif args.cmd == 'stop':
        return requests.delete(args.node + "/node")


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
    cmd_deploy.add_argument("script", metavar="<calvin script>", type=file,
                            help="script to be deployed")
    cmd_deploy.add_argument('-a', '--attr', metavar="<attribute>", type=str, dest="attr",
                               help="Will deploy script to a random node with the given attribute")
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
    jsonprint(args.func(args).text)

if __name__ == '__main__':
    main()
