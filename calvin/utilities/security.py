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
import json
import string
import glob
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

from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import calvinconfig
from calvin.utilities.utils import get_home

_conf = calvinconfig.get()
_log = get_logger(__name__)
#default timeout
TIMEOUT=5


def security_modules_check():
    if _conf.get("security","security_conf") or _conf.get("security","security_policy"):
        # Want security
        if not HAS_OPENSSL:
            # Miss open ssl
            _log.error("Security: Install openssl to allow verification of signatures and certificates")
            return False
            _conf.get("security","security_conf")['authentication']
        if _conf.get("security","security_conf")['authentication']['procedure'] == "radius" and not HAS_PYRAD:
            _log.error("Security: Install pyrad to use radius server as authentication method.")
            return False
    return True

def security_needed_check():
    if _conf.get("security","security_conf") or _conf.get("security","security_policy"):
        # Want security
        return True
    else:
        return False

class Security(object):
    def __init__(self):
        _log.debug("Security: _init_")
        self.sec_conf = _conf.get("security","security_conf")
        self.sec_policy = _conf.get("security","security_policy")
        if self.sec_conf is not None and not self.sec_conf.get('signature_trust_store', None):
            # Set default directory for trust store
            homefolder = get_home()
            truststore_dir = os.path.join(homefolder, ".calvin", "security", "trustStore")
            self.sec_conf['signature_trust_store'] = truststore_dir
        self.principal = {}
        self.auth = {}

    def __str__(self):
        return "Principal: %s\nAuth: %s" % (self.principal, self.auth)

    def set_principal(self, principal):
        _log.debug("Security: set_principal %s" % principal)
        if not isinstance(principal, dict):
            return False
        # Make sure all principal values are lists
        self.principal = {k: list(v) if isinstance(v, (list, tuple, set)) else [v]
                            for k, v in principal.iteritems()}
        # All default to unauthorized
        self.auth = {k: [False]*len(v) for k, v in self.principal.iteritems()}

    def authenticate_principal(self):
        _log.debug("Security: authenticate_principal")
        if not security_needed_check():
            _log.debug("Security: authenticate_principal no security needed")
            return True

        if self.sec_conf['authentication']['procedure'] == "local_file":
            _log.debug("Security: local file authentication method chosen")
            return self.authenticate_using_local_database()
        if self.sec_conf['authentication']['procedure'] == "radius":
            if not HAS_PYRAD:
                _log.error("Security: Install pyrad to use radius server as authentication method.\n" +
                            "NB! NO AUTHENTICATION USED")
                return False
            _log.info("Security: Radius authtentication method chosen")
            return self.authenticate_using_radius_server()
        _log.info("Security: No security config, so authentication disabled")
        return True


    def authenticate_using_radius_server(self):
        auth = []
        if self.principal['user']:
            srv=Client(server=self.sec_conf['authentication']['server_ip'], 
                        secret= bytes(self.sec_conf['authentication']['secret']),
                        dict=Dictionary("extras/pyrad_dicts/dictionary", "extras/pyrad_dicts/dictionary.acc"))
            req=srv.CreateAuthPacket(code=pyrad.packet.AccessRequest,
                        User_Name=self.principal['user'][0],
                        NAS_Identifier="localhost")
            req["User-Password"]=req.PwCrypt(self.principal['password'][0])
            # FIXME is this over socket? then we should not block here
            reply=srv.SendPacket(req)
            _log.debug("Attributes returned by server:")
            for i in reply.keys():
                _log.debug("%s: %s" % (i, reply[i]))
            if reply.code==pyrad.packet.AccessAccept:
                _log.debug("Security:access accepted")
                auth.append(True)
#                return True
            else:
                _log.debug("Security: access denied")
                auth.append(False)
