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
import glob
import json
from datetime import datetime, timedelta
try:
    import OpenSSL.crypto
    HAS_OPENSSL = True
except:
    HAS_OPENSSL = False
try:
    import pyrad.packet
    from pyrad.client import Client
    from pyrad.dictionary import Dictionary
    HAS_PYRAD = True
except:
    HAS_PYRAD = False
try:
    import jwt
    HAS_JWT = True
except:
    HAS_JWT = False
from calvin.utilities import certificate
from calvin.utilities.certificate import Certificate
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import calvinconfig
from calvin.utilities.utils import get_home
from calvin.utilities.runtime_credentials import RuntimeCredentials
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.requirement_matching import ReqMatch

_conf = calvinconfig.get()
_log = get_logger(__name__)

# Default timeout
TIMEOUT=5

try:
    _ca_conf = _conf.get("security", "certificate_authority")
    domain = _ca_conf["domain_name"]
except:
    domain = None

def security_modules_check():
    if _conf.get("security","security_conf"):
        _sec_conf =_conf.get("security","security_conf")
        # Want security
        if not HAS_OPENSSL:
            # Miss OpenSSL
            _log.error("Security: Install openssl to allow verification of signatures and certificates")
            return False
        if ('authetication' in _sec_conf) and ('procedure' in _sec_conf['authentication']) and (_conf.get("security","security_conf")['authentication']['procedure'] == "radius") and not HAS_PYRAD:
            _log.error("Security: Install pyrad to use radius server as authentication method.")
            return False
    return True

def security_enabled():
    if _conf.get("security","security_conf"):
        # Want security
        return True
    else:
        return False

def encode_jwt(payload, node):
    """Encode JSON Web Token"""
#    _log.debug("encode_jwt:\n\tpayload={}".format(payload))
    if node.runtime_credentials:
        private_key = node.runtime_credentials.get_private_key()
    else:
        _log.error("Node has no runtime credentials, cannot sign JWT")
    # Create a JSON Web Token signed using the node's Elliptic Curve private key.
    return jwt.encode(payload, private_key, algorithm='ES256')

def decode_jwt(token, sender_cert_name, node, actor_id=None, callback=None):
    """Decode JSON Web Token"""
#    _log.debug("decode_jwt:\n\ttoken={}\n\tsender_cert_name={}\n\tnode={}\n\tactor_id={}\n\tcallback={}".format(token, sender_cert_name, node, actor_id, callback))
    # Get authorization server certificate from disk.
    try:
        node.runtime_credentials.get_certificate(cert_name=sender_cert_name,
                                                callback=CalvinCB(_decode_jwt_cb,
                                                    token=token,
                                                    node=node,
                                                    actor_id=actor_id,
                                                    callback=callback))
    except Exception as err:
        #Look for certiticate in storage
        _log.debug("Certificate of sender not found, err={}".format(err))
        raise Exception("Certificate not found.")

def _decode_jwt_cb(certstring, token, node, actor_id=None, callback=None):
    """Decode JSON Web Token"""
#    _log.debug("_decode_jwt_cb\n\tsender certstring={}\n\ttoken={}\n\tnode={}\n\tactor_id={}\n\tcallback={}".format(certstring, token, node, actor_id, callback))
    sender_public_key = certificate.get_public_key_from_certstr(certstring)
    sender_node_id = certificate.cert_DN_Qualifier(certstring=certstring)
    # The signature is verified using the Elliptic Curve public key of the sender.
    # Exception raised if signature verification fails or if issuer and/or audience are incorrect.
    decoded = jwt.decode(token, sender_public_key, algorithms=['ES256'],
                         issuer=sender_node_id, audience=node.id)
    if actor_id and ('sub' in decoded) and (decoded["sub"] != actor_id):
        raise  # Exception raised if subject (actor_id) is incorrect.
    if callback:
        callback(decoded=decoded)


class Security(object):

    def __init__(self, node):
#        _log.debug("_init_, node={}".format(node))
        self.sec_conf = _conf.get("security","security_conf")
        self.node = node
        self.subject_attributes = {}
#        self.certificate = node.runtime_credentials.certificate

    def __str__(self):
        return "Subject: %s:" % self.subject_attributes

    def set_subject_attributes(self, subject_attributes):
        """Set subject attributes."""
