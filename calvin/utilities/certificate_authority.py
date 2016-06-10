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
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend
from calvin.utilities import certificate
from calvin.utilities import calvinuuid
from calvin.utilities import calvinconfig
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.utils import get_home

_log = get_logger(__name__)
_conf = calvinconfig.get()
BEGIN_LINE = "-----BEGIN CERTIFICATE-----"
BEGIN_CSR_LINE = "-----BEGIN CERTIFICATE REQUEST-----"


# Exceptions
class ConfigurationMalformed(Exception):
    """Configuration is missing required attributes to set policy."""
    pass


class CsrGenerationFailed(Exception):
    """CSR generation failed. An Error occured while generating a CSR."""
    pass


class CaDeniedConfiguration(Exception):
    """
    Ca cert is rejected due to Calvin security configuration
    or openssl.conf.
    """
    pass


class CaDeniedMalformed(Exception):
    """Ca cert is denied as it is malformed."""
    pass


class CertificateInvalid(Exception):
    """Certificate is not validly signed by CA."""
    pass


class CertificateMalformed(Exception):
    """Certificate is not validly signed by CA."""
    pass


class CertificateDeniedMalformed(Exception):
    """Ca cert is denied as it is malformed."""
    pass


class CertificateDeniedConfiguration(Exception):
    """Certificate is denied due to restrictions in configuration."""
    pass


class CsrDeniedConfiguration(Exception):
    """A CSR is rejected due to Calvin security configuration."""
    pass


class CsrDeniedMalformed(Exception):
    """A CSR is denied as it is malformed."""
    pass


class StoreFailed(Exception):
    """Storing failed."""
    pass


class TransmissionFailed(Exception):
    """Failed to transmit."""
    pass


class ListenFailed(Exception):
    """Listening to interface failed."""
    pass


class ListenTimeout(Exception):
    """Listening timed out before receiving anything."""
    pass


class CaNotFound(Exception):
    """The CA cert file was not found."""
    pass


