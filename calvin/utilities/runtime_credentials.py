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
import socket
from calvin.utilities import confsort
import OpenSSL
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend
from calvin.utilities import calvinuuid
from calvin.utilities import calvinconfig
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.utils import get_home
from calvin.utilities import certificate
from calvin.utilities.calvin_callback import CalvinCB

_log = get_logger(__name__)
_conf = calvinconfig.get()
BEGIN_CRT_LINE = "-----BEGIN CERTIFICATE-----"
BEGIN_PRIV_KEY_LINE = "-----BEGIN CERTIFICATE-----"
BEGIN_ENCRYPTED_PRIVATE_KEY = "-----BEGIN ENCRYPTED PRIVATE KEY-----"
BEGIN_RSA_PRIVATE_KEY = "-----BEGIN RSA PRIVATE KEY-----"
BEGIN_EC_PARAMETERS = "-----BEGIN EC PARAMETERS-----"
BEGIN_EC_PRIVATE_KEY = "-----BEGIN EC PRIVATE KEY-----"
BEGIN_CSR_LINE = "-----BEGIN CERTIFICATE REQUEST-----"

TYPE_ECC = 408  # Internal type name for ECC keys in version3 of PKCS#10.

TRUSTSTORE_TRANSPORT ="truststore_for_transport"
TRUSTSTORE_SIGN ="truststore_for_signing"


class RuntimeCredentials():
    """
    Create new runtime certificate.
    Return name of certificate signing request file.

    Parameters:
    -name: name of the runtime
    -domain: the name of the CA that we intend to sign the runtimes certificate
    -nodeid: optional parameter used for dnQualified of cert if supplied
    -security_dir: optional parameter if another credentials location that
        the default value (~/.calvin/security/runtimes/) is required
    Equivalent of:
    mkdir -p $new_certs_dir
    openssl req -config $OPENSSL_CONF -new \
                -newkey rsa:2048 -nodes \
                -out $new_certs_dir/runtime.csr \
                -keyout $private_dir/runtime.key
    """
    DEFAULT = {
           'req': {'distinguished_name': 'req_distinguished_name',
#                   'attributes':'req_attributes',
                   'req_extensions': 'v3_req',
                   'prompt': 'no',
                   'default_keyfile': 'privkey.pem',
                   'default_bits': '2048'},
            'v3_req': {'subjectAltName': '@alt_names',
                        'basicConstraints':'CA:false',
                        'keyUsage':'nonRepudiation, digitalSignature, keyEncipherment'},
            'req_distinguished_name': {'0.organizationName': 'domain',
                                        'commonName': 'runtime',
                                        'dnQualifier': 'dnQualifier'},
#            'req_attributes':{'challengePassword':'password'},
            'alt_names':{'IP.1':'x',
                         'DNS.1':'x',
                         'DNS.2':'x',
                         'DNS.3':'x',
                         'DNS.4':'x'},
            'ca': {'default_ca': 'RT_default'},
            'RT_default': {'dir': '~/.calvin/security/',
                           'security_dir':'~/.calvin/security/',
                            'preserve': 'no',
                            'crl_dir': '$dir/crl',
                            'RANDFILE': '$dir/private/.rand',
#                            'certificate': '$dir/mine/cert.pem',
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
                            'default_crl_days': '30',
                            'name_opt': 'ca_default',
                            'crl': '$dir/crl.pem',
                            'default_md': 'sha256'},
            'v3_ca': {'basicConstraints':'CA:false',
                        'subjectKeyIdentifier': 'hash',
                        'authorityKeyIdentifier':
                        'keyid:always,issuer:always',
                        'subjectAltNames':'alt_names'},
            'usr_cert': {'subjectKeyIdentifier': 'hash',
                            'authorityKeyIdentifier': 'keyid,issuer',
                            'basicConstraints': 'CA:false'},
            'policy_any': {'countryName': 'optional',
                            'organizationalUnitName': 'optional',
                            'organizationName': 'supplied',  # match
                            'emailAddress': 'optional',
                            'commonName': 'supplied',
                            'dnQualifier': 'supplied',
                            'stateOrProvinceName': 'optional'}}
    def __init__(self, name, node=None, domain=None, hostnames=None, nodeid=None, security_dir=None, enrollment_password=None, force=False, readonly=False):
        _log.debug("runtime::init name={} domain={}, nodeid={}".format(name, domain, nodeid))
