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
import time
import random
import shutil
from calvin.utilities import confsort
import OpenSSL
from calvin.utilities import calvinuuid
from calvin.utilities import calvinconfig
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.utils import get_home

_log = get_logger(__name__)
_conf = calvinconfig.get()
BEGIN_LINE = "-----BEGIN CERTIFICATE-----"


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
                       'prompt': 'no',
                       'default_keyfile': 'privkey.pem',
                       'default_bits': '2048'},
               'req_attributes': {},
               'req_distinguished_name': {'0.organizationName': 'domain',
                                          'commonName': 'runtime'},
               'ca': {'default_ca': 'CA_default'},
               'CA_default': {'dir': '~/.calvin/security/',
                              'preserve': 'no',
                              'crl_dir': '$dir/crl',
                              'RANDFILE': '$dir/private/.rand',
                              'certificate': '$dir/cacert.pem',
                              'database': '$dir/index.txt',
                              'private_dir': '$dir/private/',
                              'new_certs_dir': '$dir/newcerts',
                              'private_key': '$dir/private/ca.key',
                              'runtimes_dir': '$dir/runtimes',
                              'email_in_dn': 'no',
                              'x509_extensions': 'usr_cert',
                              'copy_extensions': 'none',
                              'certs': '$dir/certs',
                              'default_days': '365',
                              'policy': 'policy_any',
                              'cert_opt': 'ca_default',
                              'serial': '$dir/serial',
                              'default_crl_days': '30',
                              'name_opt': 'ca_default',
                              'crl': '$dir/crl.pem',
                              'default_md': 'sha256'},
               'v3_ca': {'subjectKeyIdentifier': 'hash',
                         'authorityKeyIdentifier':
                         'keyid:always,issuer:always',
                         'basicConstraints': 'CA:true'},
               'usr_cert': {'subjectKeyIdentifier': 'hash',
                            'authorityKeyIdentifier': 'keyid,issuer',
                            'basicConstraints': 'CA:false'},
               'policy_any': {'countryName': 'optional',
                              'organizationalUnitName': 'optional',
                              'organizationName': 'supplied',  # match
                              'emailAddress': 'optional',
                              'commonName': 'supplied',
                              'dnQualifier': 'optional',
                              'stateOrProvinceName': 'optional'}}
    # TODO Find out why the policy does not match equal org names.

    def __init__(self, configfile=None, domain=None, commonName=None, force=False, readonly=False):
        self.configfile = configfile
        self.commonName = commonName or 'runtime'
        self.config = ConfigParser.SafeConfigParser()
        self.config.optionxform = str
        os.umask(0077)

        if configfile is not None:  # Open existing config file
            self.configuration = self.parse_opensslconf()

        elif configfile is None and domain is not None:
            self.domain = domain
            homefolder = get_home()
            self.configfile = os.path.join(homefolder, ".calvin",
                                           "security", domain,
                                           "openssl.conf")
            exist = os.path.isfile(self.configfile)
            if not exist and readonly:
                raise Exception("Configuration file does not exist, create CA first")
            if exist and not force:
                self.configuration = self.parse_opensslconf()
                print "Configuration already exists " \
                      "using {}".format(self.configfile)
            else:
                self.new_opensslconf()
                self.configuration = self.parse_opensslconf()
                print "Made new configuration at " \
                      "{}".format(self.configfile)
        else:
            raise Exception("Missing argument, neither domain nor "
                            "configfile supplied.")

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
                elif option == "dir":
                    value = directory
                elif section == 'req_distinguished_name' and option == 'commonName':
                    value = self.commonName
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
            configfd.close()
        confsort.reorder(self.configfile)

    def parse_opensslconf(self):
        """
        Parse the openssl.conf file to find relevant paths.
        """
        self.config.read(self.configfile)
        configuration = {}
        for section in self.__class__.DEFAULT.keys():
            for option in self.__class__.DEFAULT[section].keys():
                raw = self.config.get(section, option)
                value = raw.split("#")[0].strip()  # Remove comments

                if "$" in value:  # Manage openssl variables
                    variable = "".join(value.split("$")[1:])
                    variable = variable.split("/")[0]
                    path = "/" + "/".join(value.split("/")[1:])
                    varvalue = self.config.get(section, variable)
                    value = varvalue.split("#")[0].strip() + path
                try:
                    configuration[section].update({option: value})
                except KeyError:
                    configuration[section] = {}  # New section
                    configuration[section].update({option: value})
        return configuration


