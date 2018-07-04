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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *
import os
import http.server
import http.server
import socketserver
import argparse
import socket

def parse_arguments():
    long_description = """
  Start web server.
  """

    argparser = argparse.ArgumentParser(description=long_description)
    argparser.add_argument('-p', '--port', metavar='<port>', type=int, dest='port',
                           help='port# of tcp server', default=8000)
    argparser.add_argument('-a', '--address', metavar='<address>', dest='address',
                           help='address of tcp server', default="")
    return argparser.parse_args()


class CORSRequestHandler (http.server.SimpleHTTPRequestHandler):
    def end_headers (self):
        self.send_header('Access-Control-Allow-Origin', '*')
        http.server.SimpleHTTPRequestHandler.end_headers(self)

def main():
    os.chdir(os.path.dirname(__file__))
    args = parse_arguments()
    Handler = CORSRequestHandler
    socketserver.TCPServer.allow_reuse_address = True

    try:
        socket.inet_pton(socket.AF_INET6, args.address)
        socketserver.TCPServer.address_family = socket.AF_INET6
    except socket.error:
        socketserver.TCPServer.address_family = socket.AF_INET

    httpd = socketserver.TCPServer((args.address, args.port), Handler)
    httpd.serve_forever()

if __name__ == '__main__':
    main()
