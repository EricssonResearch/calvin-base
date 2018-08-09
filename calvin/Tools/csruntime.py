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
import socket

# Calvin related imports must be in functions, to be able to set logfile before imports
_conf = None
_log = None



def parse_arguments():
    long_description = """
Start runtime, compile calvinscript and deploy application.
  """

    argparser = argparse.ArgumentParser(description=long_description)

    group = argparser.add_mutually_exclusive_group()
    group.add_argument('--gui', dest="gui", action="store_true", help="start Calvin GUI")
    group.add_argument('--gui-mock-devices', dest="guimockdevices", action="store_true", help="start Calvin GUI with default set of mock devices")
    argparser.add_argument('--gui-port', metavar='<gui port>', type=int, dest="guiport",
                           default=8000, help="use port <gui port> for gui server")
    argparser.add_argument('--gui-if', metavar='<gui interface>', type=str, dest="guiif",
                           default="localhost", help="use ipv4 interface <gui interface> for gui server")

    argparser.add_argument('--name', metavar='<name>', type=str,
                            help="shortcut for attribute indexed_public/node_name/name",
                            dest='name')

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

    argparser.add_argument('-x', '--external', metavar='<calvinip>', action='append', default=[],
                            help="exposed external calvin ip (e.g. outside of container)",
                            dest='ext')

    argparser.add_argument('-y', '--external-control', metavar='<url>', type=str,
                           help="exposed external control url (e.g. outside of container)",
                           dest='control_ext')

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

    argparser.add_argument('--credentials', metavar='<credentials>', type=str,
                           help='Supply credentials to run program under '
                                'e.g. \'{"user":"ex_user", "password":"passwd"}\'',
                           dest='credentials', default=None)

    argparser.add_argument('--uuid', metavar='<uuid>', type=str,
                            help="Set the UUID of the runtime. Does not apply when security is enabled.",
                            dest='uuid')

    return argparser.parse_args()


def runtime(uris, control_uri, attributes=None, dispatch=False):
    from calvin.utilities.nodecontrol import dispatch_node, start_node
    kwargs = {'attributes': attributes} if attributes else {}
    try:
        if dispatch:
            return dispatch_node(uris=uris, control_uri=control_uri, **kwargs)
        else:
            start_node(uris, control_uri, **kwargs)
    except Exception as e:
        print "Starting runtime failed:", e
        raise

def storage_runtime(uri, control_uri, attributes=None, dispatch=False):
    from calvin.utilities.nodecontrol import dispatch_storage_node, start_storage_node
    kwargs = {}
    if dispatch:
        return dispatch_storage_node(uri=uri, control_uri=control_uri, **kwargs)
    else:
        start_storage_node(uri, control_uri, **kwargs)


def compile_script(scriptfile, credentials):
    _log.debug("Compiling %s ..." % scriptfile)
    from calvin.Tools.cscompiler import compile_file
    app_info, issuetracker = compile_file(scriptfile, False, False, credentials)
    if issuetracker.error_count:
        fmt = "{type!c}: {reason} {script} {line}:{col}"
        for error in issuetracker.formatted_errors(sort_key='line', custom_format=fmt, script=scriptfile, line=0, col=0):
            _log.error(error)
        return False
    return app_info


def deploy(rt, app_info, credentials):
    from calvin.Tools import deployer
    d = {}
    try:
        d = deployer.Deployer(rt, app_info, credentials)
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


def dispatch_and_deploy(app_info, wait, uris, control_uri, attr, credentials):
    from calvin.requests.request_handler import RequestHandler
    rt, process = runtime(uris, control_uri, attr, dispatch=True)
    app_id = None
    app_id = deploy(rt, app_info, credentials)
    print "Deployed application", app_id

    timeout = wait if wait else None
    if timeout:
        process.join(timeout)
        RequestHandler().quit(rt)
        # This time has to be long enough for the mainloop to wrap things up, otherwise the program will hang indefinitely
        time.sleep(1.0)
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