#        _log.debug("set_subject_attributes: subject_attributes = %s" % subject_attributes)
        if not isinstance(subject_attributes, dict):
            _log.error("set_subject_attributes: subject_attributest should be dictionary")
            return False
        self.subject_attributes = subject_attributes

    def get_subject_attributes(self):
        """Return a dictionary with all authenticated subject attributes."""
#        _log.debug("get_subject_attributes, self.subject_attributes={}".format(self.subject_attributes))
        return self.subject_attributes.copy()

    def authenticate_subject(self, credentials, callback=None):
        """Authenticate subject using the authentication procedure specified in config."""
#        _log.debug("Security: authenticate_subject: \n\tcredentials={}".format(credentials))
        request = {}
        if not security_enabled():
            _log.debug("Security: no security enabled")
            callback(authentication_decision=True)
            return
        elif not credentials:
            _log.debug("Security: no credentials to authenticate (handle as guest)")
            self.subject_attributes = {}
            callback(authentication_decision=True)
            return
        request['subject'] = credentials
        if ('authentication' in self.sec_conf) and ('procedure' in self.sec_conf['authentication']):
            if self.sec_conf['authentication']['procedure'] == "external":
                if not HAS_JWT:
                    _log.error("Security: Install JWT to use external server as authentication method.\n" +
                                   "Note: NO authentication USED")
                    return False
                _log.debug("Security: external authentication method chosen")
                self.authenticate_using_external_server(request, callback)
                return True
            elif self.sec_conf['authentication']['procedure'] == "local":
                _log.debug("local authentication method chosen")
                # Authenticate access using a local Authentication Decision Point (ADP).
                self.node.authentication.adp.authenticate(request, CalvinCB(self._handle_local_authentication_response,
                                                          callback=callback))
                return True
            elif self.sec_conf['authentication']['procedure'] == "radius":
                if not HAS_PYRAD:
                    _log.error("Security: Install pyrad to use radius server as authentication method.\n" +
                                "Note! NO AUTHENTICATION USED")
                    return False
                _log.debug("Security: Radius authentication method chosen")
                return self.authenticate_using_radius_server(request, callback)
        _log.debug("Security: No security config, so authentication disabled")
        return True

    def authenticate_using_radius_server(self, request, callback):
        """Authenticate a subject using a RADIUS server."""
        try:
            root_dir = os.path.abspath(os.path.join(_conf.install_location(), '..'))
            client = Client(server=self.sec_conf['authentication']['server_ip'],
                            secret=bytes(self.sec_conf['authentication']['secret']),
                            dict=Dictionary(os.path.join(root_dir, "calvinextras", "pyrad_dicts", "dictionary"),
                                        os.path.join(root_dir, "calvinextras", "pyrad_dicts", "dictionary.acc")))
            req = client.CreateAuthPacket(code=pyrad.packet.AccessRequest,
                                          User_Name=request['subject']['user'],
                                          NAS_Identifier=self.node.id)
            req["User-Password"] = req.PwCrypt(request['subject']['password'])
            # FIXME: should not block here (use a callback instead)
            reply = client.SendPacket(req)
            if reply.code == pyrad.packet.AccessAccept:
                _log.debug("Security: access accepted")
                # Save attributes returned by server.
                self._return_authentication_decision(True, json.loads(reply["Reply-Message"][0]),
                                                     callback)
                return
            _log.debug("Security: access denied")
            self._return_authentication_decision(False, [], callback)
        except Exception as err:
            _log.error("Failed RADIUS authentication, err={}".format(err))
            self._return_authentication_decision(False, [], callback)


    def authenticate_using_external_server(self, request, callback):
        """
        Authenticate access using an external authentication server.

        The request is put in a JSON Web Token (JWT) that is signed and encrypted
        and includes timestamps and information about sender and receiver.
        """
        try:
            auth_server_id = self.node.authentication.auth_server_id
            payload = {
                "iss": self.node.id,
                "aud": auth_server_id,
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(seconds=60),
                "request": request
            }
            # TODO: encrypt the JWT
            # Create a JSON Web Token signed using the node's Elliptic Curve private key.
            jwt_request = encode_jwt(payload, self.node)
        except Exception as e:
            _log.error("authenticate_using_external_server, failed to encode jwt - %s" % str(e))
            self._return_authentication_decision(False, [], callback)
        try:
            # Send request to authentication server.
            self.node.proto.authentication_decision(auth_server_id,
                                                   CalvinCB(self._handle_authentication_response,
                                                            callback=callback),
                                                   jwt_request)
        except Exception as e:
            _log.error("authenticate_using_external_server: authentication error - %s" % str(e))
            self._return_authentication_decision(False, [], callback)

    def _handle_authentication_response(self, reply, callback):
        if reply.status != 200:
            _log.error("Security: authentication server error - %s" % reply)
            self._return_authentication_decision(False, [], callback)
            return
        try:
            # Decode JSON Web Token, which contains the authentication response.
            decode_jwt(reply.data["jwt"],
                       reply.data["cert_name"],
                       self.node,
                       callback=CalvinCB(self._handle_authentication_response_jwt_decoded_cb,
                                        callback=callback)
                      )
        except Exception as e:
            _log.error("Security: JWT decoding error - %s" % str(e))
            self._return_authentication_decision(False, [], callback)

    def _handle_authentication_response_jwt_decoded_cb(self, decoded, callback):
