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
import time
import json
import traceback
import logging
import os

from calvin.requests.request_handler import RequestHandler

# Calvin related imports must be in functions, to be able to set logfile before imports
_conf = None
_log = None


def parse_arguments():
    long_description = """
Start runtime, compile calvinscript and deploy application.
  """

    argparser = argparse.ArgumentParser(description=long_description)

    argparser.add_argument('-n', '--host', metavar='<host>', type=str,
                           help='ip address/hostname of calvin runtime',
                           dest='host')

    argparser.add_argument('-p', '--port', metavar='<port>', type=int, dest='port',
                           help='port# of calvin runtime', default=5000)

    argparser.add_argument('-c', '--controlport', metavar='<port>', type=int, dest='controlport',
                           help='port# of control interface', default=5001)

    argparser.add_argument('-u', '--uri', dest='uris', action='append', default=[],
                           help="URI of calvin runtime 'calvinbt://id:port'")

    argparser.add_argument('file', metavar='<filename>', type=str, nargs='?',
                           help='source file to compile')

    argparser.add_argument('-d', '--debug', dest='debug', action='store_true',
                           help='Start PDB')

    argparser.add_argument('-l', '--loglevel', dest='loglevel', action='append', default=[],
                           help="Set log level, levels: CRITICAL, ERROR, WARNING, INFO, DEBUG and ANALYZE. \
                           To enable on specific modules use 'module:level'")

    argparser.add_argument('-f', '--logfile', dest='logfile', action="store", default=None, type=str,
                           help="Set logging to file, specify filename")

    argparser.add_argument('-w', '--wait', dest='wait', metavar='sec', default=2, type=int,
                           help='wait for sec seconds before quitting (0 means forever).')

    argparser.add_argument('--keep-alive', dest='wait', action='store_const', const=0,
                           help='run forever (equivalent to -w 0 option).')

    argparser.add_argument('--attr', metavar='<attr>', type=str,
                           help='JSON coded attributes for started node '
                                'e.g. \'{"indexed_public": {"owner": {"personOrGroup": "Me"}}}\''
                                ', see documentation',
                           dest='attr', default=None)

    argparser.add_argument('--attr-file', metavar='<attr>', type=str,
                           help='File with JSON coded attributes for started node '
                                'e.g. \'{"indexed_public": {"owner": {"personOrGroup": "Me"}}}\''
                                ', see documentation',
                           dest='attr_file', default=None)

    argparser.add_argument('--dht-network-filter', type=str,
                           help='Any string for filtering your dht clients, use same for all nodes in the network.',
                           default=None)

    argparser.add_argument('-s', '--storage-only', dest='storage', action='store_true', default=False,
                           help='Start storage only runtime')

    return argparser.parse_args()


def runtime(uri, control_uri, attributes=None, dispatch=False):
    from calvin.utilities.nodecontrol import dispatch_node, start_node
    kwargs = {'attributes': attributes} if attributes else {}
    if dispatch:
        return dispatch_node(uri=uri, control_uri=control_uri, **kwargs)
    else:
        start_node(uri, control_uri, **kwargs)


def storage_runtime(uri, control_uri, attributes=None, dispatch=False):
    from calvin.utilities.nodecontrol import dispatch_storage_node, start_storage_node
    kwargs = {}
    if dispatch:
        return dispatch_storage_node(uri=uri, control_uri=control_uri, **kwargs)
    else:
        start_storage_node(uri, control_uri, **kwargs)


def compile_script(scriptfile):
    _log.debug("Compiling %s ..." % file)
    from calvin.Tools import cscompiler
    app_info, errors, _ = cscompiler.compile_file(scriptfile)
    if errors:
        _log.error("{reason} {script} [{line}:{col}]".format(script=file, **errors[0]))
        return False
    return app_info


def deploy(rt, app_info):
    from calvin.Tools import deployer
    d = {}
    try:
        d = deployer.Deployer(rt, app_info)
        d.deploy()
    except:
        from calvin.utilities.calvinlogger import get_logger
        time.sleep(0.1)
        if get_logger().getEffectiveLevel <= logging.DEBUG:
            traceback.print_exc()
    return d.app_id


def set_loglevel(levels, filename):
    from calvin.utilities.calvinlogger import get_logger, set_file
    global _log

    if filename:
        set_file(filename)

    _log = get_logger(__name__)

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
        elif level == "ANALYZE":
            get_logger(module).setLevel(5)


def dispatch_and_deploy(app_info, wait, uri, control_uri, attr):
    rt, process = runtime(uri, control_uri, attr, dispatch=True)
    app_id = None
    app_id = deploy(rt, app_info)
    print "Deployed application", app_id

    timeout = wait if wait else None
    if timeout:
        process.join(timeout)
        RequestHandler().quit(rt)
        time.sleep(0.1)
    else:
        process.join()


def set_config_from_args(args):
    from calvin.utilities import calvinconfig
    global _conf
    _conf = calvinconfig.get()
    _conf.add_section("ARGUMENTS")
    for arg in vars(args):
        if getattr(args, arg) is not None:
            _log.debug("Adding ARGUMENTS to config {}={}".format(arg, getattr(args, arg)))
            _conf.set("ARGUMENTS", arg, getattr(args, arg))


def main():
    args = parse_arguments()

    if args.debug:
        import pdb
        pdb.set_trace()

    # Need to be before other calvin calls to set the common log file
    set_loglevel(args.loglevel, args.logfile)

    set_config_from_args(args)

    app_info = None

    if args.file:
        app_info = compile_script(args.file)
        if not app_info:
            print "Compilation failed."
            return 1

    uris = args.uris
    if args.host is None:
        control_uri = None
    else:
        control_uri = "http://%s:%d" % (args.host, args.controlport)
        uris.append("calvinip://%s:%d" % (args.host, args.port))

    if not uris:
        print "At least one listening interface is needed"
        return -1

    attr_ = None
    if args.attr:
        try:
            attr_ = json.loads(args.attr)
        except Exception as e:
            print "Attributes not JSON:\n", e
            return -1

    if args.attr_file:
        try:
            attr_ = json.load(open(args.attr_file))
        except Exception as e:
            print "Attribute file not JSON:\n", e
            return -1

    if app_info:
        dispatch_and_deploy(app_info, args.wait, uris, control_uri, attr_)
    else:
        if args.storage:
            storage_runtime(uris, control_uri, attr_, dispatch=False)
        else:
            runtime(uris, control_uri, attr_, dispatch=False)
    return 0


def csruntime(host, port=5000, controlport=5001, loglevel=None, logfile=None, attr=None, storage=False,
              outfile=None, configfile=None):
    """ Create a completely seperate process for the runtime. Useful when doing tests that start multiple
        runtimes from the same python script, since some objects otherwise gets unexceptedly shared.
    """
    call = "csruntime -n %s -p %d -c %d" % (host, port, controlport)
    try:
        call += (" --attr \"%s\"" % (json.dumps(attr).replace('"',"\\\""), )) if attr else ""
    except:
        pass
    call += " -s" if storage else ""
    call += (" --logfile %s" % (logfile, )) if logfile else ""
    if loglevel:
        for l in loglevel:
            call += " --loglevel %s" % (l, )
    call += " -w 0"
    call += (" &> %s" % outfile) if outfile else ""
    call += " &"
    if configfile:
        call = "CALVIN_CONFIG_PATH=%s " % configfile + call
    return os.system(call)


if __name__ == '__main__':
    import sys
    sys.exit(main())
