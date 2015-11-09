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

import ConfigParser
import subprocess
import sys

class Config():
    SECTIONS = {
        "CA_default":["dir", "certs", "crl_dir", "database", \
                      "new_certs_dir", "certificate", "serial", \
                      "crl", "private_key", "RANDFILE", \
                      "x509_extensions", "default_days", \
                      "default_crl_days", "default_md", "preserve", "policy", \
                      "email_in_dn", "name_opt", "cert_opt", \
                      "copy_extensions"], \
        "policy_any":["countryName", "stateOrProvinceName", \
                      "organizationName", "organizationalUnitName", \
                      "commonName", "emailAddress"], \
        "req":["default_bits", "default_keyfile", "distinguished_name", \
               "attributes", "prompt"]
    }

    def __init__(self, configfile="./openssl.conf"):
        self.configfile = configfile
        print self.parse_opensslconf()

    def parse_opensslconf(self):
        """
        Parse the openssl.conf file to find relevant paths.
        """
        config = ConfigParser.SafeConfigParser()
        config.read(self.configfile)
        configuration = {}
        for section in self.__class__.SECTIONS.keys():
            for item in self.__class__.SECTIONS[section]:
                raw = config.get(section, item)
                entry = raw.split("#")[0].strip()
                try:
                   configuration[section].append({item: entry})
                except KeyError:
                   configuration[section] = []
                   configuration[section].append({item: entry})
        return configuration


def new_runtime():
    """
    Create new runtime certificate.

    Equivalent of:
    mkdir -p $new_certs_dir
    openssl req -config $OPENSSL_CONF -new -newkey rsa:2048 -nodes -out $new_certs_dir/runtime.csr -keyout $private_dir/runtime.key
    """
    pass

def new_domain():
    """
    Create new domain Certificate Authority Cert.

    Equivalent of:
    echo "Creating a certificate authority for a new domain."
    mkdir -p -m 700 $private_dir
    mkdir -p -m 700 $crl_dir
    chmod 700 $private_dir #Because chmod -m is not recursive
    echo 1000 > $dir/serial
    touch $dir/index.txt
    openssl rand -out $private_dir/ca_password 20
    openssl req -new -x509 -config $OPENSSL_CONF -keyout $private_key -out $certificate -passout file:$private_dir/ca_password
    """
    pass

def sign_req():
    """
    Sign a certificate request.

    Equivalent of:
    mkdir -p $certs
    openssl ca -in $new_certs_dir/$SIGN_REQ -config $OPENSSL_CONF -out $certs/runtime.pem -passin file:$private_dir/ca_password
    """
    pass