#        _log.debug("_handle_authentication_jwt_decoded_cb:\n\tdecoded={}\n\tcallback={}".format(decoded, callback))
        authentication_response = decoded['response']
        self._return_authentication_decision(authentication_response['decision'],
                                            authentication_response['subject_attributes'],
                                            callback,
                                            authentication_response.get("obligations", []))

    def _handle_local_authentication_response(self, auth_response, callback):
#        _log.debug("_handle_local_authentication_response:\n\tauth_response={}\n\tcallback={}".format(auth_response, callback))
        try:
            self._return_authentication_decision(auth_response['decision'],
                                                 auth_response['subject_attributes'],
                                                 callback,
                                                 auth_response.get("obligations", []))
        except Exception as e:
            _log.error("Security: local authentication error - %s" % str(e))
            self._return_authentication_decision(False, [], callback)

    def _return_authentication_decision(self, decision, subject_attributes, callback, obligations=None):
        _log.debug("_return_authentication_decision: \n\tdecision={}\n\tsubject_attributes={}\n\tcallback={}\n\tobligations={}".format(decision, subject_attributes, callback, obligations))
        if decision:
            _log.debug("Authentication successful")
            self.set_subject_attributes(subject_attributes)
            callback(authentication_decision=True)
        else:
            _log.debug("Authentication failed")
            callback(authentication_decision=False)
#        if obligations:
#            callback(access_decision=(True, obligations))
#        else:
#            callback(access_decision=True)

    def check_security_policy(self, callback, element_type, actor_id=None, requires=None, element_value=None, decision_from_migration=None):
        """Check if access is permitted by the security policy."""
        # Can't use id for application since it is not assigned when the policy is checked.
#        _log.debug("check_security_policy, element_type={}".format(element_type))
        element_dict={}
        if self.sec_conf and 'authorization' in self.sec_conf and 'procedure' in self.sec_conf['authorization']:
            if element_type in ['application', 'actor']:
                element_dict[element_type + "_signer"] = element_value
            if element_type is 'control_interface':
                element_dict['control_interface'] = element_value
            self.get_authorization_decision(callback, actor_id, requires, element_dict, decision_from_migration)
            return
        # No security config, so access control is disabled.
        return callback(access_decision=True)

    def get_authorization_decision(self, callback, actor_id=None, requires=None, element_dict=None, decision_from_migration=None):
        """Get authorization decision using the authorization procedure specified in config."""
