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
from calvin.utilities import dtrace
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import utils
from calvin.utilities.nodecontrol import dispatch_node, node_control
import logging


_log = get_logger(__name__)

dtrace._trace_on = True
dtrace._marker = "|   "
dtrace._indent_size = 1


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
                           help='keep debugging information from compilation')

    argparser.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                           help='print extra information during deployment')

    argparser.add_argument('-w', '--wait', dest='wait', metavar='sec', default=2,
                           help='wait for sec seconds before quitting (0 means forever).')

    argparser.add_argument('-q', '--quiet', action='store_const', const=0, dest='quiet',
                           help='quiet, no output')

    argparser.add_argument('--deploy-only', dest='runtime', action='store_false',
                           help='do not start a new runtime')

    argparser.add_argument('--start-only', dest='deploy', action='store_false',
                           help='start runtime without deploying an application')

    argparser.add_argument('--keep-alive', dest='wait', action='store_const', const=0,
                           help='run forever (equivalent to -w 0 option).')

    argparser.add_argument('--kill', dest='appid', metavar='appid',
                           help="stop application")

    return argparser.parse_args()


def runtime(uri, control_uri, start_new):
    if start_new:
        rt = dispatch_node(uri=uri, control_uri=control_uri)
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


def deploy(rt, app_info, verbose):
    d = {}
    try:
        d = deployer.Deployer(rt, app_info)
        d.deploy()
    except Exception:
        time.sleep(0.1)
        if verbose:
            traceback.print_exc()
    return d.app_id


def set_loglevel(verbose, quiet):
    logger = get_logger()

    if quiet:
        logger.setLevel(logging.WARNING)
    else:
        logger.setLevel(logging.INFO)

    if verbose == 1:
        dtrace._trace_on = True
        logger.setLevel(logging.INFO)
    elif verbose == 2:
        dtrace._trace_on = True
        logger.setLevel(logging.DEBUG)
    else:
        dtrace._trace_on = False
        logger.setLevel(logging.INFO)


def main():
    args = parse_arguments()

    set_loglevel(args.verbose, args.quiet)

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

    rt = runtime(uri, control_uri, start_runtime)

    if add_peer:
        res = utils.peer_setup(rt, [args.peer])
        print res
        return 0

    if args.appid:
        res = utils.delete_application(rt, args.appid)
        print res['result']
        return 0

    app_id = None
    if deploy_app:
        app_id = deploy(rt, app_info, args.verbose)

    if start_runtime:
        timeout = int(args.wait) if int(args.wait) else None
        select.select([], [], [], timeout)
        utils.quit(rt)
        time.sleep(0.1)
    if app_id:
        print "Deployed application", app_id

if __name__ == '__main__':
    main()
