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
#                        'URI.1':'https://elxahyc5lz1:5022',
                        'DNS.2':'elxahyc5lz1',
                        'DNS.1':'runtime'},
            'ca': {'default_ca': 'RT_default'},
            'RT_default': {'dir': '~/.calvin/security/',
                           'security_dir':'~/.calvin/security/',
                            'preserve': 'no',
                            'crl_dir': '$dir/crl',
                            'RANDFILE': '$dir/private/.rand',
                            'certificate': '$dir/mine/cert.pem',
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
    def __init__(self, name, node=None, domain=None, nodeid=None, security_dir=None, enrollment_password=None, force=False, readonly=False):
        _log.debug("runtime::init name={} domain={}, nodeid={}".format(name, domain, nodeid))
        print "runtime::init name={} domain={}, nodeid={}".format(name, domain, nodeid)

        def get_own_credentials_path(security_dir=None):
            """Return the full path of the node's own certificate"""
            _log.debug("__init__::get_own_credentials_path, security_dir={}".format(security_dir))
            return os.path.join(certificate.get_runtimes_credentials_path(security_dir=security_dir),self.node_name)

        def new_opensslconf():
            """
            Create new openssl.conf configuration file.
            """
            print "new_opensslconf"
            _log.debug("__init__::new_opensslconf")
            for section in self.__class__.DEFAULT.keys():
                self.config.add_section(section)
                print "[{}]".format(section)
                for option in self.__class__.DEFAULT[section]:
                    if option == "0.organizationName":
                        value = self.domain
                    elif option == "DNS.1":
                        value = self.node_name
                    elif option == "IP.1":
                        value = self.subjectAltName
                    elif option == "dir":
                        value = self.runtime_dir
                    elif option == "security_dir":
                        value = self.security_dir
                    elif section == 'req_distinguished_name' and option == 'commonName':
                        value = self.node_name
                    elif option == 'dnQualifier':
                        value = self.node_id
                    #The pythong cryptography and the pyOpensSSL packages does not support
                    #parsing the Attributes extension in a CSR, so instead it is stored
                    #outside of the CSR
#                    elif option == 'challengePassword':
#                        value = self.enrollment_password
                    else:
                        value = self.__class__.DEFAULT[section][option]
                    print "\t{}={}".format(option, value)
                    self.config.set(section, option, value)

            with open(self.configfile, 'wb') as configfd:
                self.config.write(configfd)
                configfd.close()
            confsort.reorder(self.configfile)


        def parse_opensslconf():
            """
            Parse the openssl.conf file to find relevant paths.
            """
            print "parse_opensslconf"
            _log.debug("__init__::parse_opensslconf")
            if not self.config.read(self.configfile):
                print "could not parse config file"
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
            print "new_runtime_credentials"
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
        self.domain = self.get_domain(domain=domain)
        self.subjectAltName="127.0.1.1"
        self.enrollment_password=enrollment_password
        #Create generic runtimes folder and trust store folders
        self.security_dir=security_dir
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
            print "Runtime openssl.conf already exists, self.configuration={}".format(self.configuration)
            self.node_id =  self.configuration['req_distinguished_name']['dnQualifier'] 
            self.node_name =self.configuration['req_distinguished_name']['commonName'] 
            self.domain =   self.configuration['req_distinguished_name']['0.organizationName']
            self.runtime_dir=self.configuration['RT_default']['dir']
            self.private_key=self.configuration['RT_default']['private_key']
            self.cert=None
        else:
            _log.debug("Runtime openssl.conf does not exist, let's create it")
            new_opensslconf()
            self.configuration = parse_opensslconf()
            print "Made new configuration at " \
                  "{}".format(self.configfile)
            #Generate keys and certiticate request
            try:
                out = new_runtime_credentials(force=False, readonly=False)
                print "Created new credentials for runtime, CSR at={}".format(out)
            except:
                _log.error("creation of new runtime credentials failed")
                raise
        self.cert_name = self.get_own_cert_name()


    def update_opensslconf(self):
        """
        Update openssl.conf configuration file.
        """
        print "update_opensslconf"
        _log.debug("update_opensslconf")
        self.config=ConfigParser.SafeConfigParser()
        self.config.optionxform = str
        for section in self.__class__.DEFAULT.keys():
            self.config.add_section(section)
            print "[{}]".format(section)
            for option in self.__class__.DEFAULT[section]:
                if option == "0.organizationName":
                    value = self.domain
                elif option == "DNS.1":
                    value = self.node_name
                elif option == "IP.1":
                    value = self.subjectAltName
                elif option == "dir":
                    value = self.runtime_dir
                elif option == "security_dir":
                    value = self.security_dir
                elif section == 'req_distinguished_name' and option == 'commonName':
                    value = self.node_name
                elif option == 'dnQualifier':
                    value = self.node_id
                elif option == 'certificate':
                    value = self.configuration['RT_default']['certificate']
                else:
                    value = self.__class__.DEFAULT[section][option]
                print "\t{}={}".format(option, value)
                self.config.set(section, option, value)
        try:
            os.rename(self.configfile, self.configfile+".OLD")
        except Exception as exc:
            _log.exception("Failed to rename old config file")
            raise
        with open(self.configfile, 'wb') as configfd:
            self.config.write(configfd)
            configfd.close()
        confsort.reorder(self.configfile)


    def get_node_name(self, security_dir=None):
        if self.node_name is not None:
            return self.node_name
        else:
            raise Exception("Node name not set in runtime_credentials")

    def get_runtime_credentials(self, security_dir=None):
        _log.debug("get_runtime_credentials:: node_name={}".format(self.node_name))
        runtime_cert_chain = self.get_runtime_certificate_chain_as_string(security_dir=security_dir)
        private_key = self.get_private_key(security_dir=security_dir)
        return runtime_cert_chain + private_key


    def get_csr(self):
        """Return certificate with name cert_name from disk for runtime my_node_name"""
        # TODO: get certificate from DHT (alternative to getting from disk).
        _log.debug("get_csr: my_node_name={}".format(self.node_name))
        return os.path.join(self.runtime_dir, "{}.csr".format(self.node_name))

    def get_certificate(self, cert_name, callback=None):
        """Return certificate with name cert_name from disk for runtime my_node_name"""
        # TODO: get certificate from DHT (alternative to getting from disk).
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
        _log.debug("_get_certificate_from_storage_cb, \nkey={}\nvalue={}".format(key,value))
        if value:
            nbr = len(value)
            try:
                #Store certificate in others folder so we don't have to look it up again next time
                certificate.verify_certificate(TRUSTSTORE_TRANSPORT, value[0], security_dir=self.security_dir)
            except Exception as err:
                _log.error("Verification of the received certificate failed, err={}".format(err))
            else:
                try:
                    self.store_others_cert(value[0])
                except Exception as err:
                    _log.debug("Failed to write received certificate to others folder, err={}".format(err))
                callback(certstring=value[0])
        else:
            _log.error("The certificate can not be found")
            raise Exception("The certificate can not be found")



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
            _log.debug("get_own_cert: certstr={}".format(certstr))
            return certpath, cert, certstr
        except:
            # Certificate not available
            _log.debug("No runtime certificate can be found")
            return None, None, None

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
        certpath, cert, certstr = self.get_own_cert()
        cert_pem = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, certpath)
        cert = load_pem_x509_certificate(cert_pem, default_backend())
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
                                                   security_dir=self.configuration['req_distinguished_name']['dnQualifier'] )



    def store_own_cert(self, certstring=None, certpath=None, security_dir=None):
        """
        Store the signed runtime certificate
        in the "mine" folder
        """
        _log.debug("store_own_cert:\n    certstring={}\n    certpath={}\n    security_dir={}".format(certstring, certpath, security_dir))
        path = self.store_cert("mine", certstring=certstring, certpath=certpath)
        #Let's update openssl.conf, but this entry should probably not
        #be trusted, it is likely that someone will copy certs into the folder 
        #by other means
        self.configuration['RT_default']['certificate'] = path
        self.update_opensslconf()
        self.cert_name = self.get_own_cert_name()
        return path

    def store_others_cert(self, certstring=None, certpath=None):
        """
        Store the signed runtime certificate
        in the "others" folder
        """
        _log.debug("store_others_cert, node_name={}".format(self.node_name))
        return self.store_cert("others", certstring=certstring, certpath=certpath)

    def store_cert(self, type, certstring=None, certpath=None):
        """
        Store the signed runtime certificate
        """
        _log.debug("store_cert")
        if certpath:
            try:
                with open(certpath, 'rb') as f:
                    certstring = f.read()
            except Exception as exc:
                _log.exception("Failed to read cert at certpath={}, exc={}".format(certpath, exc))
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
        _log.debug("Store signed cert as %s" % storepath)
        try:
            with open(storepath, 'w') as cert_fd:
                    cert_fd.write(certstring)
        except (Exception), err:
            _log.exception("Storing signed cert failed")
            raise Exception("Storing signed cert failed")
        return storepath


    def get_truststore(self, type):
        """
        Returns the truststore for the type of usage as list of
        certificate strings, a list of OpenSSL objects and as a 
        OpenSSL truststore object
        """
        ca_cert_list_str, ca_cert_list_x509, truststore = certificate.get_truststore(type, security_dir=self.configuration['RT_default']['security_dir'])
        return ca_cert_list_str, ca_cert_list_x509, truststore
  

    def get_truststore_path(self, type):
        _log.debug("get_trust_store_path: type={}".format(type))
        return certificate.get_truststore_path(type, security_dir=self.configuration['RT_default']['security_dir'])

    def get_domain(self, domain=None, security_dir=None):
        """Return the node's own certificate name without file extension"""
        _log.debug("get_security_credentials_path")
        _conf_domain = _conf.get("security", "security_domain_name")
        if domain and _conf_domain and (domain != _conf_domain):
                raise Exception("supplied domain and domain in config are not the same")
        elif domain:
            return domain
        elif _conf_domain:
            return _conf_domain
        else:
            raise Exception("Domain not set anywhere")

    def remove_runtime(self):
        shutil.rmtree(self.runtime_dir,ignore_errors=True)



    def cert_enrollment_encrypt_csr(self, csr_path, cert):
        """
        csr_path: path to csr file
        cert: CA certificate as a string
        """
        import json
        import base64
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        _log.debug("cert_enrollment_encrypt_csr")
        #Load CSR from file
        #TODO: take csr as string instead of path
        try:
            with open(csr_path, 'r') as csr_fd:
                csr= csr_fd.read()
        except Exception as err:
            _log.exception("Failed to load unencrypted CSR, err={}".format(err))
            raise

#        encrypted_csr = certificate.wrap_object_with_symmetric_key(plaintext)
        plaintext = {'csr':csr, 'challenge_password':self.enrollment_password}
        encrypted_csr = certificate.encrypt_object_with_RSA(cert, json.dumps(plaintext),unencrypted_data=self.node_name)
        try:
            filename = "{}.csr".format(self.node_name)
            encrypted_filepath = csr_path + ".encrypted"
            with open(encrypted_filepath, 'w') as fd:
                json.dump(encrypted_csr, fd)
        except Exception as err:
            _log.exception("Failed to write encrypted CSR to file, err={}".format(err))
            raise
        return encrypted_csr