#        _log.debug("Security: get_authorization_decision:\n\tcallback={}\n\tactor_id={}\n\trequires={}\n\telement_dict={}\n\tdecision_from_migration={}".format(callback, actor_id, requires, element_dict, decision_from_migration))
        if decision_from_migration:
            try:
                _log.debug("Authorization decision from migration")
                # Decode JSON Web Token, which contains the authorization response.
                decode_jwt(decision_from_migration["jwt"], decision_from_migration["cert_name"],
                            self.node, actor_id,
                            CalvinCB(self._get_authorization_decision_jwt_decoded_cb,
                                callback=callback))
                return
            except Exception as e:
                _log.error("Security: JWT decoding error - %s" % str(e))
                self._return_authorization_decision("indeterminate", [], callback)
                return
        else:
            request = {}
            request["subject"] = self.get_subject_attributes()
            if element_dict is not None:
                request["subject"].update(element_dict)
            request["resource"] = {"node_id": self.node.id}
            if requires is not None:
                request["action"] = {"requires": requires}
            _log.debug("Security: authorization request: %s" % request)

            # Check if the authorization server is local (the runtime itself) or external.
            if 'authorization' in self.sec_conf and 'procedure' in self.sec_conf['authorization']:
                if self.sec_conf['authorization']['procedure'] == "external":
                    if not HAS_JWT:
                        _log.error("Security: Install JWT to use external server as authorization method.\n" +
                                   "Note: NO AUTHORIZATION USED")
                        return False
                    _log.debug("Security: external authorization method chosen")
                    self.authorize_using_external_server(request, callback, actor_id)
                else:
                    _log.debug("Security: local authorization method chosen")
                    # Authorize access using a local Policy Decision Point (PDP).
                    self.node.authorization.pdp.authorize(request, CalvinCB(self._handle_local_authorization_response,
                                                              callback=callback))
            else:
                _log.error("This should have already been caught, raise exception")
                raise("No authorization procedure configured")

    def _get_authorization_decision_jwt_decoded_cb(self, decoded, callback):
        """Get authorization decision using the authorization procedure specified in config."""
        _log.debug("Security: _get_authorization_decision_decoded_jwt_cb")
        authorization_response = decoded['response']
        self._return_authorization_decision(authorization_response['decision'],
                                            authorization_response.get("obligations", []),
                                            callback)
        return

    def _return_authorization_decision(self, decision, obligations, callback):
        _log.debug("Authorization response received: %s, obligations %s" % (decision, obligations))
        if decision == "permit":
            _log.debug("Security: access permitted to resources")
            if obligations:
                callback(access_decision=(True, obligations))
            else:
                callback(access_decision=True)
        elif decision == "deny":
            _log.debug("Security: access denied to resources")
            callback(access_decision=False)
        elif decision == "indeterminate":
            _log.debug("Security: access denied to resources. Error occured when evaluating policies.")
            callback(access_decision=False)
        else:
            _log.debug("Security: access denied to resources. No matching policies.")
            callback(access_decision=False)

    def authorize_using_external_server(self, request, callback, actor_id=None):
        """
        Authorize access using an external authorization server.

        The request is put in a JSON Web Token (JWT) that is signed
        and includes timestamps and information about sender and receiver.
        """
        try:
            authz_server_id = self.node.authorization.authz_server_id
            payload = {
                "iss": self.node.id,
                "aud": authz_server_id,
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(seconds=60),
                "request": request
            }
            if actor_id:
                payload["sub"] = actor_id
            # Create a JSON Web Token signed using the node's Elliptic Curve private key.
            jwt_request = encode_jwt(payload, self.node)
            # Send request to authorization server.
            self.node.proto.authorization_decision(authz_server_id,
                                                   CalvinCB(self._handle_authorization_response,
                                                            callback=callback, actor_id=actor_id),
                                                   jwt_request)
        except Exception as e:
            _log.error("Security: authorization error - %s" % str(e))
            self._return_authorization_decision("indeterminate", [], callback)

    def _handle_authorization_response(self, reply, callback, actor_id=None):
#        _log.debug("_handle_authorization_response\n\treply={}\n\tcallback={}\n\tactor_id={}".format(reply, callback, actor_id))
        if reply.status != 200:
            _log.error("Security: authorization server error - %s" % reply)
            self._return_authorization_decision("indeterminate", [], callback)
            return
        try:
            # Decode JSON Web Token, which contains the authorization response.
            decode_jwt(reply.data["jwt"], reply.data["cert_name"],
                                self.node, actor_id,
                                CalvinCB(self._handle_authorization_response_jwt_decoded_cb,
                                    callback=callback))
        except Exception as e:
            _log.error("Security: JWT decoding error - %s" % str(e))
            self._return_authorization_decision("indeterminate", [], callback)

    def _handle_authorization_response_jwt_decoded_cb(self, decoded, callback):
