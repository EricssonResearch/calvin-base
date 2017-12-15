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
import json
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

class CsrMissingPassword(Exception):
    """A CSR is denied as an no challenge password was supplied"""
    pass

class CsrIncorrectPassword(Exception):
    """A CSR is denied as an incorrect challenge password was supplied"""
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
                              'copy_extensions': 'copy',
                              'certs': '$dir/certs',
                              'default_days': '365',
                              'policy': 'policy_any',
                              'cert_opt': 'ca_default',
                              'serial': '$dir/serial',
                              'default_crl_days': '30',
                              'name_opt': 'ca_default',
                              'crl': '$dir/crl.pem',
                              'default_md': 'sha256'},
               'v3_ca': {'basicConstraints':'CA:true',
                        'subjectKeyIdentifier': 'hash',
                         'authorityKeyIdentifier':
                         'keyid:always,issuer:always'},
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
        _log.debug("__init__")
        self.configfile = None
        self.commonName = commonName or 'runtime'
        self.config = ConfigParser.SafeConfigParser()
        self.config.optionxform = str
        self.enrollment_challenge_db_path =None
        self.enrollment_challenge_db = {}
        self.allowed_authentication_servers = None
        self.allowed_authorization_servers = None
        os.umask(0077)
        self.domain = domain
        _log.debug("CA init")
        self.security_dir = _conf.get("security", "security_dir")
        if security_dir:
            self.configfile = os.path.join(security_dir, domain, "openssl.conf")
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

#            print "Configuration already exists " \
#                  "using {}".format(self.configfile)
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
                _log.error("Creation of new CA credentials failed")
                raise
#            print "Made new configuration at " \
#                  "{}".format(self.configfile)
            self.cert_enrollment_update_db_file()
        self.enrollment_challenge_db_path = os.path.join(self.configuration["CA_default"]["private_dir"],"enrollment_challenge_db.json")

    def new_ca_credentials(self, security_dir=None, force=False, readonly=False):
        """
        Generate keys, files and certificate
        for the new CA
        """
        from os import urandom
        _log.debug("new_ca_credentials")
        outpath = self.configuration["CA_default"]["new_certs_dir"]
        private = self.configuration["CA_default"]["private_dir"]
        crlpath = self.configuration["CA_default"]["crl_dir"]
        private_key = self.configuration["CA_default"]["private_key"]
        out = self.configuration["CA_default"]["certificate"]

        password_file = os.path.join(private, "ca_password")
        self.enrollment_challenge_db_path = os.path.join(private, "enrollment_challenge_db.json")

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

        organization = self.domain
        commonname = self.commonName
        subject = "/O={}/CN={}".format(organization, commonname)
        # Generate a password for protection of the private key,
        # store it in the password file
        password = self.generate_password(20)
        try:
            with open(self.enrollment_challenge_db_path,'w') as fd:
                fd.write("{}")
        except Exception as err:
            _log.error("Failed to creat CA enrollment_challenge_db file")
            raise
        try:
            with open(password_file,'w') as fd:
                fd.write(password)
        except Exception as err:
            _log.error("Failed to write CA password to file")
            raise
        # Generate keys and CA certificate
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

        try:
            os.makedirs(directory, 0700)
        except OSError, e:
            _log.error("Failed to create directory, err={}".format(e))
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
        _log.debug("sign_file: file={}".format(file))
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

    def store_csr_with_enrollment_password(self, plaintext):
        """
        Store `csr` in newcerts location from configuration.
        Raise store failed if there was problems storing.
        Return path to csr-file.
        """