#        print "runtime::init name={} domain={}, nodeid={} enrollment_password={} security_dir={}".format(name, domain, nodeid, enrollment_password, security_dir)

        def get_own_credentials_path(security_dir=None):
            """Return the full path of the node's own certificate"""
            _log.debug("__init__::get_own_credentials_path, security_dir={}".format(security_dir))
            return os.path.join(certificate.get_runtimes_credentials_path(security_dir=security_dir),self.node_name)

        def new_opensslconf():
            """
            Create new openssl.conf configuration file.
            """
#            print "new_opensslconf"
            _log.debug("__init__::new_opensslconf")
            for section in self.__class__.DEFAULT.keys():
                self.config.add_section(section)
    #            print "[{}]".format(section)
                hostname = socket.gethostname()
                for option in self.__class__.DEFAULT[section]:
                    if option == "0.organizationName":
                        value = self.domain
                    #TODO: use dynamic number of DNS entries instead of hardcoding the number
                    elif option == "DNS.1":
                        value = self.node_name
                    elif (option == "DNS.2") and len(self.hostnames)>0:
                        value = self.hostnames[0]
                    elif (option == "DNS.3") and len(self.hostnames)>1:
                        value = self.hostnames[1]
                    elif (option == "DNS.4") and len(self.hostnames)>2:
                        value = self.hostnames[2]
                    elif option == "IP.1":
                        value = self.ip
                    elif option == "dir":
                        value = self.runtime_dir
                    elif section == 'req_distinguished_name' and option == 'commonName':
                        value = self.node_name
                    elif option == 'dnQualifier':
                        value = self.node_id
                    #The python cryptography and the pyOpensSSL packages does not support
                    #parsing the Attributes extension in a CSR, so instead it is stored
                    #outside of the CSR
    #                    elif option == 'challengePassword':
    #                        value = self.enrollment_password
                    else:
                        value = self.__class__.DEFAULT[section][option]
    #                    print "\t{}={}".format(option, value)
                    self.config.set(section, option, value)
            with open(self.configfile, 'wb') as configfd:
                self.config.write(configfd)
                configfd.close()
            confsort.reorder(self.configfile)


        def parse_opensslconf():
            """
            Parse the openssl.conf file to find relevant paths.
            """
#            print "parse_opensslconf"
            _log.debug("__init__::parse_opensslconf")
            if not self.config.read(self.configfile):