#        _log.debug("_handle_authorization_response_jwt_decoded_cb:\n\tdecoded={}\n\tcallback={}".format(decoded, callback))
        authorization_response = decoded['response']
        self._return_authorization_decision(authorization_response['decision'],
                                            authorization_response.get("obligations", []),
                                            callback)

    def _handle_local_authorization_response(self, authz_response, callback):
#        _log.debug("_handle_local_authorization_response:\n\tauthz_response={}\n\tcallback={}".format(authz_response, callback))
        try:
            self._return_authorization_decision(authz_response['decision'],
                                                authz_response.get("obligations", []), callback)
        except Exception as e:
            _log.error("Security: local authorization error - %s" % str(e))
            self._return_authorization_decision("indeterminate", [], callback)

    def authorization_runtime_search(self, actor_id, actorstore_signature, callback):
        """Search for runtime where the authorization decision for the actor is 'permit'."""
#       _log.debug("authorization_runtime_search:\n\tactor_id={}\n\tactorstore_signature={}\n\tcallback={}".format(actor_id, actorstore_signature, callback))
        #Search for runtimes supporting the actor with appropriate actorstore_signature
        r = ReqMatch(self.node,
                     callback=CalvinCB(self._authorization_server_search,
                                       actor_id=actor_id,
                                       actorstore_signature=actorstore_signature,
                                       callback=callback))
        r.match_for_actor(actor_id)

    def _authorization_server_search(self, possible_placements, actor_id, actorstore_signature, callback, status=None):
 #       _log.debug("_authorization_server_search:\n\tpossible_placements={}\n\tactor_id={}\n\tactorstore_signature={}\n\tcallback={}".format(possible_placements, actor_id, actorstore_signature, callback))
        if not possible_placements:
            callback(None)
            return
        #Search for available authorization servers in storage
        self.node.storage.get_index(['authorization_server'],
                                    cb=CalvinCB(self._send_authorization_runtime_search, key='authorization_server',
                                                       counter=0, actor_id=actor_id,
                                                       actorstore_signature=actorstore_signature,
                                                       possible_placements=list(possible_placements),
                                                       callback=callback))

    def _send_authorization_runtime_search(self, key, value, counter, actor_id, actorstore_signature,
                                           possible_placements, callback):
#        _log.debug("_send_authorization_runtime_search:\n\tkey={}\n\tvalue={}\n\tcounter={}\n\tactor_id={}\
#                   \n\tactorstore_signature={}\n\tpossible_placements={}\n\tcallback={}".format(key,\
#                                           value,\
#                                           counter,
#                                           actor_id,
#                                           actorstore_signature,
#                                           possible_placements,
#                                           callback))
        if not value:
            callback(None)
            return
        request = {}
        request["subject"] = self.get_subject_attributes()
        request["subject"]["actorstore_signature"] = actorstore_signature
        authz_server_id = value[counter]
        try:
            payload = {
                "iss": self.node.id,
                "sub": actor_id,
                "aud": authz_server_id,
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(seconds=60),
                "request": request,
                "whitelist": possible_placements
            }
            jwt_request = encode_jwt(payload, self.node)
            # Send request to authorization server.
            self.node.proto.authorization_search(authz_server_id,
                                                 CalvinCB(self._handle_authorization_runtime_search_response,
                                                        key=key, value=value,
                                                        counter=counter,
                                                        actor_id=actor_id,
                                                        actorstore_signature=actorstore_signature,
                                                        possible_placements=possible_placements,
                                                        callback=callback), jwt_request)
        except Exception as e:
            _log.error("Security: authorization server error - %s" % str(e))
            callback(None)



    def _handle_authorization_runtime_search_response(self, reply, key, value, counter, actor_id,
                                                      actorstore_signature, possible_placements,
                                                      callback):