#        _log.debug("store_csr_with_enrollment_password, plaintext={}".format(plaintext))
        plaintext_json = json.loads(plaintext)
        enrollment_password = plaintext_json['enrollment_password']
        csr = plaintext_json['csr']
        new_cert = self.configuration["CA_default"]["new_certs_dir"]
        load_csr = OpenSSL.crypto.load_certificate_request
        try:
            csrx509 = load_csr(OpenSSL.crypto.FILETYPE_PEM, csr)
            subject = csrx509.get_subject()
            filename = "{}.csr".format(subject.commonName)
            filepath = os.path.join(new_cert, filename)
            with open(filepath, 'w') as csr_fd:
                csr_fd.write(csr)
            with open(filepath +".enrollment_password", 'w') as csr_fd:
                csr_fd.write(enrollment_password)
        except EnvironmentError as err:
            raise StoreFailed(err)
        return filepath

    def validate_enrollment_password(self, enrollment_password, common_name):
        if not self.enrollment_challenge_db:
            self.cert_enrollment_load_db_file()
        if self.enrollment_challenge_db and self.enrollment_challenge_db[common_name]['password'] != enrollment_password:
            raise CsrIncorrectPassword("Incorrect challenge password, "
                                       "\n\t{}"
                                       "\n\t{}".format(self.enrollment_challenge_db[common_name]['password'],enrollment_password))


    def validate_csr(self, csr_path, enrollment_password=None, is_ca=False):
        """
        Validate that the `csr` matches with configuration.
        Args:
            csr_path: path to the CSR
            is_ca: if the CSR is for the current CA runtime, skipp enrollment
                    password verification
        Raise CsrDeniedConfiguration if the CSR did not satisfy the
        configuration.
        Raise CsrDeniedMalformed if the csr could not be read at all.
        Raise CertDeniedConfiguration is the CSR key is too short.
        """
        _log.debug("CA::validate_csr"
                   "\n\tcsr_path={}"
                   "\n\tenrollment_password={}"
                   "\n\tis_ca={}".format(csr_path, enrollment_password, is_ca))
        try:
            with open(csr_path) as fd:
                csr=fd.read()
        except EnvironmentError as err:
            _log.exception("Failed to open CSR file, err={}".format(err))
            raise
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
            #Only runtimes listed in the CA runtime configuration are allowed
            #to claim a runtime name with authz in. This is use full to prevent
            #any runtime from being an applicable authorization server when they are
            #automatically bootstraped from the DHT. Runtimes can now filter out valide
            #authorization server by looking at the certified runtime name in the certificate
            if "authzserver" in common_name:
                if not self.runtime_in_allowed_authorization_server_list(common_name):
                    _log.error("The runtime is not allowed to operate as an authorization server."
                                    "To be applicable, the runtime name must be listed in the"
                                    "allowed_authz_list.json white list file for the CA runtime."
                                    "\nUsed runtime commonName={}".format(common_name))
                    raise Exception("The runtime is not allowed to operate as an authorization server."
                                    "To be applicable, the runtime name must be listed in the"
                                    "allowed_authz_list.json white list file for the CA runtime."
                                    "\nUsed runtime commonName={}".format(common_name))
            if "authserver" in common_name:
                if not self.runtime_in_allowed_authentication_server_list(common_name):
                    _log.error("The runtime is not allowed to operate as an authentication server."
                                    "To be applicable, the runtime name must be listed in the"
                                    "allowed_auth_list.json white list file for the CA runtime."
                                    "\nUsed runtime commonName={}".format(common_name))
                    raise Exception("The runtime is not allowed to operate as an authentication server."
                                    "To be applicable, the runtime name must be listed in the"
                                    "allowed_auth_list.json white list file for the CA runtime."
                                    "\nUsed runtime commonName={}".format(common_name))

            #Validate challenge password, skip this if the node is a CA
            #If csmanage is used, no enrollment_password will be used, so skip verification
            if not is_ca and enrollment_password: 
                try:
                    self.validate_enrollment_password(enrollment_password, common_name)
#                    self.validate_enrollment_password(csr_path, common_name)
                except Exception as err:
                    _log.exception("Failed to validate challenge password, err={}".format(err))
                    #TODO: sent appropriate reply to requester
                    raise
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
        return csrx509

    def sign_csr(self, request, is_ca=False, enrollment_password=None):
        """
        Sign a certificate request.
        request: is the path to a Certificate Signing Request.
        is_ca: True if the CSR is for the current runtime and that runtime
                is acting as a CA

        Equivalent of:
        mkdir -p $certs
        openssl ca -in $new_certs_dir/$SIGN_REQ
                   -config $OPENSSL_CONF
                   -out $certs/runtime.pem
                   -passin file:$private_dir/ca_password
        """
        try:
            csrx509 = self.validate_csr(request, enrollment_password=enrollment_password, is_ca=is_ca)
        except:
            raise
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
            try:
                with open(signed,'ab') as rt_fd:
                    with open(self.configuration["CA_default"]["certificate"],'rb') as ca_fd:
                        rt_fd.write(ca_fd.read())
            except Exception as err:
                _log.debug("Failed to append ca cert, err={}".format(err))
                raise
            subject = csrx509.get_subject()
            dnQualifier = subject.dnQualifier
            newcert = "{}.pem".format(dnQualifier)
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
        try:
            _ca_conf = _conf.get("security", "certificate_authority")
            is_ca = _ca_conf["is_ca"]
            domain_name = _ca_conf["domain_name"]
        except:
            is_ca = False
        if is_ca==True:
            if self.security_dir:
                cert_conf_file = os.path.join(self.security_dir, domain_name, "openssl.conf")
            else:
                homefolder = get_home()
                cert_conf_file = os.path.join(homefolder,"security",domain_name,"openssl.conf")
            return cert_conf_file
        else:
            return None


    def generate_password(self, length):
        from os import urandom
        _log.debug("generate_password, length={}".format(length))
        if not isinstance(length, int) or length < 8:
            raise ValueError("Password must be longer")

        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ123456789!#%&/()=?[]{}"
        return "".join(chars[ord(c) % len(chars)] for c in urandom(length))


    def cert_enrollment_add_new_runtime(self, node_name, password=None):
        """Sets a enrollment password for the runtime with name node_name
        Args:
            node_name: name of the node in question
            password: if provided, this password is set in the database (optional), if
                    not provided, a random password is generated and returned. Mainly
                    available to enable group passwords that can be same for several
                    runtimes
        Results:
            random_password: the password set for the runtime which is required to be
                            sent along the with the CSR
        """
        _log.debug("add_new_runtime_enrollment_password for node_name={}".format(node_name))
        if not self.enrollment_challenge_db:
            self.cert_enrollment_load_db_file()
        if password:
            random_password=password
        else:
            random_password = self.generate_password(20)
        self.enrollment_challenge_db[node_name] = {'password':random_password}
        self.cert_enrollment_update_db_file()
        return random_password

    def cert_enrollment_load_db_file(self):
        import json
        try:
            with open(self.enrollment_challenge_db_path,'r') as f:
                self.enrollment_challenge_db = json.load(f)
        except Exception as exc:
            _log.exception("Failed to load Certificate Enrollment Authority password database")
            #TODO: temporarily disable password verification if no file can be opened
            #Longterm, we should raise exception instead
