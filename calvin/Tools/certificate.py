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
import os
import subprocess
import sys
import tempfile

class Config():
    """
    A openssl.conf configuration parser class.
    Create this object by pointing at the configuration file
    to be parsed.

    myconf = Config("/tmp/openssl.conf")
    """
    SECTIONS = {
        "CA_default":["dir", "certs", "crl_dir", "database",
                      "new_certs_dir", "certificate", "serial",
                      "crl", "private_dir", "RANDFILE",
                      "x509_extensions", "default_days",
                      "default_crl_days", "default_md", "private_key",
                      "preserve", "policy", "email_in_dn",
                      "name_opt", "cert_opt", "copy_extensions"],
        "policy_any":["countryName", "stateOrProvinceName",
                      "organizationName", "organizationalUnitName",
                      "commonName", "emailAddress"],
        "req":["default_bits", "default_keyfile",
               "distinguished_name", "attributes", "prompt"],
        "req_distinguished_name":["0.organizationName", 
                                  "commonName"],
        "usr_cert": ["basicConstraints", "subjectKeyIdentifier",
                     "authorityKeyIdentifier"],
        "v3_req": ["subjectAltName"],
        "v3_ca": ["subjectKeyIdentifier", "authorityKeyIdentifier",
                  "basicConstraints"]
    }

    def __init__(self, configfile="./openssl.conf"):
        self.configfile = configfile
        self.configuration = self.parse_opensslconf()

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

                if "$" in entry: # Manage openssl variables
                    variable = "".join(entry.split("$")[1:])
                    variable = variable.split("/")[0]
                    path = "/" + "/".join(entry.split("/")[1:])
                    entry = configuration[section][variable] + path
                try:
                    configuration[section].update({item: entry})
                except KeyError:
                    configuration[section] = {} # New section
                    configuration[section].update({item: entry})
        return configuration


def touch(fname, times=None):
    fhandle = open(fname, 'a')
    try:
        os.utime(fname, times)
    finally:
        fhandle.close()

