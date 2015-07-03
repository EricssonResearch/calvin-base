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
import deployer
import select
import time
import traceback
import cscompiler as compiler
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import utils
from calvin.utilities.nodecontrol import dispatch_node, node_control
import logging
import random

_log = get_logger(__name__)

def parse_arguments():
    long_description = """
Start runtime, compile calvinscript and deploy application.
  """

    argparser = argparse.ArgumentParser(description=long_description)

    argparser.add_argument('-n', '--host', metavar='<host>', type=str,
                           help='ip address/hostname of calvin runtime',
                           dest='host', default='localhost')

    argparser.add_argument('--peer', metavar='<calvin uri>', dest='peer',
                           help="add peer to calvin runtime")

    argparser.add_argument('-p', '--port', metavar='<port>', type=int, dest='port',
                           help='port# of calvin runtime', default=5000)

    argparser.add_argument('-c', '--controlport', metavar='<port>', type=int, dest='controlport',
                           help='port# of control interface', default=5001)

    argparser.add_argument('file', metavar='<filename>', type=str, nargs='?',
                           help='source file to compile')

    argparser.add_argument('-d', '--debug', dest='debug', action='store_true',
                           help='Start PDB')

    argparser.add_argument('-l', '--loglevel', dest='loglevel', action='append', default=[],
                           help="Set log level, levels: CRITICAL, ERROR, WARNING, INFO and DEBUG. \
                           To enable on specific modules use 'module:level'")

    argparser.add_argument('-w', '--wait', dest='wait', metavar='sec', default=2,
                           help='wait for sec seconds before quitting (0 means forever).')

    argparser.add_argument('--deploy-only', dest='runtime', action='store_false',
                           help='do not start a new runtime')

    argparser.add_argument('--start-only', dest='deploy', action='store_false',
                           help='start runtime without deploying an application')

    argparser.add_argument('--keep-alive', dest='wait', action='store_const', const=0,
                           help='run forever (equivalent to -w 0 option).')

    argparser.add_argument('--kill', dest='appid', metavar='appid',
                           help="stop application")

    argparser.add_argument('--attr', metavar='<attr>', type=str,
                           help='a comma seperate list of attributes for started node ' +
                                'e.g. node/affiliation/owner/me,node/affiliation/name/bot',
                           dest='attr')

    argparser.add_argument('--deploy-to', metavar='<attr>', type=str,
                           help='an attribute of an existing node to deploy to, ' +
                                'will pick a random node from attribute lookup, ' +
                                'e.g. node/affiliation/owner/me',
                           dest='to_attr')

    return argparser.parse_args()


def runtime(uri, control_uri, start_new, attributes=None):
    if start_new:
        kwargs = {'attributes': attributes} if attributes else {}
        rt = dispatch_node(uri=uri, control_uri=control_uri, **kwargs)
    else:
        rt = node_control(control_uri)
    return rt


def compile(scriptfile):
    _log.debug("Compiling %s ..." % file)
    app_info, errors, warnings = compiler.compile_file(scriptfile)
    if errors:
        _log.error("{reason} {script} [{line}:{col}]".format(script=file, **errors[0]))
        return False
    return app_info


def deploy(rt, app_info, loglevel):
    d = {}
    try:
        d = deployer.Deployer(rt, app_info)
        d.deploy()
    except Exception:
        time.sleep(0.1)
        if get_logger().getEffectiveLevel <= logging.DEBUG:
            traceback.print_exc()
    return d.app_id


def get_control_uri_from_index(rt, deploy_to):
    node_ids = utils.get_index(rt, deploy_to)
    if not isinstance(node_ids, list) or not node_ids:
        # No list of node ids
        return None
    while(node_ids):
        node_id = random.choice(node_ids)
        node_ids.remove(node_id)
        node_info = utils.get_node(rt, node_id)
        if isinstance(node_info, dict) and 'control_uri' in node_info:
            return node_info['control_uri']
    return None


def set_loglevel(levels):
    if not levels:
        get_logger().setLevel(logging.INFO)
    else:
        for level in levels:
            module = None
            if ":" in level:
                module, level = level.split(":")
            if level == "CRITICAL":
                get_logger(module).setLevel(logging.CRITICAL)
            elif level == "ERROR":
                get_logger(module).setLevel(logging.ERROR)
            elif level == "WARNING":
                get_logger(module).setLevel(logging.WARNING)
            elif level == "INFO":
                get_logger(module).setLevel(logging.INFO)
            elif level == "DEBUG":
                get_logger(module).setLevel(logging.DEBUG)


def main():
    args = parse_arguments()

    if args.debug:
        import pdb ; pdb.set_trace()

    set_loglevel(args.loglevel)

    add_peer = args.peer
    kill_app = args.appid and not add_peer
    start_runtime = args.runtime and not kill_app and not add_peer
    deploy_app = args.deploy and args.file and not kill_app

    app_info = None
    if deploy_app:
        app_info = compile(args.file)
        if not app_info:
            return 1

    uri = "calvinip://%s:%d" % (args.host, args.port)
    control_uri = "http://%s:%d" % (args.host, args.controlport)

    attr_list = None
    if args.attr:
        attr_list = args.attr.split(',')

    rt = runtime(uri, control_uri, start_runtime, attr_list)
    # Default we deploy to the specified runtime
    deploy_rt = rt

    # When deploy-to option get the deploy runtime from index,
    # but need the first runtime to have access to the storage
    if args.to_attr:
        # If we started a new runtime above let it first connect the storage
        time.sleep(2)
        deploy_rt_control_uri = get_control_uri_from_index(rt, args.to_attr)
        if deploy_rt_control_uri:
            deploy_rt = runtime(None, deploy_rt_control_uri, False, [])

    if add_peer:
        res = utils.peer_setup(deploy_rt, [args.peer])
        print res
        return 0

    if args.appid:
        res = utils.delete_application(deploy_rt, args.appid)
        print res['result']
        return 0

    app_id = None
    if deploy_app:
        app_id = deploy(deploy_rt, app_info, args.loglevel)

    if start_runtime:
        # FIXME: This is a weird construct that is required since python's
        #        MultiProcess will reap all it's children on exit, regardless
        #        of deamon attribute value
        timeout = int(args.wait) if int(args.wait) else None
        select.select([], [], [], timeout)
        utils.quit(rt)
        time.sleep(0.1)

    if app_id:
        print "Deployed application", app_id

if __name__ == '__main__':
    main()
