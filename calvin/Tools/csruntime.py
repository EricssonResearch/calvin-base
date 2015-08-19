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
from calvin.utilities.nodecontrol import dispatch_node
import logging

_log = get_logger(__name__)


def parse_arguments():
    long_description = """
Start runtime, compile calvinscript and deploy application.
  """

    argparser = argparse.ArgumentParser(description=long_description)

    argparser.add_argument('-n', '--host', metavar='<host>', type=str,
                           help='ip address/hostname of calvin runtime',
                           dest='host', required=True)

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

    argparser.add_argument('--keep-alive', dest='wait', action='store_const', const=0,
                           help='run forever (equivalent to -w 0 option).')

    argparser.add_argument('--attr', metavar='<attr>', type=str,
                           help='a comma separated list of attributes for started node '
                                'e.g. node/affiliation/owner/me,node/affiliation/name/bot',
                           dest='attr')

    return argparser.parse_args()


def runtime(uri, control_uri, attributes=None):
    kwargs = {'attributes': attributes} if attributes else {}
    return dispatch_node(uri=uri, control_uri=control_uri, **kwargs)


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


def set_loglevel(levels):
    if not levels:
        get_logger().setLevel(logging.INFO)
        return

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
        import pdb
        pdb.set_trace()

    set_loglevel(args.loglevel)

    deploy_app = args.file

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

    rt = runtime(uri, control_uri, attr_list)

    app_id = None
    if deploy_app:
        app_id = deploy(rt, app_info, args.loglevel)

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