def fingerprint(filename):
    """
    Return the sha256 fingerprint of a certificate `filename`.
    Can only be run on trusted/signed certificates.
    Equivalent to:
    openssl x509 -sha256 -in ./runtime.csr -noout -fingerprint
    """
    #f = open('./openssl.log', 'a')
    #e, errlog = tempfile.mkstemp()
    log = subprocess.Popen(["openssl", "x509", "-sha256",
                           "-in", filename, "-noout",
                           "-fingerprint"],
          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #f.close()
    stdout, stderr = log.communicate()
    try:
        fingerprint = stdout.split("=")[1].strip()
    except (IndexError, AttributeError):
        errormsg = "Error fingerprinting " \
                   "certificate file. {}".format(stderr)
        raise OSError(errormsg)

    return fingerprint

def new_runtime(conf):
    """
    Create new runtime certificate.
    Return name of certificate signing request file.

    Equivalent of:
    mkdir -p $new_certs_dir
    openssl req -config $OPENSSL_CONF -new -newkey rsa:2048 -nodes -out $new_certs_dir/runtime.csr -keyout $private_dir/runtime.key
    """
    outpath = conf.configuration["CA_default"]["new_certs_dir"]
    private = conf.configuration["CA_default"]["private_dir"]

    out = os.path.join(outpath, "runtime.csr")
    private_key = os.path.join(private, "newnode.key")

    os.umask(0077)

    try:
        os.mkdir(outpath, 0755)
    except OSError:
        pass

    try:
        os.mkdir(private, 0700)
    except OSError:
        pass

    f = open('./openssl.log', 'a')
    log = subprocess.Popen(["openssl", "req", "-config",
                            conf.configfile, "-new",
                            "-newkey", "rsa:2048", "-nodes",
                            "-out", out, "-keyout", private_key],
             stdout=f, stderr=f, stdin=subprocess.PIPE)
    f.close()

    # I would have liked to name the CSR as its fingerprint
    # but openss does not fingerprint unsigned certificates.
    #certfingerprint = fingerprint(out)

    #csrname = "{}.csr".format(certfingerprint)
    #csrpath = os.path.join(outpath, csrname)
    #os.rename(out, csrpath)
    #keyname = "{}.key".format(certfingerprint)
    #keypath = os.path.join(private, keyname)
    #os.rename(private_key, keypath)
    #return csrpath
    return out

def new_domain(conf):
    """
    Create new domain Certificate Authority Cert.
    Return path and filename of new domain certificate.

    Equivalent of:
    echo "Creating a certificate authority for a new domain."
    mkdir -p -m 700 $private_dir
    mkdir -p -m 700 $crl_dir
    chmod 700 $private_dir #Because mkdir -p -m is not recursive
    echo 1000 > $dir/serial
    touch $dir/index.txt
    openssl rand -out $private_dir/ca_password 20
    openssl req -new -x509 -config $OPENSSL_CONF -keyout $private_key -out $certificate -passout file:$private_dir/ca_password
    """
    outpath = conf.configuration["CA_default"]["new_certs_dir"]
    private = conf.configuration["CA_default"]["private_dir"]
    crlpath = conf.configuration["CA_default"]["crl_dir"]
    private_key = conf.configuration["CA_default"]["private_key"]
    out = conf.configuration["CA_default"]["certificate"]
    dirpath = conf.configuration["CA_default"]["dir"]

    password_file = os.path.join(private, "ca_password")

    os.umask(0077)
    try:
        os.mkdir(crlpath, 0700)
    except OSError:
        pass

    try:
        os.mkdir(outpath, 0700)
    except OSError:
        pass

    try:
        os.mkdir(private, 0700)
    except OSError:
        pass

    touch(os.path.join(dirpath, "index.txt"))
    serialfd = open(os.path.join(dirpath, "serial"), 'w')
    serialfd.write("1000")
    serialfd.close()

    #f = open('./openssl.log', 'a')
    log = subprocess.Popen(["openssl", "rand", "-out",
             password_file, "20"],
             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = log.communicate()
    print stdout, stderr

    log = subprocess.Popen(["openssl", "req", "-new","-config",
                            conf.configfile, "-x509",
                            "-passout", "file:" + password_file,
                            "-out", out, "-keyout", private_key],
             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = log.communicate()
    print stdout, stderr
    #f.close()
    #TODO: Rename certificate to the current domain name.
    #newkey = "{}.key".format(fingerprint(out))
    #newkeyname = os.path.join(private, newkey)
    #os.rename(private_key, newkeyname)
    return out

def sign_req(conf, req):
    """
    Sign a certificate request.
    Conf is a Config object with a loaded openssl.conf configuration.
    Req is the name of a Certificate Signing Request in $new_certs_dir.

    Equivalent of:
    mkdir -p $certs
    openssl ca -in $new_certs_dir/$SIGN_REQ
               -config $OPENSSL_CONF
               -out $certs/runtime.pem
               -passin file:$private_dir/ca_password
    """

    private = conf.configuration["CA_default"]["private_dir"]
    password_file = private + "ca_password"
    requestpath = conf.configuration["CA_default"]["new_certs_dir"]
    certspath = conf.configuration["CA_default"]["certs"]

    password_file = os.path.join(private, "ca_password")
    signed = os.path.join(certspath, "signed.pem")
    request = os.path.join(requestpath, req)

    os.umask(0077)
    try:
        os.mkdir(private, 0700)
    except OSError:
        pass

    try:
        os.mkdir(certspath, 0700)
    except OSError:
        pass

    log = subprocess.Popen(["openssl", "ca", "-in", request,
                           "-config", conf.configfile, "-out", signed,
                           "-passin", "file:" + password_file],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           stdin=subprocess.PIPE)

    log.stdin.write("y\r\n")
    stdout, stderr = log.communicate("y\r\n")
    print stdout, stderr
    fp = fingerprint(signed)
    newcert = "{}.pem".format(fp)
    newkeyname = os.path.join(certspath, newcert)
    os.rename(signed, newkeyname)