#                return False
        self.auth['user']=auth
        return any(auth)

    def authenticate_using_local_database(self):
        """ Authenticate a principal against config stored information
            This is primarily intended for testing purposes,
            since passwords arn't stored securily.
        """
        if 'local_users' not in self.sec_conf['authentication']:
            _log.debug("local_users not found in security_conf: %s" % self.sec_conf['authentication'])
            return False
        # Verify users against stored passwords
        # TODO expand with other principal types
        d = self.sec_conf['authentication']['local_users']
        if not ('user' in self.principal and 'password' in self.principal):
            return False
        if len(self.principal['user']) != len(self.principal['password']):
            return False
        auth = []
        for user, password in zip(self.principal['user'], self.principal['password']):
            if user in d.keys():
                if d[user] == password:
                    _log.debug("Security: found user: %s",user)
                    auth.append(True)
                else:
                    _log.debug("Security: incorrect username or password")
                    auth.append(False)
            else:
                auth.append(False)
        self.auth['user'] = auth
        return any(auth)

    def check_security_actor_requirements(self, requires):
        _log.debug("Security: check_security_actor_requirements")
        if self.sec_conf and self.sec_conf['access_control_enabled'] == "True":
            for req in requires:
                if not self.check_security_policy_actor(req, "user", self.principal):
                    return False
        #no security config, so access control is disabled
        return True

    def check_security_policy_actor(self, req, principal_type, principal):
        """ Checks that the requirement is allowed by the security policy """
        _log.debug("Security: check_security_policy_actor")
        #Calling function shall already have checked that self.sec_conf exist
        #create list, e.g., ['calvinsys','media','camera','lense']
        temp = req.split(".")
        while len(temp) >0:
            temp2 = '.'.join(temp)
            # Satisfied when one principal match in one policy
            for plcy in [p for p in self.sec_policy.values() if temp2 in p['resource']]:
                if any([principal_name in plcy['principal'][principal_type]
                            for principal_type, principal_names in principal.iteritems()
                                if principal_type in plcy['principal']
                            for principal_name, auth in zip(principal_names, self.auth[principal_type])
                                if auth]):
                    _log.debug("Security: found a match for %s against %s" % (req, temp2))
                    return True
            #Let's go up in hierarchy, e.g. if we found no policy for calvinsys.media.camera
            #let's now try calvinsys.media instead
            temp.pop()
        #The user is not in the list of allowed users for the resource
        _log.debug("Security: the principal does not have access rights to resource: %s" % req)
        return False

    @staticmethod
    def verify_signature_get_files(filename, skip_file=False):
        # Get the data
        sign_filenames = filename + ".sign.*"
        sign_content = {}
        file_content = ""
        sign_files = {os.path.basename(f).split(".sign.")[1]: f for f in glob.glob(sign_filenames)}
        for cert_hash, sign_filename in sign_files.iteritems():
            try:
                with open(sign_filename, 'rt') as f:
                    sign_content[cert_hash] = f.read()
                    _log.debug("Security: found signature for %s" % cert_hash)
            except:
                pass
        if not skip_file:
            try:
                with open(filename, 'rt') as f:
                    file_content = f.read()
            except:
                return None
                _log.debug("Security: file can't be opened")
        return {'sign': sign_content, 'file': file_content}

    def verify_signature(self, file, flag):
        content = Security.verify_signature_get_files(file)
        if content:
            return self.verify_signature_content(content, flag)
        else:
            return False

    def verify_signature_content(self, content, flag):
        _log.debug("Security: verify %s signature of %s" % (flag, content))
        if not self.sec_conf:
            _log.debug("Security: no signature verification required: %s"% content['file'])
            return True

        if flag not in ["application", "actor"]:
            # TODO add component verification
            raise NotImplementedError

        # loop through the policies until one is found that applies to the principal
        # Verification OK if sign and cert OK for any principal matching policy
        # that have previously been authorized
        for plcy in self.sec_policy.values():
            _log.debug("Security: verify_signature policy: %s\nprincipal: %s\nauth:%s" %
                        (plcy, self.principal, self.auth))
            if any([principal_name in plcy['principal'][principal_type]
                        for principal_type, principal_names in self.principal.iteritems()
                            if principal_type in plcy['principal']
                        for principal_name, auth in zip(principal_names, self.auth[principal_type])
                            if auth]):
                _log.debug("Security: found a policy with matching principal")
                if (flag + '_signature') in plcy:
                    if self.verify_signature_and_certificate(content, plcy, flag):
                        _log.debug("Security: signature verification successfull")
                        return True
        _log.error("Security: verification of %s signature failed 1" % flag)
        return False

    def verify_signature_and_certificate(self, content, plcy, flag):
        if "__unsigned__" in plcy[flag + '_signature']:
            _log.debug("Security: %s is allowed unsigned" % flag)
            return True

        if content is None:
            _log.debug("Security: %s need file and signature with certificate hash" % flag)
            return False

        if not content['sign']:
            _log.debug("Security: %s signature information missing" % flag)
            return False

        if not HAS_OPENSSL:
            _log.error("Security: Install openssl to allow verification of signatures and certificates")
            _log.error("Security: verification of %s signature failed 2" % flag)
            return False

        _log.debug("Security:verify_signature_and_certificate")
        for cert_hash, signature in content['sign'].iteritems():
            try:
                trusted_cert = os.path.join(self.sec_conf['signature_trust_store'], cert_hash + ".0")
                with open(trusted_cert, 'rt') as f:
                    string_trusted_cert = f.read()
                    trusted_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, string_trusted_cert)
                    if self.check_signature_policy(trusted_cert, flag, plcy):
                        try:
                            OpenSSL.crypto.verify(trusted_cert, signature, content['file'], 'sha256')
                            _log.debug("Security: %s signature correct" % flag)
                            return True
                        except Exception as e:
                            _log.debug("Security: OpenSSL verification error", exc_info=True)
                            continue
                    else:
                        _log.debug("Security: signature policy not fulfilled")
                        continue
            except Exception as e:
                _log.debug("Security: error opening one of the needed certificates", exc_info=True)
                continue
        _log.error("Security: verification of %s signature failed 3" % flag)
        return False

    def check_signature_policy(self, cert, flag, plcy):
        """ Checks that if the signer is allowed by the security policy """
        _log.debug("Security:check_signature_policy")
        if flag=="application":
            if 'application_signature' in plcy:
                if cert.get_issuer().CN not in plcy['application_signature']:
                    _log.debug("Security: application signer not allowed")
                    return False
            else:
                _log.debug("Security: no application_signature element, unsigned applications allowed")
        elif flag=="actor":
            if 'actor_signature' in plcy:
                if cert.get_issuer().CN not in plcy['actor_signature']:
                    _log.debug("Security: actor signer not allowed")
                    return False
            else:
                _log.debug("Security: no actor_signature element, unsigned applications allowed")
        return True