#                print "could not parse config file"
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

        def new_runtime_credentials(force=False, readonly=False):
            """
            Generate keys, files and certificate
            for the new runtime
            """
            _log.debug("new_runtime_credentials")
            #Create keys and certificate request
            private_key = os.path.join(self.runtime_dir, "private", "private.key")
            private = os.path.dirname(private_key)
            _log.debug("new_runtime: %s" % self.runtime_dir)
            out = os.path.join(self.runtime_dir, "{}.csr".format(self.node_name))
            _log.debug("out dir: %s"% out)
            # Create ECC-based certificate
            log = subprocess.Popen(["openssl", "ecparam", "-genkey",
                                    "-name", "prime256v1",
                                    "-out", private_key],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
            stdout, stderr = log.communicate()
            if log.returncode != 0:
                raise IOError(stderr)

            log = subprocess.Popen(["openssl", "req", "-new",
                                    "-config",self.configfile,
                              #      "-subj", subject,
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

        def get_domain(domain=None, security_dir=None):
            """Return the node's own certificate name without file extension"""
            _log.debug("get_domain")
            try:
                _domain = _conf.get("security", "domain_name")
                if _domain:
                    return _domain
            except Exception as err:
                _log.error("get_domain: error while trying to read domain from Calvin config, err={}".format(err))
            _log.debug("get_domain: Domain not found in Calvin config, let's use supplied domain")
            if domain:
                return domain
            else:
                raise Exception("Domain not set anywhere")



        self.node=node
        self.node_name=name
        self.node_id=nodeid
        self.runtime_dir=None
        self.private_key=None
        self.cert=None
        self.cert_name=None
        self.configfile = None
        self.config=ConfigParser.SafeConfigParser()
        self.configuration=None
        self.config.optionxform = str
        os.umask(0077)
        self.domain = None
        self.ip="127.0.1.1"
        self.hostnames = hostnames if hostnames!=None else [socket.gethostname(),  socket.getfqdn(socket.gethostname())]
        self.enrollment_password=enrollment_password
        #Create generic runtimes folder and trust store folders
        self.security_dir=security_dir
        self.truststore_for_transport=None
        runtimes_dir = certificate.get_runtimes_credentials_path(security_dir=security_dir)
        if not os.path.isdir(runtimes_dir):
            try:
                os.makedirs(runtimes_dir)
            except OSError:
                pass
        trust_store_transport_dir = os.path.join(runtimes_dir,TRUSTSTORE_TRANSPORT)
        if not os.path.isdir(trust_store_transport_dir):
            try:
                os.makedirs(trust_store_transport_dir)
            except OSError:
                pass
        trust_store_sign_dir = os.path.join(runtimes_dir,TRUSTSTORE_SIGN)
        if not os.path.isdir(trust_store_sign_dir):
            try:
                os.makedirs(trust_store_sign_dir)
            except OSError:
                pass

        #Create folders for runtime
        self.runtime_dir = get_own_credentials_path(security_dir=security_dir)
        if not os.path.isdir(self.runtime_dir):
            try:
                os.makedirs(self.runtime_dir, 0755)
            except OSError:
                pass
        if not os.path.isdir(os.path.join(self.runtime_dir, "mine")):
            try:
                os.makedirs(os.path.join(self.runtime_dir, "mine"), 0755)
            except OSError:
                pass
        if not os.path.isdir(os.path.join(self.runtime_dir, "others")):
            try:
                os.makedirs(os.path.join(self.runtime_dir, "others"))
            except OSError:
                pass
        if not os.path.isdir(os.path.join(self.runtime_dir, "private")):
            try:
                os.makedirs(os.path.join(self.runtime_dir, "private"), 0700)
            except OSError:
                pass

        #Create OpenSSL config file
        self.configfile = os.path.join(self.runtime_dir, "openssl.conf")
        exist = os.path.isfile(self.configfile)
        if not exist and readonly:
            raise Exception("Configuration file does not exist, create runtime openssl.conf first")
        if exist and not force:
            self.configuration = parse_opensslconf()
            _log.debug("Runtime openssl.conf already exists, self.configuration={}".format(self.configuration))
#            print "Runtime openssl.conf already exists, self.configuration={}".format(self.configuration)
            self.node_id =  self.configuration['req_distinguished_name']['dnQualifier'] 
            self.node_name =self.configuration['req_distinguished_name']['commonName'] 
            self.domain =   self.configuration['req_distinguished_name']['0.organizationName']
            self.runtime_dir=self.configuration['RT_default']['dir']
            self.private_key=self.configuration['RT_default']['private_key']
            self.cert=None
        else:
            _log.debug("Runtime openssl.conf does not exist, let's create it")
            self.domain = get_domain(domain=domain)
            new_opensslconf()
            self.configuration = parse_opensslconf()
#            print "Made new configuration at " \
#                  "{}".format(self.configfile)
            #Generate keys and certiticate request
            try:
                out = new_runtime_credentials(force=False, readonly=False)
#                print "Created new credentials for runtime, CSR at={}".format(out)
            except:
                _log.error("creation of new runtime credentials failed")
                raise
        self.cert_name = self.get_own_cert_name()
        if enrollment_password:
            self.cert_enrollment_encrypt_csr()


    def get_node_name(self, security_dir=None):
        if self.node_name is not None:
            return self.node_name
        else:
            raise Exception("Node name not set in runtime_credentials")

    def get_runtime_credentials(self, security_dir=None):
        _log.debug("get_runtime_credentials:: node_name={}".format(self.node_name))
        runtime_cert_chain = self.get_runtime_certificate_chain_as_string(security_dir=security_dir)
        private_key = self.get_private_key()
        return runtime_cert_chain + private_key

    def get_encrypted_csr_path(self):
        """Return the path to the csr for the runtime"""
        _log.debug("get_encrypted_csr_path: my_node_name={}".format(self.node_name))
        return os.path.join(self.runtime_dir, "{}.csr.encrypted".format(self.node_name))

    def get_csr_path(self):
        """Return the path to the csr for the runtime"""
        _log.debug("get_csr_path: my_node_name={}".format(self.node_name))
        return os.path.join(self.runtime_dir, "{}.csr".format(self.node_name))

    def get_certificate(self, cert_name, callback=None):
        """Return certificate with name cert_name from disk or storage"""
        _log.debug("get_certificate:\n\tmy_node_name={}\n\tcert_name={}\n\tcallback={}".format(self.node_name, cert_name, callback))
        try:
            _log.debug("Look for certificate in others folder, cert_name={}".format(cert_name))
            # Check if the certificate is in the 'others' folder for runtime my_node_name.
            files = os.listdir(os.path.join(self.runtime_dir, "others"))
            matching = [s for s in files if cert_name in s]
            certpath = os.path.join(self.runtime_dir, "others", matching[0])
            certificate.verify_certificate_from_path(TRUSTSTORE_TRANSPORT, certpath, security_dir=self.security_dir)
            with open(certpath, 'rb') as fd:
                certstr=fd.read()
            if callback:
                callback(certstring=certstr)
            else:
                return certstr
        except Exception as err:
            _log.debug("Certificate {} is not in {{others}} folder, continue looking in {{mine}} folder, err={}".format(cert_name, err))
            try:
                # Check if cert_name is the runtime's own certificate.
                files = os.listdir(os.path.join(self.runtime_dir, "mine"))
                matching = [s for s in files if cert_name in s]
                certpath = os.path.join(self.runtime_dir, "mine", matching[0])
                certificate.verify_certificate_from_path(TRUSTSTORE_TRANSPORT, certpath, security_dir=self.security_dir)
                with open(certpath, 'rb') as fd:
                    certstr=fd.read()
                if callback:
                    callback(certstring=certstr)
                else:
                    return certstr
            except Exception as err:
                _log.debug("Certificate {} is not in {{others, mine}} folder, continue looking in storage, err={}".format(cert_name, err))
                try:
                    self.node.storage.get_index(['certificate',cert_name],
                                                CalvinCB(self._get_certificate_from_storage_cb,
                                                        callback=callback))
                except Exception as err:
                    _log.debug("Certificate could not be found in storage, err={}".format(err))
                    raise

    def _get_certificate_from_storage_cb(self, key, value, callback):
        _log.debug("_get_certificate_from_storage_cb, \nkey={}\nvalue={}\n\tcallback={}".format(key, value, callback))
        if value:
            nbr = len(value)
            try:
                #Store certificate in others folder so we don't have to look it up again next time
                self.verify_certificate(value[0], TRUSTSTORE_TRANSPORT)
            except Exception as err:
                _log.error("Verification of the received certificate failed, err={}".format(err))
            else:
                try:
                    self.store_others_cert(certstring=value[0])
                except Exception as err:
                    _log.debug("Failed to write received certificate to others folder, err={}".format(err))
                callback(certstring=value[0])
        else:
            _log.error("The certificate can not be found")
            raise Exception("The certificate can not be found")

    def verify_certificate(self, cert_str, type):
        _log.debug("verify_certificate:\n\tcert_str={}\n\ttype={}".format(cert_str, type))
        try:
            cert = certificate.verify_certificate(type, cert_str, security_dir=self.security_dir)
        except Exception as err:
            _log.error("Failed to verify certificate, err={}".format(err))
        return cert

    def get_private_key(self, security_dir=None):
        """Return the node's private key"""
        _log.debug("get_private_key: node_name={}".format(self.node_name))
        with open(os.path.join(self.runtime_dir, "private", "private.key"), 'rb') as f:
            return f.read()


    def get_runtime_certificate_chain_as_list(self, security_dir=None):
        """
        Return certificate chain as a list of strings and as a list 
        of OpenSSL certificate objects
        """
        # TODO: make for flexible to support intermediate certificates
        _log.debug("get_runtime_certificate_chain_as_list: my_node_name={}".format(self.node_name))
        cert_chain_list_of_strings = []
        cert_chain_list_of_x509 = []
        try:
            cert_chain_str = get_runtime_certificate_chain_as_string(security_dir=security_dir)
            cert_part = cert_chain_str.split(BEGIN_CRT_LINE)
            cert_chain_list_of_strings = []
            cert_chain_list_of_strings.append("{}{}".format(BEGIN_CRT_LINE, cert_part[1]))
            cert_chain_list_of_strings.append("{}{}".format(BEGIN_CRT_LINE, cert_part[2]))
            cert_chain_list_of_x509.append(OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                  cert_chain_list_of_strings[0]))
            cert_chain_list_of_x509.append(OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                  cert_chain_list_of_strings[1]))
            return cert_chain_list_of_strings, cert_chain_list_of_x509
        except Exception:
            _log.debug("Failed to get the runtimes certificate chain")
            raise

    def get_runtime_certificate_chain_as_string(self, security_dir=None):
        """
        Return the full certificate chain as a string
        """
        # TODO: get certificate from DHT (alternative to getting from disk).
        _log.debug("get_runtime_certificate_chain_as_string: my_node_name={}".format(self.node_name))
        try:
            # Check if cert_name is the runtime's own certificate.
            files = os.listdir(os.path.join(self.runtime_dir, "mine"))
            with open(os.path.join(self.runtime_dir, "mine", files[0]), 'rb') as f:
                cert_str=f.read()
                return cert_str
        except Exception as err:
            _log.debug("Failed to get the runtimes certificate chain, err={}".format(err))
            raise Exception("Failed to get the runtimes certificate chain")

    def get_own_cert_fingerprint(self):
        _log.debug("get_own_cert_fingerprint")
        certpath, cert, certstr = self.get_own_cert()
        return cert.digest("sha256")

    def get_own_cert(self, security_dir=None):
        """
        Return the signed runtime certificate
        in the "mine" folder. It returns just the certificate,
        not the entire chain even if the whole chain is in
        the same pem file.
        """
        _log.debug("get_own_cert: node_name={}".format(self.node_name))
        cert_dir = os.path.join(self.runtime_dir, "mine")
        try:
            filename = os.listdir(cert_dir)
            certpath = os.path.join(cert_dir, filename[0]) 
            st_cert = open(certpath, 'rt').read()
            cert_part = st_cert.split(BEGIN_CRT_LINE)
            certstr = "{}{}".format(BEGIN_CRT_LINE, cert_part[1])
            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                  certstr)
            _log.debug("get_own_cert: certpath={}, cert={}, certstr={}".format(certpath, cert, certstr))
            return certpath, cert, certstr
        except:
            # Certificate not available
            _log.debug("No runtime certificate can be found")
            return None, None, None

    def get_own_cert_path(self):
        """
        Return the paht to the signed runtime certificate
        in the "mine" folder.
        """
        _log.debug("get_own_cert_path: node_name={}".format(self.node_name))
        cert_dir = os.path.join(self.runtime_dir, "mine")
        try:
            filename = os.listdir(cert_dir)
            return os.path.join(cert_dir, filename[0])
        except Exception as err:
            # Certificate not available
            _log.debug("No runtime certificate path can be found, err={}".format(err))
            return None

    def get_own_cert_chain_as_string(self):
        """
        Return the signed runtime certificate
        in the "mine" folder as a string. The entire
        chain is returned as one string
        """
        _log.debug("get_own_cert_chain_as_string: node_name={}".format(self.node_name))
        cert_path = self.get_own_cert_path()
        try:
            cert_chain_str = open(cert_path, 'rt').read()
            return cert_chain_str
        except Exception as err:
            # Certificate not available
            _log.debug("No runtime certificate string can be found, err={}".format(err))
            return None

    def get_own_cert_as_string(self):
        """
        Return the signed runtime certificate
        in the "mine" folder as a string. The entire
        chain is returned as one string
        """
        _log.debug("get_own_cert_as_string: node_name={}".format(self.node_name))
        cert_chain_str = self.get_own_cert_chain_as_string()
        try:
            cert_part = cert_chain_str.split(BEGIN_CRT_LINE)
            certstr = "{}{}".format(BEGIN_CRT_LINE, cert_part[1])
            return certstr
        except Exception as err:
            # Certificate not available
            _log.debug("No runtime certificate chain can be found, err={}".format(err))
            return None

    def get_own_cert_as_openssl_object(self):
        """
        Return the signed runtime certificate
        in the "mine" folder. It returns just the certificate,
        not the entire chain even if the whole chain is in
        the same pem file.
        """
        _log.debug("get_own_cert_as_openssl_object: node_name={}".format(self.node_name))
        certstr = self.get_own_cert_as_string()
        try:
            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                  certstr)
            return cert
        except Exception as err:
            # Certificate not available
            _log.debug("No runtime certificate OpenSSL object can be found, err={}".format(err))
            return None

    def get_own_cert_name(self):
        """Return the node's own certificate name without file extension"""
        _log.debug("get_own_cert_name: node_name={}".format(self.node_name))
        certs = os.listdir(os.path.join(self.runtime_dir, "mine"))
        if certs:
            return os.path.splitext(certs[0])[0]
        else:
            return None

    def get_public_key(self):
        """Return the public key from certificate"""
        _log.debug("get_public_key")
        certpath, cert, certstr = self.get_own_cert()