#        _log.debug("_handle_authorization_runtime_search_response:\n\treply={}\n\tkey={}\n\tvalue={}\n\tcounter={}\n\tactor_id={}\n\tactorstore_signature={}\n\tpossible_placements={}\n\tcallback={}".format(reply,key,value,counter,actor_id,actorstore_signature,possible_placements,callback))
        if reply.status != 200 or reply.data["node_id"] is None:
            counter += 1
            if counter < len(possible_placements):
                _log.debug("_handle_authorization_runtime_search_response: No target from {}, continue with {}".format(value[counter-1],value[counter]))
                # Continue searching
                self._send_authorization_runtime_search(key=key, value=value,
                                                        counter=counter,
                                                        actor_id=actor_id,
                                                        actorstore_signature=actorstore_signature,
                                                        possible_placements=possible_placements,
                                                        callback=callback)
                return
        else:
                _log.debug("_handle_authorization_runtime_search_response: No target from {}, this was the last authorization server".format(value[counter-1]))

        callback(reply)

    @staticmethod
    def verify_signature_get_files(filename, skip_file=False):
        """Get files needed for signature verification of the specified file."""
        # Get the data
        sign_filenames = filename + ".sign.*"
        sign_content = {}
        file_content = ""
        # Filename is *.sign.<cert_hash>
        sign_files = {os.path.basename(f).split(".sign.")[1]: f for f in glob.glob(sign_filenames)}
        for cert_hash, sign_filename in sign_files.iteritems():
            try:
                with open(sign_filename, 'rt') as f:
                    sign_content[cert_hash] = f.read()
                    _log.debug("Found signature for %s" % cert_hash)
            except:
                _log.error("Signature file {} is missing".format(sign_filename))
                pass
        if not skip_file:
            try:
                with open(filename, 'rt') as f:
                    file_content = f.read()
            except:
                _log.error("verify_signature_get_files: file can't be opened, filename={}".format(filename))
                return None
        return {'sign': sign_content, 'file': file_content}

    def verify_signature(self, file, flag):
        """
        Verify the signature of the specified file of type flag.

        A tuple (verified True/False, signer) is returned.
        """
        _log.debug("verify_signature: file={}, flag={}".format(file, flag))
        content = Security.verify_signature_get_files(file)
        if content:
            return self.verify_signature_content(content, flag)
        else:
            _log.error("verify_signature: no content, signature verification fails")
            return (False, None)

    def verify_signature_content(self, content, flag):
        """
        Verify the signature of the content of type flag.

        A tuple (verified True/False, signer) is returned.
        """
#        _log.debug("verify_signature_content: flag={} , content={}".format(flag, content))
        if not self.sec_conf:
            _log.debug("verify_signature_content: no signature verification required: %s" % content['file'])
            return (True, None)

        if flag not in ["application", "actor"]:
            # TODO add component verification
            raise NotImplementedError

        signer = None

        if content is None or not content['sign']:
            _log.debug("verify_signature_content: signature information missing, content={}".format(content))
            signer = ["__unsigned__"]
            return (True, signer)  # True is returned to allow authorization request with the signer attribute '__unsigned__'.

        if not HAS_OPENSSL:
            _log.error("verify_signature_content: install OpenSSL to allow verification of signatures and certificates, verification of %s signature failed" % flag)
            return (False, None)

        # If any of the signatures is verified correctly, True is returned.
        for cert_hash, signature in content['sign'].iteritems():
            try:
                # Check if the certificate is stored in the truststore (name is <cert_hash>.0)
                #TODO: remove signature_trust_store dependency
                truststore_path = self.node.runtime_credentials.certificate.get_truststore_path(certificate.TRUSTSTORE_SIGN)
                trusted_cert_path = os.path.join(truststore_path, cert_hash + ".0")
                with open(trusted_cert_path, 'rt') as f:
                    certstr=f.read()
                    try:
#                        # Verify signature
                        cert = self.node.runtime_credentials.certificate.truststore_sign.verify_signature(content['file'],
                                                          signature,
                                                          certstr )
                        signer = [cert.get_issuer().CN]  # The Common Name field for the issuer
                        return (True, signer)
                    except Exception as e:
                        _log.error("OpenSSL verification error, err={}".format(e), exc_info=True)
                        continue
            except Exception as e:
                _log.error("Error opening one of the needed certificates, err={}".format(e), exc_info=True)
                continue
        _log.error("Security: verification of %s signature failed" % flag)
        return (False, signer)
