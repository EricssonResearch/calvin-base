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

    To access a previously known openssl configuration file.
    myconf = Config(configfile="/tmp/openssl.conf")

    or to create a new domain:
    myconf = Config(domain="mydomain")

    to access an existing known domain configuration use:
    myconf = Config(domain="myolddomain")
    """
    DEFAULT = {'v3_req': {'subjectAltName': 'email:move'},
               'req': {'distinguished_name': 'req_distinguished_name',
                       'attributes': 'req_attributes',
                       'prompt': 'no', 'default_keyfile': 'privkey.pem',
                       'default_bits': '2048'},
               'req_attributes': {},
               'req_distinguished_name': {'0.organizationName': 'domain',
                                          'commonName': 'runtime'},
               'ca': {'default_ca': 'CA_default'},
               'CA_default': {'adir': '~/.calvin/security/',
                              'preserve': 'no',
                              'crl_dir': '$adir/crl',
                              'RANDFILE': '$adir/private/.rand',
                              'certificate': '$adir/cacert.pem',
                              'database': '$adir/index.txt',
                              'private_dir': '$adir/private/',
                              'new_certs_dir': '$adir/newcerts',
                              'private_key': '$adir/private/ca.key',
                              'email_in_dn': 'no',
                              'x509_extensions': 'usr_cert',
                              'copy_extensions': 'none',
                              'certs': '$adir/certs',
                              'default_days': '365',
                              'policy': 'policy_any',
                              'cert_opt': 'ca_default',
                              'serial': '$adir/serial',
                              'default_crl_days': '30',
                              'name_opt': 'ca_default',
                              'crl': '$adir/crl.pem',
                              'default_md': 'sha256'},
               'v3_ca': {'subjectKeyIdentifier': 'hash',
                         'authorityKeyIdentifier': 'keyid:always,issuer:always',
                         'basicConstraints': 'CA:true'},
               'usr_cert': {'subjectKeyIdentifier': 'hash',
                            'authorityKeyIdentifier': 'keyid,issuer',
                            'basicConstraints': 'CA:false'},
               'policy_any': {'string_mask': 'utf8only',
                              'countryName': 'optional',
                              'organizationalUnitName': 'optional',
                              'organizationName': 'supplied', # match
                              'emailAddress': 'optional',
                              'commonName': 'supplied',
                              'stateOrProvinceName': 'optional'}
              }
    # TODO Add function to reorder configuration file to put variables on top.
    # TODO Add additional documentation in docstrings.
    # TODO Clean up pep8 compatability.
    # TODO Find out why the policy does not match equal org names.
    def __init__(self, configfile=None, domain=None):
        self.configfile = configfile
        self.config = ConfigParser.SafeConfigParser()
        self.config.optionxform = str
        os.umask(0077)

        if configfile != None: # Open existing config file
            self.configuration = self.parse_opensslconf()

        elif configfile == None and domain != None:
            self.domain = domain
            homefolder = os.getenv("HOME")
            self.configfile = os.path.join(homefolder, ".calvin",
                                           "security", domain,
                                           "openssl.conf")
            if os.path.isfile(self.configfile):
                self.configuration = self.parse_opensslconf()
                print "Configuration already exists " \
                      "using {}".format(self.configfile)
            else:
                self.new_opensslconf()
                self.configuration = self.parse_opensslconf()
                print "Made new configuration at " \
                      "{}".format(self.configfile)

    def new_opensslconf(self):
        """
        Create new openssl.conf configuration file.
        """
        directory = os.path.dirname(self.configfile)

        for section in self.__class__.DEFAULT.keys():
            self.config.add_section(section)
            print "[{}]".format(section)
            for option in self.__class__.DEFAULT[section]:
                if option == "0.organizationName":
                    value = self.domain
                elif option == "adir":
                    value = directory
                else:
                    value = self.__class__.DEFAULT[section][option]
                self.config.set(section, option, value)
                print "\t{}={}".format(option, value)

        try:
            os.makedirs(directory, 0700)
        except OSError, e:
            print e
        with open(self.configfile, 'wb') as configfd:
            self.config.write(configfd)

    def parse_opensslconf(self):
        """
        Parse the openssl.conf file to find relevant paths.
        """
        self.config.read(self.configfile)
        configuration = {}
        for section in self.__class__.DEFAULT.keys():
            for option in self.__class__.DEFAULT[section].keys():
                raw = self.config.get(section, option)
                value = raw.split("#")[0].strip() # Remove comments

                if "$" in value: # Manage openssl variables
                    variable = "".join(value.split("$")[1:])
                    variable = variable.split("/")[0]
                    path = "/" + "/".join(value.split("/")[1:])
                    varvalue = self.config.get(section, variable)
                    value = varvalue.split("#")[0].strip() + path
                try:
                    configuration[section].update({option: value})
                except KeyError:
                    configuration[section] = {} # New section
                    configuration[section].update({option: value})
        return configuration

def incr(fname):
    """
    Open a file read an integer from the first line.
    Increment by one and save.
    """
    fhandle = open(fname, 'r+')
    current = int(fhandle.readline())
    current = current + 1
    fhandle.seek(0)
    fhandle.write(str(current))
    fhandle.truncate()
    fhandle.close()
    return current

def touch(fname, times=None):
    """
    Touch a file to update the file timestamp.
    """
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
    log = subprocess.Popen(["openssl", "x509", "-sha256",
                           "-in", filename, "-noout",
                           "-fingerprint"],
          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = log.communicate()
    try:
        fingerprint = stdout.split("=")[1].strip()
    except (IndexError, AttributeError):
        errormsg = "Error fingerprinting " \
                   "certificate file. {}".format(stderr)
        raise OSError(errormsg)

    return fingerprint

# TODO Add better exception management for errors in subprocesses.
# For instance if an Error type 2 occurs on signing it is vital to
# revoke the previous certificate and renew the certificate.
# Error type two means that all certificates must have a unique
# subject.
# How ever this procedure is a catch 22 as it will not provide any
# secure channels to transmit the new certificate to the requester.

def new_runtime(conf, name):
    """
    Create new runtime certificate.
    Return name of certificate signing request file.

    Equivalent of:
    mkdir -p $new_certs_dir
    openssl req -config $OPENSSL_CONF -new -newkey rsa:2048 -nodes -out $new_certs_dir/runtime.csr -keyout $private_dir/runtime.key
    """
    outpath = conf.configuration["CA_default"]["new_certs_dir"]
    private = conf.configuration["CA_default"]["private_dir"]

    out = os.path.join(outpath, "{}.csr".format(name))
    private_key = os.path.join(private, "{}.key".format(name))

    os.umask(0077)

    try:
        os.mkdir(outpath, 0755)
    except OSError:
        pass

    try:
        os.mkdir(private, 0700)
    except OSError:
        pass

    organization = conf.domain
    commonname = name
    subject = "/O={}/CN={}".format(organization, commonname)
    log = subprocess.Popen(["openssl", "req", "-new",
                            #"-config", conf.configfile,
                            "-subj", subject,
                            "-newkey", "rsa:2048", 
                            "-nodes",
                            "-utf8",
                            "-out", out,
                            "-keyout", private_key],
             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = log.communicate()
    print stdout, stderr
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
    dirpath = conf.configuration["CA_default"]["adir"]

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

    touch(conf.configuration["CA_default"]["database"])
    serialfd = open(conf.configuration["CA_default"]["serial"], 'w')
    serialfd.write("1000")
    serialfd.close()

    organization = conf.domain
    commonname = conf.domain
    subject = "/O={}/CN={}".format(organization, commonname)

    log = subprocess.Popen(["openssl", "rand", "-out",
             password_file, "20"],
             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = log.communicate()
    print stdout, stderr

    log = subprocess.Popen(["openssl", "req", "-new","-config",
                            conf.configfile, "-x509", "-utf8",
                            "-subj", subject, "-passout",
                            "file:{}".format(password_file),
                            "-out", out, "-keyout", private_key],
             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = log.communicate()
    print stdout, stderr
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

    serial = incr(conf.configuration["CA_default"]["serial"])
    print "Using serial {}".format(serial)
    log = subprocess.Popen(["openssl", "ca", "-in", request, "-utf8",
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