class CA():
    """
    A openssl.conf configuration parser class.
    Create this object by pointing at the configuration file
    to be parsed.

    To access a previously known openssl configuration file.
    myconf = CA(configfile="/tmp/openssl.conf")

    or to create a new domain:
    myconf = CA(domain="mydomain")

    to access an existing known domain configuration use:
    myconf = CA(domain="myolddomain")
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

    def __init__(self, domain, commonName=None, security_dir=None, force=False, readonly=False):
        self.configfile = None
        self.commonName = commonName or 'runtime'
        self.config = ConfigParser.SafeConfigParser()
        self.config.optionxform = str
        os.umask(0077)
        self.domain = domain
        _log.debug("CA init")
        security_path = _conf.get("security", "security_path")
        if security_dir:
            self.configfile = os.path.join(security_dir, domain, "openssl.conf")
        elif security_path:
            self.configfile = os.path.join(security_path, domain, "openssl.conf")
        else:
            homefolder = get_home()
            self.configfile = os.path.join(homefolder, ".calvin",
                                           "security", domain,
                                           "openssl.conf")
        exist = os.path.isfile(self.configfile)
        if not exist and readonly:
            raise Exception("Configuration file does not exist, create CA first")
        if exist and not force:
            self.configuration = self.parse_opensslconf()
            _log.debug("Configuration already exists")

            print "Configuration already exists " \
                  "using {}".format(self.configfile)
        else:
            _log.debug("Configuration does not exist, let's create CA")
            self.new_opensslconf()
            self.configuration = self.parse_opensslconf()
            #Generate keys and CA certiticate
            try:
                self.new_ca_credentials(security_dir=security_dir,
                                        force=False,
                                        readonly=False)
            except:
                _log.error("creation of new CA credentials failed")
            print "Made new configuration at " \
                  "{}".format(self.configfile)

    def new_ca_credentials(self, security_dir=None, force=False, readonly=False):
        """
        Generate keys, files and certificate
        for the new CA
        """
        _log.debug("new_ca_credentials")
        outpath = self.configuration["CA_default"]["new_certs_dir"]
        private = self.configuration["CA_default"]["private_dir"]
        crlpath = self.configuration["CA_default"]["crl_dir"]
        private_key = self.configuration["CA_default"]["private_key"]
        out = self.configuration["CA_default"]["certificate"]

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

        certificate.touch(self.configuration["CA_default"]["database"])
        serialfd = open(self.configuration["CA_default"]["serial"], 'w')
        serialfd.write("1000")
        serialfd.close()
        _log.debug("new_ca_credentials")

        organization = self.domain
        commonname = self.commonName
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
                                "-config", self.configfile,
                                "-x509",
                                "-days", "1825",
                                "-utf8",
                                "-subj", subject,
                                "-passout",
                                "file:{}".format(password_file),
                                "-out", out,
                                "-keyout", private_key],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = log.communicate()
        _log.debug("new_ca_credentials")
        if log.returncode != 0:
            _log.error("CA req failed")
            raise IOError(stderr)
        return

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
        if not self.config.read(self.configfile):
            # Empty openssl.conf file or could not successfully parse the file.
            self.new_opensslconf()
        configuration = {}
        for section in self.__class__.DEFAULT.keys():
            for option in self.__class__.DEFAULT[section].keys():
                raw = self.config.get(section, option)
                value = raw.split("#")[0].strip()  # Remove comments

                if "$" in value:  # Manage OpenSSL variables
                    variable = "".join(value.split("$")[1:])
                    variable = variable.split("/")[0]
                    if variable == "calvindir":
                        varvalue = _conf.install_location()
                    else:
                        varvalue = self.config.get(section, variable).split("#")[0].strip()
                        if "$calvindir" in varvalue:
                            varvalue = _conf.install_location() + "/" + "/".join(varvalue.split("/")[1:])
                    path = "/" + "/".join(value.split("/")[1:])
                    value = varvalue + path
                try:
                    configuration[section].update({option: value})
                except KeyError:
                    configuration[section] = {}  # New section
                    configuration[section].update({option: value})
        return configuration

    def verify_configuration(self):
        """
        Verify that the self.conf and openssl.conf contains required fields.
        """
        try:
            if self.configuration['CA_default']['certificate'] is None:
                raise ConfigurationMalformed("Missing `CA_default`."
                                             "`certificate` variable"
                                             " in {}".format(cert_conf_file))
            if self.configuration['CA_default']['private_key'] is None:
                raise ConfigurationMalformed("Missing `CA_default`."
                                             "`private_key` variable"
                                             " in {}".format(cert_conf_file))
        except (Exception), err:
            raise ConfigurationMalformed(err)






    def remove_domain(self, domain, directory=None):
        """
        Remove an existing domain uses default security
        directory if not supplied.
        """
        homefolder = get_home()
        domaindir = directory or os.path.join(homefolder, ".calvin", "security", domain)
        configfile = os.path.join(domaindir, "openssl.conf")
        if os.path.isfile(configfile):
            shutil.rmtree(domaindir, ignore_errors=True)



    def get_ca_cert(self):
        """
        Return CA certificate if it exist,
        if not, raise exception

        """
        ca_cert_file = self.configuration["CA_default"]["certificate"]
        return certificate.load_cert(ca_cert_file)

    def export_ca_cert(self, path):
        """
        Copy the certificate giving it the name that can be stored in
        trustStore for verification of signatures.
        file is the out file

        """
        return certificate.export_cert(self.configuration["CA_default"]["certificate"], path)
        cert_file = self.configuration["CA_default"]["certificate"]

    #Is this needed for CA???#Is this needed for CA????
    def sign_file(self, file):
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
        private = self.configuration["CA_default"]["private_dir"]
        cert_file = self.configuration["CA_default"]["certificate"]
        private_key = self.configuration["CA_default"]["private_key"]
        password_file = os.path.join(private, "ca_password")

        try:
            certificate_hash = certificate.cert_hash(certpath=cert_file)
        except:
            _log.exception("Failed to get certificate hash")
            raise Exception("Failed to get certificate hash")
        sign_file = file + ".sign." + certificate_hash
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

    def store_csr(self, csr):
        """
        Store `csr` in newcerts location from configuration.
        Raise store failed if there was problems storing.
        Return path to csr-file.
        """
        new_cert = self.configuration["CA_default"]["new_certs_dir"]
        load_csr = OpenSSL.crypto.load_certificate_request
        try:
            csrx509 = load_csr(OpenSSL.crypto.FILETYPE_PEM, csr)
            subject = csrx509.get_subject()
            filename = "{}.csr".format(subject.commonName)
            filepath = os.path.join(new_cert, filename)
            with open(filepath, 'w') as csr_fd:
                csr_fd.write(csr)
        except (Exception), err:
            raise StoreFailed(err)
        return filepath

    def validate_csr(self, csr):
        """
        Validate that the `csr` matches with configuration.
        Raise CsrDeniedConfiguration if the CSR did not satisfy the
        configuration.
        Raise CsrDeniedMalformed if the csr could not be read at all.
        Raise CertDeniedConfiguration is the CSR key is too short.
        """
        _log.debug("ca.validate_csr %s" % csr)
        try:
            csrx509 = certificate.verify_certstr_with_policy(csr)
        except (OpenSSL.crypto.Error, IOError), err:
            raise CsrDeniedMalformed(err)
        except:
            raise
        try:
            subject = csrx509.get_subject()
            common_name = subject.commonName
            domain = subject.organizationName
            try:
                dnQualifier = subject.dnQualifier
            except:
                dnQualifier = "missing"
            _log.debug("CSR name: subject:%s %s org: %s qualifier: %s" % (subject, common_name, domain, dnQualifier))
            if self.domain != domain:
                raise CsrDeniedConfiguration("Wrong domain, self.domain={}, domain={}".format(self.domain, domain))
            # TODO: Check more subject items against conf!
            # TODO: Make sure there is a configuration entry for CA services
            # to filter accepted nodes, e.g. implement node name whitelist.
            # The openssl policy can also do this ...
        except (OpenSSL.crypto.Error), err:
            raise CsrDeniedConfiguration(err)

    def sign_csr(self, request):
        """
        Sign a certificate request.
        Req is the name of a Certificate Signing Request in $new_certs_dir.

        Equivalent of:
        mkdir -p $certs
        openssl ca -in $new_certs_dir/$SIGN_REQ
                   -config $OPENSSL_CONF
                   -out $certs/runtime.pem
                   -passin file:$private_dir/ca_password
        """
        private = self.configuration["CA_default"]["private_dir"]
        certspath = self.configuration["CA_default"]["certs"]
        new_certs_dir = self.configuration["CA_default"]["new_certs_dir"]

        password_file = os.path.join(private, "ca_password")
        signed = os.path.join(certspath, "signed.pem")
        os.umask(0077)
        try:
            os.mkdir(private, 0700)
        except OSError:
            pass

        try:
            os.mkdir(certspath, 0700)
        except OSError:
            pass

        try:
            os.remove(signed)
        except:
            pass

        fname_lock = "{}.lock".format(self.configuration["CA_default"]["serial"])
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

            serial = certificate.incr(self.configuration["CA_default"]["serial"])

            log = subprocess.Popen(["openssl", "ca",
                                    "-in", request,
                                    "-utf8",
                                    "-config", self.configfile,
                                    "-out", signed,
                                    "-passin", "file:" + password_file],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE)

            log.stdin.write("y\r\n")
            stdout, stderr = log.communicate("y\r\n")
            if log.returncode != 0:
                raise IOError(stderr)

            fp = certificate.fingerprint(signed)
            newcert = "{}.pem".format(fp.replace(":", "")[-40:])
        except:
            _log.exception("Sign request failed")
            newcert = None
        finally:
            # Release primitive lock
            if fdlock:
                try:
                    os.close(fdlock)
                    os.remove(fname_lock)
                except:
                    pass
        if newcert is None:
            raise IOError("Could not sign certificate")

        newkeyname = os.path.join(new_certs_dir, newcert)
        print(signed)
        print(newkeyname)
        os.rename(signed, newkeyname)
        return newkeyname


    def verify_private_key_exist(self):
        """Return the node's private key"""
        return os.path.isfile(self.configuration["CA_default"]["private_key"])


    def get_ca_public_key(self):
        """Return the public key from certificate"""
        return certificate.get_public_key(self.configuration["CA_default"]["certificate"])

    def get_ca_conf(self):
        """Return path to openssl.conf for the CA"""
        _log.debug("get_ca_conf")
        is_ca = _conf.get("security","certificate_authority")
        if is_ca=="True":
            security_dir = _conf.get("security", "security_path")
            domain_name = _conf.get("security", "security_domain_name")
            if security_dir:
                cert_conf_file = os.path.join(security_dir,domain_name,"openssl.conf")
            else:
                homefolder = get_home()
                cert_conf_file = os.path.join(homefolder,"security",domain_name,"openssl.conf")
            return cert_conf_file
        else:
            return None

    ###########################################################
    # Linking a runtime name on a host to a persistent node-id
    # This linkage is included in CSR and signed by CA
    ###########################################################

    def obtain_cert_node_info(self, name):
        """ Obtain node id based on name and domain from config
            Return dict with domain, node name and node id
        """
        if self.domain is None or name is None:
            # No security or name specified just use standard node UUID
            _log.debug("OBTAINING no security domain={}, name={}".format(domain, name))
            return {'domain': None, 'name': name, 'id': calvinuuid.uuid("NODE")}

        runtime_dir = get_own_credentials_path(name)
        # Does existing signed runtime certificate exist, return info
        try:
            filenames = os.listdir(os.path.join(runtime_dir, "mine"))
            content = open(os.path.join(runtime_dir, "mine", filenames[0]), 'rt').read()
            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                  content)
            subject = cert.get_subject()
            if subject.commonName != name or subject.organizationName != self.domain:
                raise
            _log.debug("OBTAINING existing security domain={}, name={}".format(self.domain, name))
            return {'domain': self.domain, 'name': name, 'id': subject.dnQualifier}
        except:
            pass
            #_log.exception("OBTAINING fail existing security domain={}, name={}".format(domain, name))

        # No valid signed cert available, create new node id and let user create certificate later
        nodeid = calvinuuid.uuid("NODE")
        return {'domain': self.domain, 'name': name, 'id': nodeid}