def discover(timeout=2, retries=5):
    import struct
    from calvin.runtime.south.storage.twistedimpl.dht.service_discovery_ssdp import SSDPServiceDiscovery,\
                                                                                            SERVICE_UUID,\
                                                                                            CA_SERVICE_UUID,\
                                                                                            SSDP_ADDR,\
                                                                                            SSDP_PORT,\
                                                                                            MS_CA
    _log.info("discover")
    message = MS_CA
    socket.setdefaulttimeout(timeout)
    responses = {}
    attempt=0
    while attempt in range(retries) and not bool(responses):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        ttl = struct.pack('b', 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        try:
            sent = sock.sendto(message, (SSDP_ADDR,SSDP_PORT))
            while True:
                try:
                    data, server = sock.recvfrom(1000)
                except socket.timeout:
                    time.sleep(5)
                    break
                else:
                    responses[server] = data
                    _log.debug("Received {} from {}".format(data, server))
        finally:
            _log.debug("Closing socket")
            sock.close()
    return responses.values()

def runtime_certificate(rt_attributes):
    import copy
    import requests
    import sys
    from calvin.requests.request_handler import RequestHandler
    from calvin.utilities.attribute_resolver import AttributeResolver
    from calvin.utilities import calvinconfig
    from calvin.utilities import calvinuuid
    from calvin.utilities import runtime_credentials
    from calvin.utilities import certificate
    from calvin.utilities import certificate_authority
    from calvin.runtime.south.storage.twistedimpl.dht.service_discovery_ssdp import parse_http_response
    global _conf
    global _log
    _conf = calvinconfig.get()
    if not _conf.get_section("security"):
        #If the security section is empty, no securty features are enabled and certificates aren't needed
        _log.debug("No runtime security enabled")
    else:
        _log.debug("Some security features are enabled, let's make sure certificates are in place")
        _ca_conf = _conf.get("security","certificate_authority")
        security_dir = _conf.get("security","security_dir")
        storage_type = _conf.get("global","storage_type")
        if _ca_conf:
            try:
                ca_ctrl_uri = _ca_conf["ca_control_uri"] if "ca_control_uri" in _ca_conf else None
                domain_name = _ca_conf["domain_name"] if "domain_name" in _ca_conf else None
                is_ca = _ca_conf["is_ca"] if "is_ca" in _ca_conf else None
                enrollment_password =  _ca_conf["enrollment_password"] if "enrollment_password" in _ca_conf else None
            except Exception as err:
                _log.error("runtime_certificate: Failed to parse security configuration in calvin.conf, err={}".format(err))
                raise
            #AttributeResolver tranforms the attributes, so make a deepcopy instead
            rt_attributes_cpy = copy.deepcopy(rt_attributes)
            attributes = AttributeResolver(rt_attributes_cpy)
            node_name = attributes.get_node_name_as_str()
            nodeid = calvinuuid.uuid("")
            runtime = runtime_credentials.RuntimeCredentials(node_name, domain_name,
                                                           security_dir=security_dir,
                                                           nodeid=nodeid,
                                                           enrollment_password=enrollment_password)
            certpath, cert, certstr = runtime.get_own_cert()
            if not cert:
                csr_path = os.path.join(runtime.runtime_dir, node_name + ".csr")
                if is_ca:
                    _log.debug("No runtime certificate, but node is a CA, just sign csr, domain={}".format(domain_name))
                    ca = certificate_authority.CA(domain=domain_name,
                                                  security_dir=security_dir)
                    cert_path = ca.sign_csr(csr_path, is_ca=True)
                    runtime.store_own_cert(certpath=cert_path)

                else:
                    _log.debug("No runtime certicificate can be found, send CSR to CA")
                    truststore_dir = certificate.get_truststore_path(type=certificate.TRUSTSTORE_TRANSPORT,
                                                                     security_dir=security_dir)
                    request_handler = RequestHandler(verify=truststore_dir)
                    ca_control_uris = []
                    #TODO: add support for multiple CA control uris
                    if ca_ctrl_uri:
                        _log.debug("CA control_uri in config={}".format(ca_ctrl_uri))
                        ca_control_uris.append(ca_ctrl_uri)
                    elif storage_type in ["dht","securedht"]:
                        _log.debug("Find CA via SSDP")
                        responses = discover()
                        if not responses:
                            _log.error("No responses received")
                        for response in responses:
                            cmd, headers = parse_http_response(response)
                            if 'location' in headers:
                                ca_control_uri, ca_node_id = headers['location'].split('/node/')
                                ca_control_uris.append(ca_control_uri)
                                _log.debug("CA control_uri={}, node_id={}".format(ca_control_uri, ca_node_id))
                    else:
                        _log.error("There is no runtime certificate. For automatic certificate enrollment using proxy storage,"
                                        "the CA control uri must be configured in the calvin configuration ")
                        raise Exception("There is no runtime certificate. For automatic certificate enrollment using proxy storage,"
                                        "the CA control uri must be configured in the calvin configuration ")
                    cert_available=False
                    # Loop through all CA:s that responded until hopefully one signs our CSR
                    # Potential improvement would be to have domain name in response and only try
                    # appropriate CAs
                    i=0
                    csr = json.dumps(runtime.get_csr_and_enrollment_password())
                    while not cert_available and i<len(ca_control_uris):
                        certstr=None
                        #Repeatedly (maximum 10 attempts) send CSR to CA until a certificate is returned (this to remove the requirement of the CA
                        #node to be be the first node to start)
                        j=0
                        while not certstr and j<10:
                            try:
                                certstr = request_handler.sign_csr_request(ca_control_uris[i], csr)['certificate']
                            except requests.exceptions.RequestException as err:
                                time_to_sleep = 1 + j*j*j
                                _log.debug("RequestException, CSR not accepted or CA not up and running yet, sleep {} seconds and try again, err={}".format(time_to_sleep, err))
                                time.sleep(time_to_sleep)
                                j=j+1
                                pass
                            else:
                                cert_available = True
                        i = i+1
                    #TODO: check that everything is ok with signed cert, e.g., check that the CA domain
                    # matches the expected and that the CA cert is trusted
                    runtime.store_own_cert(certstring=certstr)
            else:
                _log.debug("Runtime certificate available")

def start_gui(interface4, port, mockdevices):
  import calvinextras
  import inspect
  import os.path
  from twisted.web.server import Site
  from twisted.web.static import File
  from twisted.internet import endpoints, reactor
  from calvin.utilities import calvinconfig

  # find installation path of calvinextras package
  extras_path = os.path.dirname(inspect.getfile(calvinextras))
  # build path to gui files
  gui_path = os.path.join(extras_path, "CalvinGUI", "Build", "GUI")
  gui_config_path =  os.path.join(extras_path, "CalvinGUI", "calvin.conf")
  if mockdevices:
      # Patch config
      _conf = calvinconfig.get()
      delta_config = _conf.config_at_path(gui_config_path)
      _conf.update_config(delta_config)
  # Add endpoint to twisted reactor
  resource = File(gui_path)
  factory = Site(resource)
  endpoint = endpoints.TCP4ServerEndpoint(reactor, interface=interface4, port=port)
  endpoint.listen(factory)
  _log.info("Calvin GUI server listening on http://{}:{}".format(interface4, port))


def main():
    args = parse_arguments()

    if args.debug:
        import pdb
        pdb.set_trace()

    # Need to be before other calvin calls to set the common log file
    set_loglevel(args.loglevel, args.logfile)
    set_config_from_args(args)

    # Start gui (if applicaple)
    if args.gui or args.guimockdevices:
        start_gui(args.guiif, args.guiport, args.guimockdevices)

    app_info = None

    credentials_ = None
    if args.credentials:
        try:
            credentials_ = json.loads(args.credentials)
        except Exception as e:
            print "Credentials not JSON:\n", e
            return 1

    if args.file:
        app_info = compile_script(args.file, credentials_)
        if not app_info:
            print "Compilation failed."
            return 1

    uris = args.uris
    tls_enabled = _conf.get("security","control_interface_security")
    if args.host is None:
        control_uri = None
    else:
        if tls_enabled=="tls":
            control_uri = "https://%s:%d" % (args.host, args.controlport)
        else:
            control_uri = "http://%s:%d" % (args.host, args.controlport)
        uris.append("calvinip://%s:%d" % (args.host, args.port))

    if not uris:
        print "At least one listening interface is needed"
        return -1

    # Attributes
    runtime_attr = {}

    if args.attr_file:
        try:
            runtime_attr = json.load(open(args.attr_file))
        except Exception as e:
            print "Attribute file not JSON:\n", e
            return -1

    if args.attr:
        try:
            runtime_attr = json.loads(args.attr)
        except Exception as e:
            print "Attributes not JSON:\n", e
            return -1

    if args.ext:
        runtime_attr['external_uri'] = args.ext

    if args.control_ext:
        runtime_attr['external_control_uri'] = args.control_ext

    # We let --name override node_name:name (if present)
    if args.name:
        runtime_attr.setdefault("indexed_public",{}).setdefault("node_name",{})['name'] = args.name

    # If still no name give it "no_name" name
    if not 'name' in runtime_attr.setdefault("indexed_public",{}).setdefault("node_name",{}):
        runtime_attr["indexed_public"]["node_name"]['name'] = "no_name"

    if app_info:
        dispatch_and_deploy(app_info, args.wait, uris, control_uri, runtime_attr, credentials_)
    else:
        runtime_certificate(runtime_attr)
        if args.storage:
            storage_runtime(uris, control_uri, runtime_attr, dispatch=False)
        else:
            runtime(uris, control_uri, runtime_attr, dispatch=False)
    return 0


def csruntime(host, port=5000, controlport=5001, loglevel=None, logfile=None, attr=None, storage=False,
              credentials=None, outfile=None, configfile=None, dht_network_filter=None):
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
    try:
        call += (" --credentials \"%s\"" % (json.dumps(credentials).replace('"',"\\\""), )) if credentials else ""
    except:
        pass
    try:
        call += (" --dht-network-filter \"%s\"" % (dht_network_filter, )) if dht_network_filter else ""
    except:
        pass
    call += " -w 0"
    call += (" &> %s" % outfile) if outfile else ""
    call += " &"
    if configfile:
        call = "CALVIN_CONFIG=%s " % configfile + call
    return os.system(call)


if __name__ == '__main__':
    import sys
    sys.exit(main())