#            raise
            self.enrollment_challenge_db = None

    def cert_enrollment_update_db_file(self):
        import json
        try:
            with open(self.enrollment_challenge_db_path,'w') as f:
                json.dump(self.enrollment_challenge_db, f)
        except Exception as exc:
            _log.exception("Failed to create/update Certificate Enrollment Authority password database")
            raise

    def add_new_authentication_server(self, node_name):
        if not self.allowed_authentication_servers:
            self._load_allowed_authentication_server_list()
        self.allowed_authentication_servers.append(node_name)
        self._update_allowed_authentication_server_file()

    def _load_allowed_authentication_server_list(self):
        auth_list_path = os.path.join(self.configuration["CA_default"]["dir"],"allowed_auth_list.json")
        try:
            with open(auth_list_path,'r') as f:
                self.allowed_authentication_servers = f.read().splitlines()
        except Exception as exc:
            _log.debug("Failed to load allowed authentication server list, create empty list")
            self.allowed_authentication_servers = []

    def _update_allowed_authentication_server_file(self):
        auth_list_path = os.path.join(self.configuration["CA_default"]["dir"],"allowed_auth_list.json")
        try:
            with open(auth_list_path,'w') as f:
                for item in self.allowed_authentication_servers:
                    f.write("%s\n" % item)
        except Exception as exc:
            _log.exception("Failed to create/update allowed authentication runtime list")
            raise

    def runtime_in_allowed_authentication_server_list(self, node_name):
        if not self.allowed_authentication_servers:
            self._load_allowed_authentication_server_list()
        if node_name in self.allowed_authentication_servers:
            return True
        else:
            return False

    def add_new_authorization_server(self, node_name):
        if not self.allowed_authorization_servers:
            self._load_allowed_authorization_server_list()
        self.allowed_authorization_servers.append(node_name)
        self._update_allowed_authorization_server_file()

    def _load_allowed_authorization_server_list(self):
        _log.debug("_load_allowed_authorization_server_list")
        authz_list_path = os.path.join(self.configuration["CA_default"]["dir"],"allowed_authz_list.json")
        try:
            with open(authz_list_path,'r') as f:
                self.allowed_authorization_servers = f.read().splitlines()
        except Exception as exc:
            _log.debug("Failed to load allowed authorization server list, create empty list")
            self.allowed_authorization_servers = []

    def _update_allowed_authorization_server_file(self):
        authz_list_path = os.path.join(self.configuration["CA_default"]["dir"],"allowed_authz_list.json")
        try:
            with open(authz_list_path,'w') as f:
                for item in self.allowed_authorization_servers:
                    f.write("%s\n" % item)
        except Exception as exc:
            _log.exception("Failed to create/update allowed authorization runtime list")
            raise

    def runtime_in_allowed_authorization_server_list(self, node_name):
        if not self.allowed_authorization_servers:
            self._load_allowed_authorization_server_list()
        if node_name in self.allowed_authorization_servers:
            return True
        else:
            return False

