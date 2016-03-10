# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import sys
import json
import os
import argparse
try:
    import jwt
    from datetime import datetime, timedelta
    HAS_JWT = True
except:
    HAS_JWT = False
from calvin.utilities.authorization.policy_decision_point import PolicyDecisionPoint

key_storage_path = os.path.join(os.path.expanduser("~/.calvin/security/keys/"), '')

def parse_arguments():
    long_description = """Start authorization server."""

    argparser = argparse.ArgumentParser(description=long_description)
    argparser.add_argument('-p', '--port', metavar='<port>', type=int, dest='port',
                           help='server port', default=8080)
    argparser.add_argument('-a', '--address', metavar='<address>', dest='address',
                           help='server address', default="")
    return argparser.parse_args()

class HTTPRequestHandler(BaseHTTPRequestHandler):

    def send_success(self, message):
        """Send success response that includes message"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(message))
        return

    def send_error(self, status, message):
        """Send error response that includes message"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": str(message)}))
        return

    def get_data(self):
        """Get data included in the HTTP request"""
        h = self.headers.getheader('Content-Length')
        if h == None:
            return None
        return self.rfile.read(int(h))

    def handle_authorization_request(self, data):
        """
        Return a response to the authorization request included in the data.

        Signed JSON Web Tokens (JWT) with timestamps and information about 
        sender and receiver are used for both the request and response.
        A Policy Decision Point (PDP) is used to determine if access is permitted.
        """
        global args
        data = json.loads(data)
        # FIXME: How is the public key retrieved? Put it on authorization server during setup or send certificate signed by CA?
        public_key_runtime = open(key_storage_path + 'public_key.pem', 'rb').read()
        # FIXME: Use name from certificate as audience/issuer (use obtain_cert_node_info in certificate.py)
        authorization_server_id = "localhost"
        decoded = jwt.decode(data["jwt"], public_key_runtime, algorithms=['RS256'], audience=authorization_server_id)
        node_id = decoded["iss"]
        pdp = PolicyDecisionPoint()
        response = pdp.authorize(decoded["request"])
        payload = {
            "iss": authorization_server_id,
            "aud": node_id, 
            "iat": datetime.utcnow(), 
            "exp": datetime.utcnow() + timedelta(seconds=60),
            "response": response
        }
        # FIXME: How is the private key retrieved?
        private_key = open(key_storage_path + 'private_key_2.pem', 'rb').read()
        token = jwt.encode(payload, private_key, algorithm='RS256')
        return {"jwt": token}

    def do_POST(self):
        """Handle POST requests"""
        try:
            if self.path == '/authorization/pdp':
                self.send_success(self.handle_authorization_request(self.get_data()))
                return
            self.send_error(400, "Invalid path")
        except Exception as e:
            self.send_error(500, str(e))
        return

if __name__ == "__main__":
    if not HAS_JWT:
        print "Install JWT to use external server as authorization method."
        sys.exit(1)
    try:
        global args
        args = parse_arguments()
        server = HTTPServer((args.address, args.port), HTTPRequestHandler)
        print "Authorization server starting - %s:%s" % server.server_address
        server.serve_forever()
    except KeyboardInterrupt:
        print "Server stopping - %s:%s" % server.server_address
        server.server_close()
        