#        try:
#            cert_pem = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
#        except Exception as err:
#            _log.error("Failed to dump certificate, err={}".format(err))
#            raise
        try:
            cert = load_pem_x509_certificate(certstr, default_backend())
        except Exception as err:
            _log.error("Failed to load X509 certificate from PEM, err={}".format(err))
            raise
        return cert.public_key()
        # The following line can replace the two lines above in pyOpenSSL version 16.0.0 (unreleased):
        # return OpenSSL.crypto.dump_publickey(OpenSSL.crypto.FILETYPE_PEM, certificate.get_pubkey())


    ###########################################################
    # Linking a runtime name on a host to a persistent node-id
    # This linkage is included in CSR and signed by CA
    ###########################################################

    def obtain_cert_node_info(self, security_dir=None):
        """ Obtain node id based on name and domain from config
            Return dict with domain, node name and node id
        """
        _log.debug("obtain_cert_node_info: node_name={}".format(self.node_name))
        if self.domain is None or self.node_name is None:
            # No security or name specified just use standard node UUID
            _log.debug("OBTAINING no security domain={}, name={}".format(self.domain, self.node_name))
            return {'domain': None, 'name': self.node_name, 'id': calvinuuid.uuid("NODE")}

        # Does existing signed runtime certificate exist, return info
        try:
            filenames = os.listdir(os.path.join(self.runtime_dir, "mine"))
            content = open(os.path.join(self.runtime_dir, "mine", filenames[0]), 'rt').read()
            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                  content)
            subject = cert.get_subject()
            if subject.commonName != self.node_name or subject.organizationName != domain:
                raise Exception("names of cert incorrect")
            _log.debug("OBTAINING existing security domain={}, name={}, id={}".format(self.domain, self.node_name, subject.dnQualifier))
            return {'domain': self.domain, 'name': self.node_name, 'id': subject.dnQualifier}
        except:
            pass
            #_log.exception("OBTAINING fail existing security domain={}, name={}".format(domain, name))
        # No valid signed cert available, create new node id and let user create certificate later
        nodeid = calvinuuid.uuid("NODE")
        return {'domain': self.domain, 'name': self.node_name, 'id': nodeid}




    def store_trusted_root_cert(self, cert_file, trusted_root):
        """
        Copy the certificate giving it the name that can be stored in
        trustStore for verification of signatures.
        file is the out file

        """
        return certificate.store_trusted_root_cert(cert_file, trusted_root,
                                                   security_dir=self.security_dir)



    def store_own_cert(self, certstring=None, certpath=None, security_dir=None):
        """
        Store the signed runtime certificate
        in the "mine" folder
        """
        _log.debug("store_own_cert:\n\tcertstring={}\n\tcertpath={}".format(certstring, certpath))
        path = self.store_cert("mine", certstring=certstring, certpath=certpath)
        print "Hakan path={}".format(path)
        #Let's update openssl.conf, but this entry should probably not
        #be trusted, it is likely that someone will copy certs into the folder 
        #by other means