def incr(fname):
    """
    Open a file read an integer from the first line.
    Increment by one and save.
    """
    fhandle = open(fname, 'r+')
    current = int(fhandle.readline(), 16)
    print(current)
    current = current + 1
    fhandle.seek(0)
    fhandle.write(str(format(current, 'x')))
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
    log = subprocess.Popen(["openssl", "x509",
                            "-sha256",
                            "-in", filename,
                            "-noout",
                            "-fingerprint"],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    stdout, stderr = log.communicate()
    if log.returncode != 0:
        raise IOError(stderr)
    try:
        fingerprint = stdout.split("=")[1].strip()
    except (IndexError, AttributeError):
        errormsg = "Error fingerprinting " \
                   "certificate file. {}".format(stderr)
        raise IOError(errormsg)

    return fingerprint


def new_runtime(conf, name, nodeid=None):
    """
    Create new runtime certificate.
    Return name of certificate signing request file.

    Equivalent of:
    mkdir -p $new_certs_dir
    openssl req -config $OPENSSL_CONF -new \
                -newkey rsa:2048 -nodes \
                -out $new_certs_dir/runtime.csr \
                -keyout $private_dir/runtime.key
    """
    outpath = conf.configuration["CA_default"]["new_certs_dir"]
    name_dir = os.path.join(conf.configuration["CA_default"]["runtimes_dir"], name)
    private_key = os.path.join(name_dir, "private", "private.key")
    private = os.path.dirname(private_key)

    out = os.path.join(outpath, "{}.csr".format(name))

    os.umask(0077)

    try:
        os.makedirs(outpath, 0755)
    except OSError:
        pass

    try:
        os.makedirs(private, 0700)
    except OSError:
        pass

    organization = conf.domain
    commonname = name
    dnQualifier =  "any" if nodeid is None else nodeid
    subject = "/O={}/CN={}/dnQualifier={}".format(organization, commonname, dnQualifier)
    # Creates ECC-based certificate
    log = subprocess.Popen(["openssl", "ecparam", "-genkey",
                            "-name", "prime256v1",
                            "-out", private_key],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    stdout, stderr = log.communicate()
    if log.returncode != 0:
        raise IOError(stderr)

    log = subprocess.Popen(["openssl", "req", "-new",
                            "-subj", subject,
                            "-key", private_key,
                            "-nodes",
                            "-utf8",
                            "-out", out],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    stdout, stderr = log.communicate()
    if log.returncode != 0:
        raise IOError(stderr)
    return out
    # Creates RSA-based certificate
    # log = subprocess.Popen(["openssl", "req", "-new",
    #                         "-subj", subject,
    #                         "-newkey", "rsa:2048",
    #                         "-nodes",
    #                         "-utf8",
    #                         "-out", out,
    #                         "-keyout", private_key],
    #                        stdout=subprocess.PIPE,
    #                        stderr=subprocess.PIPE)
    # stdout, stderr = log.communicate()
    # if log.returncode != 0:
    #     raise IOError(stderr)
    # return out

def remove_domain(domain, directory=None):
    """
    Remove an existing domain uses default security
    directory if not supplied.
    """
    homefolder = get_home()
    domaindir = directory or os.path.join(homefolder, ".calvin", "security", domain)
    configfile = os.path.join(domaindir, "openssl.conf")
    if os.path.isfile(configfile):
        shutil.rmtree(domaindir, ignore_errors=True)

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
    openssl req -new -x509 -config $OPENSSL_CONF \
            -keyout $private_key -out $certificate \
            -passout file:$private_dir/ca_password
    """
    outpath = conf.configuration["CA_default"]["new_certs_dir"]
    private = conf.configuration["CA_default"]["private_dir"]
    crlpath = conf.configuration["CA_default"]["crl_dir"]
    private_key = conf.configuration["CA_default"]["private_key"]
    out = conf.configuration["CA_default"]["certificate"]

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

    log = subprocess.Popen(["openssl", "rand",
                            "-out", password_file, "20"],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    stdout, stderr = log.communicate()
    if log.returncode != 0:
        raise IOError(stderr)

    log = subprocess.Popen(["openssl", "req",
                            "-new",
                            "-config", conf.configfile,
                            "-x509",
                            "-utf8",
                            "-subj", subject,
                            "-passout",
                            "file:{}".format(password_file),
                            "-out", out,
                            "-keyout", private_key],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    stdout, stderr = log.communicate()
    if log.returncode != 0:
        raise IOError(stderr)
    return out

def copy_cert(conf, path):
    """
    Copy the certificate giving it the name that can be stored in
    trustStore for verification of signatures.
    file is the out file

    """
    cert_file = conf.configuration["CA_default"]["certificate"]

    try:
        with open(cert_file, 'rt') as f:
            cert_str = f.read()
            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_str)
            cert_hash = format(cert.subject_name_hash(),'x')
    except:
        _log.exception("Failed to get certificate hash")
        raise Exception("Failed to get certificate hash")
    out_file = os.path.join(path, cert_hash + ".0")
    shutil.copyfile(cert_file, out_file)
    return out_file

def sign_file(conf, file):
    """
    Sign an actor, component or application.
    Store the signature in <file>.sign.<hash-cert>
    Conf is a Config object with a loaded openssl.conf configuration.
    File is the file to be signed.

    Equivalent of:
    openssl dgst -sha256 -sign "$private_key"
                -out "$file.sign.<cert-hash>"
                -passin file:$private_dir/ca_password
                 "$file"
    """
    private = conf.configuration["CA_default"]["private_dir"]
    cert_file = conf.configuration["CA_default"]["certificate"]
    private_key = conf.configuration["CA_default"]["private_key"]
    password_file = os.path.join(private, "ca_password")

    try:
        with open(cert_file, 'rt') as f:
            cert_str = f.read()
            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_str)
            cert_hash = format(cert.subject_name_hash(),'x')
    except:
        _log.exception("Failed to get certificate hash")
        raise Exception("Failed to get certificate hash")
    sign_file = file + ".sign." + cert_hash
    log = subprocess.Popen(["openssl", "dgst", "-sha256",
                            "-sign", private_key,
                            "-passin", "file:" + password_file,
                            "-out", sign_file,
                            file],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    stdout, stderr = log.communicate()
    if log.returncode != 0:
        raise IOError(stderr)
    return sign_file

def sign_req(conf, req, name):
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
    name_dir = os.path.join(conf.configuration["CA_default"]["runtimes_dir"], name)

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

    fname_lock = "{}.lock".format(conf.configuration["CA_default"]["serial"])
    fdlock = None
    try:
        # Take primitive lock
        while True:
            try:
                fdlock = os.open(fname_lock, os.O_CREAT|os.O_EXCL|os.O_RDWR)
            except OSError:
                # Try again
                time.sleep(random.random()*0.2)
                continue
            break

        serial = incr(conf.configuration["CA_default"]["serial"])

        log = subprocess.Popen(["openssl", "ca",
                                "-in", request,
                                "-utf8",
                                "-config", conf.configfile,
                                "-out", signed,
                                "-passin", "file:" + password_file],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               stdin=subprocess.PIPE)

        log.stdin.write("y\r\n")
        stdout, stderr = log.communicate("y\r\n")
        if log.returncode != 0:
            raise IOError(stderr)

        fp = fingerprint(signed)
        newcert = "{}.pem".format(fp.replace(":", "")[-40:])
    except:
        pass
    finally:
        # Release primitive lock
        if fdlock:
            try:
                os.close(fdlock)
                os.remove(fname_lock)
            except:
                pass

    try:
        os.makedirs(os.path.join(name_dir, "mine"))
    except OSError:
        pass
    try:
        os.makedirs(os.path.join(name_dir, "others"))
    except OSError:
        pass

    newkeyname = os.path.join(name_dir, "mine", newcert)
    print(signed)
    print(newkeyname)
    os.rename(signed, newkeyname)
    return newkeyname

###########################################################
# Linking a runtime name on a host to a persistent node-id
# This linkage is included in CSR and signed by CA
###########################################################

def obtain_cert_node_info(name):
    """ Obtain node id based on name and domain from config
        Return dict with domain, node name and node id
    """
    cert_conffile = _conf.get("security", "certificate_conf")
    domain = _conf.get("security", "certificate_domain")
    if domain is None or name is None:
        # No security or name specified just use standard node UUID
        _log.debug("OBTAINING no security domain={}, name={}".format(domain, name))
        return {'domain': None, 'name': name, 'id': calvinuuid.uuid("NODE")}

    cert_conf = Config(cert_conffile, domain)
    name_dir = os.path.join(cert_conf.configuration["CA_default"]["runtimes_dir"], name)
    # Does existing signed runtime certificate exist, return info
    try:
        filenames = os.listdir(os.path.join(name_dir, "mine"))
        content = open(os.path.join(name_dir, "mine", filenames[0]), 'rt').read()
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                              content)
        subject = cert.get_subject()
        if subject.commonName != name or subject.organizationName != domain:
            raise
        _log.debug("OBTAINING existing security domain={}, name={}".format(domain, name))
        return {'domain': domain, 'name': name, 'id': subject.dnQualifier}
    except:
        pass
        #_log.exception("OBTAINING fail existing security domain={}, name={}".format(domain, name))

    # Create new CSR
    csrfile = new_runtime(cert_conf, name, nodeid=calvinuuid.uuid("NODE"))
    _log.debug("OBTAINING new security csr={}, domain={}, name={}".format(csrfile, domain, name))
    try:
        content = open(csrfile, 'rt').read()
        cert = OpenSSL.crypto.load_certificate_request(OpenSSL.crypto.FILETYPE_PEM,
                                                      content)
        subject = cert.get_subject()
        # TODO multicast signing of CSR, now just sign it assuming local CA
        sign_req(cert_conf, os.path.basename(csrfile), name)
        _log.debug("OBTAINING new security domain={}, name={}".format(domain, name))
        return {'domain': domain, 'name': name, 'id': subject.dnQualifier}
    except:
        #_log.exception("OBTAINING fail new security domain={}, name={}".format(domain, name))
        return {'domain': None, 'name': name, 'id': calvinuuid.uuid("NODE")}

