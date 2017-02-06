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
"""
Openssl wrapper used to generate and sign certificates.
This module depends on openssl.
"""

import os
import subprocess
import sys
import tempfile
import time
import random
import shutil
from calvin.utilities import confsort
import OpenSSL
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend
from calvin.utilities import certificate
from calvin.utilities import calvinuuid
from calvin.utilities import calvinconfig
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.utils import get_home

_log = get_logger(__name__)
_conf = calvinconfig.get()

class CS():
    """
    A Code Signer (CS) class used to sign actors and applications.
    The CS is uniquely identified by its organization and common
    name. If the CS does not exist, it will be created on first
    reference.

    """

    def __init__(self, organization, commonName, security_dir=None, force=False, readonly=False):
        self.cs_dir = self.get_cs_credentials_path(organization, security_dir)
        self.outpath = os.path.join(self.cs_dir, "new_signed_code")
        self.private = os.path.join(self.cs_dir, "private")
        self.private_key = os.path.join(self.private, "cs.key")
        self.out = os.path.join(self.cs_dir, "cs.pem")
        self.password_file = os.path.join(self.private, "cs_password")
        self.certificate = os.path.join(self.cs_dir, "cscert.pem")

        _log.debug("CS init, organization={}, commonName={}".format(organization, commonName))
        print"CS init, organization="+ organization+", commonName="+commonName
        exist = os.path.isdir(self.cs_dir)
        if not exist and readonly:
            raise Exception("CS dir does not exist, create Code Signer first")
        elif exist and not force:
            print "CS already exist, let's use it"
        else:
            _log.debug("Code signer dir does not exist, let's create CS")
            #Generate keys and CA certiticate
            try:
                self.new_cs_credentials(organization,
                                        commonName,
                                        security_dir=security_dir,
                                        force=False,
                                        readonly=False)
            except:
                _log.error("creation of new CS credentials failed")
            print "Made new code signer"

    def new_cs_credentials(self, organization, commonName, security_dir=None, force=False, readonly=False):
        """
        Generate keys, files and certificate
        for the new CA
        """
        _log.debug("new_cs_credentials")


        os.umask(0077)
        code_signers_dir = self.get_code_signers_credentials_path(security_dir) 
        if not os.path.isdir(code_signers_dir):
            try:
                os.mkdir(code_signers_dir, 0700)
            except OSError:
                pass
        try:
            os.mkdir(self.cs_dir, 0700)
        except OSError:
            pass

        try:
            os.mkdir(self.outpath, 0700)
        except OSError:
            pass

        try:
            os.mkdir(self.private, 0700)
        except OSError:
            pass

        subject = "/O={}/CN={}".format(organization, commonName)

        # Generate a password for protection of the private key,
        # store it in the password file
        password = self.generate_password(20)
        try:
            with open(self.password_file,'w') as fd:
                fd.write(password)
        except Exception as err:
            _log.err("Failed to write CS password to file, err={}".format(err))
            raise
        out = os.path.join(self.outpath, "{}.csr".format(organization))
        log = subprocess.Popen(["openssl", "req",
                                "-new",
                                "-x509",
                                "-days", "1825",
                                "-utf8",
                                "-subj", subject,
                                "-passout",
                                "file:{}".format(self.password_file),
                                "-out", self.certificate,
                                "-keyout", self.private_key],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = log.communicate()
        _log.debug("new_cs_credentials")
        if log.returncode != 0:
            _log.error("CS req failed")
            raise IOError(stderr)
        return

    def generate_password(self, length):
        from os import urandom
        _log.debug("generate_password, length={}".format(length))
        if not isinstance(length, int) or length < 8:
            raise ValueError("Password must be longer")

        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ123456789!#%&/()=?[]{}"
        return "".join(chars[ord(c) % len(chars)] for c in urandom(length))

    def remove_cs(self, cs_name, security_dir=None):
        """
        Remove an existing code signer, uses default security
        directory if not supplied.
        """
        cs_dir = get_cs_path(security_dir)
        if os.path.isdir(cs_dir):
            shutil.rmtree(cs_dir, ignore_errors=True)



    def get_cs_cert(self):
        """
        Return CA certificate if it exist,
        if not, raise exception

        """
        return certificate.load_cert(self.certificate)

    def export_cs_cert(self, path):
        """
        Copy the certificate giving it the name that can be stored in
        trustStore for verification of signatures.
        file is the out file

        """
        return certificate.export_cert(self.certificate, path)

    def sign_file(self, file, dir=None):
        """
        Sign an actor, component or application.
        Store the signature in <file>.sign.<hash-cert>
        File is the file to be signed.

        Equivalent of:
        openssl dgst -sha256 -sign "$private_key"
                    -out "$file.sign.<cert-hash>"
                    -passin file:$private_dir/ca_password
                     "$file"
        """
        _log.debug("sign_file: file={}".format(file))
        try:
            certificate_hash = certificate.cert_hash(certpath=self.certificate)
        except:
            _log.exception("Failed to get certificate hash")
            raise Exception("Failed to get certificate hash")
        sign_file_name = file + ".sign." + certificate_hash
        if dir:
            sign_file = os.path.join(dir, sign_file_name)
        else:
            sign_file = sign_file_name
        print "signed file name="+sign_file
        log = subprocess.Popen(["openssl", "dgst", "-sha256",
                                "-sign", self.private_key,
                                "-passin", "file:" + self.password_file,
                                "-out", sign_file,
                                file],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = log.communicate()
        if log.returncode != 0:
            raise IOError(stderr)
        with open(sign_file, 'rt') as f:
            signature = f.read()
        with open(file, 'rt') as f:
            content= f.read()
        with open(self.certificate, 'rt') as f:
            trusted_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, f.read())
            try:
                # Verify signature
                OpenSSL.crypto.verify(trusted_cert, signature, content, 'sha256')
                _log.debug("verify_signature_content: signature correct")
            except Exception as e:
                _log.error("OpenSSL verification error", exc_info=True)
        return sign_file



    def verify_private_key_exist(self):
        """Return the node's private key"""
        return os.path.isfile(self.private_key)


    def get_cs_public_key(self):
        """Return the public key from certificate"""
        return certificate.get_public_key(self.certificate)



    def get_cs_credentials_path(self, name, security_dir=None):
        """Return the node's own certificate name without file extension"""
        _log.debug("get_cs_credentials_path")
        return os.path.join(self.get_code_signers_credentials_path(security_dir), name)

    def get_code_signers_credentials_path(self, security_dir=None):
        """Return the node's own certificate name without file extension"""
        _log.debug("get_cs_credentials_path")
        return os.path.join(certificate.get_security_credentials_path(security_dir), "code_signers")

      