#        self.configuration['RT_default']['certificate'] = path
#        self.update_opensslconf()
        self.cert_name = self.get_own_cert_name()
        return path

    def others_cert_stored(self, certstring):
        """
        Check if the certificate is already store in the other folder
        """
        _log.debug("others_cert_stored")
        dnQualifier = certificate.cert_DN_Qualifier(certstring)
        _log.debug("others_cert_stored")
        filename = "{}.pem".format(dnQualifier)
        _log.debug("others_cert_stored")
        path = os.path.join(self.runtime_dir, "others", filename)
        if os.path.isfile(path):
            return True
        else:
            return False

    def store_others_cert(self, certstring=None, certpath=None, force=False):
        """
        Store the signed runtime certificate
        in the "others" folder
        """
        _log.debug("store_others_cert")
        return self.store_cert("others", certstring=certstring, certpath=certpath, force=force)

    def store_cert(self, type, certstring=None, certpath=None, force=False):
        """
        Store the signed runtime certificate
        return values.
            path: path to the stored certificate
        """
        _log.debug("store_cert:\n\ttype={}\n\tcertstring={}\n\tcertpath={}\n\tforce=={}".format(type, certstring, certpath, force))
        if certpath:
            try:
                with open(certpath, 'rb') as f:
                    certstring = f.read()
            except Exception as exc:
                _log.exception("cert path supplied, but failed to read cert at certpath={}, exc={}".format(certpath, exc))
                raise
        elif not certstring:
            raise Exception("Neither certstring nor certpath supplied")
        commonName = certificate.cert_CN(certstring)
        dnQualifier = certificate.cert_DN_Qualifier(certstring)
        filename = "{}.pem".format(dnQualifier)
        if type not in ["mine","others"]:
            _log.error("type not supported")
            raise Exception("type not supported")
        storepath = os.path.join(self.runtime_dir, type, filename)
        _log.debug("Path to store signed cert as %s" % storepath)
        if force or not os.path.isfile(storepath):
            _log.debug("Store signed cert as %s" % storepath)
            try:
                with open(storepath, 'w') as cert_fd:
                    cert_fd.write(certstring)
            except (Exception), err:
                _log.exception("Storing signed cert failed")
                raise Exception("Storing signed cert failed")
        else:
            _log.debug("Cert already stored")
        return storepath

    def get_truststore(self, type):
        """
        Returns the truststore for the type of usage as list of
        certificate strings, a list of OpenSSL objects and as a 
        OpenSSL truststore object
        """
        ca_cert_list_str, ca_cert_list_x509, truststore = certificate.get_truststore(type, 
                                                    security_dir=self.security_dir)
        return ca_cert_list_str, ca_cert_list_x509, truststore

    def get_truststore_path(self, type):
        _log.debug("get_trust_store_path: type={}".format(type))
        return certificate.get_truststore_path(type, security_dir=self.security_dir)


    def remove_runtime(self):
        shutil.rmtree(self.runtime_dir,ignore_errors=True)



    def cert_enrollment_encrypt_csr(self, csr_path=None, ca_cert_str=None):
        """
        """
        import json
        import base64
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        _log.debug("cert_enrollment_encrypt_csr:")

        #TODO: support multiple CA certs
        try:
            ca_cert = self.get_truststore(type=certificate.TRUSTSTORE_TRANSPORT)[0][0]
            if not ca_cert:
                _log.error("Truststore empty, please configure runtime with  a trusted CA cert")
                raise Exception("Truststore empty, please configure runtime with  a trusted CA cert")
        except Exception as err:
            _log.error("Failed to load CA cert from truststore, err={}".format(err))
            raise
        try:
            csr_path = self.get_csr_path()
            with open(csr_path, 'r') as csr_fd:
                csr= csr_fd.read()
        except Exception as err:
            _log.exception("Failed to load unencrypted CSR, err={}".format(err))
            raise

        plaintext = {'csr':csr, 'challenge_password':self.enrollment_password}
        encrypted_csr = certificate.encrypt_object_with_RSA(ca_cert, json.dumps(plaintext),unencrypted_data=self.node_name)
        try:
            filename = "{}.csr".format(self.node_name)
            encrypted_filepath = csr_path + ".encrypted"
            with open(encrypted_filepath, 'w') as fd:
                json.dump(encrypted_csr, fd)
        except Exception as err:
            _log.error("Failed to write encrypted CSR to file, err={}".format(err))
            raise
        return encrypted_csr

    def sign_data(self, data):
        _log.debug("sign_data, data={}".format(data))
        from OpenSSL import crypto
        private_key_str = self.get_private_key()
        try:
            private_key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM,
                                                        private_key_str, '')
            signature = OpenSSL.crypto.sign(private_key,
                                            data,
                                            "sha256")
        except Exception as err:
            _log.error("Failed to sign data, err={}".format(err))
            raise
        try:
            certstr =  self.get_own_cert_as_string()
            cert =  self.get_own_cert_as_openssl_object()
            OpenSSL.crypto.verify(cert,
                                 signature,
                                 data,
                                 "sha256")
        except Exception as err:
            _log.error("Failed to verify signature, err={}".format(err))
            raise
        return signature

    def verify_signed_data_from_certname(self,  signature, data, type, certname):
        from OpenSSL import crypto
        _log.debug("verify_signed_data_from_certname:\n\tsigned_data={}\n\ttype={}\n\tcertname={}".format(signed_data, type, certname))
        if type not in ["mine","others"]:
            _log.error("type not supported")
            raise Exception("type not supported")
        try:
            signature = signed_data["signature"]
            data = signed_data["data"]
        except Exception as err:
            _log.error("Either data or the signature is missing from signed data, err={}".format(err))
            raise
        #Try to find certificate locally or in storage
        self.get_certificate(cert_name=certname, 
                             callback=CalvinCB(verify_signed_data_from_certstring,
                                              signature,
                                              data,
                                              type))

    def verify_signed_data_from_certstring(self, certstring, signature, data, type, callback=None):
        from OpenSSL import crypto
        _log.debug("verify_signed_data_from_certstring:\n\tcertstring={}\n\tdata={}\n\tsignature={}\n\ttype={}".format(certstring, data, signature, type))
        try:
            cert_OpenSSL = self.verify_certificate(certstring, type)
        except Exception as err:
            _log.error("Certificate verification failed, err={}".format(err))
            raise
        try:
            OpenSSL.crypto.verify(cert_OpenSSL,
                                 signature,
                                 data,
                                 "sha256")
        except Exception as err:
            _log.error("Signature verification failed, err={}\n\tcertstring={}\n\tdata={}\n\tsignature={}".format(err,certstring, data, signature))
            raise
        _log.debug("verify_signed_data_from_certstring: signature is ok")
        try:
            path = self.store_others_cert(certstring=certstring)
        except Exception as err:
            _log.error("Failed to store certificate, err={}".format(err))
            raise
        if callback:
            callback()


