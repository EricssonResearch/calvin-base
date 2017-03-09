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

def id_from_cert_string(cert_str):
    fingerprint = fingerprint_from_cert_string(cert_str)
    return fingerprint.replace(":","")[-40:]
    



def fingerprint_from_cert_string(cert_str):
    """
    Return the sha256 fingerprint of a certificate `filename`.
    Can only be run on trusted/signed certificates.
    Equivalent to:
    openssl x509 -sha256 -in ./runtime.csr -noout -fingerprint
    """
    cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                      cert_str)
    fingerprint = cert.digest("sha256")
#    id = fingerprint.replace(":","")[-40:]

    return fingerprint

def get_cert_data(certstring=None, certpath=None):
    """Return the hash of the certificate subject"""
    if certpath:
        try:
            with open(certpath, 'r') as cert_fd:
                certdata = cert_fd.read()
        except Exception as err:
            _log.error("Error opening certificate file, err= {}".format(err))
            raise IOError(err)
    elif certstring:
        certdata=certstring
    cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certdata)
    return cert

def cert_hash(certstring=None, certpath=None):
    """Return the hash of the certificate subject"""
    cert = get_cert_data(certstring=certstring, certpath=certpath)
    return format(cert.subject_name_hash(),'x')

def cert_O(certstring=None, certpath=None):
    """Return the organization of the certificate subject"""
    cert = get_cert_data(certstring=certstring, certpath=certpath)
    return cert.get_subject().O

def get_runtime_CN(node_name, security_dir=None):
    certlist_str, certlist_x509, = get_runtime_certificate_chain_as_list(node_name, security_dir=security_dir)
    return cert_CN(certstring=certlist_str[0])
    
def cert_CN(certstring=None, certpath=None):
    """Return the common name of the certificate subject"""
    cert = get_cert_data(certstring=certstring, certpath=certpath)
    return cert.get_subject().CN

def get_runtime_DN_Qualifier(node_name, security_dir=None):
    certlist_str, certlist_x509, = get_runtime_certificate_chain_as_list(node_name, security_dir=security_dir)
    return cert_DN_Qualifier(certstring=certlist_str[0])
    
def cert_DN_Qualifier(certstring=None, certpath=None):
    """Return the common name of the certificate subject"""
    cert = get_cert_data(certstring=certstring, certpath=certpath)
    return cert.get_subject().dnQualifier

def new_runtime(name, domain, nodeid=None, security_dir=None):
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
    _log.debug("new_runtime: name={} domain={}".format(name, domain))
    runtimes_dir = get_runtimes_credentials_path(security_dir=security_dir)
    print runtimes_dir
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
 
    runtime_dir = get_own_credentials_path(name, security_dir=security_dir)
    os.umask(0077)
    try:
        os.makedirs(os.path.join(runtime_dir, "mine"), 0755)
    except OSError:
        pass
    try:
        os.makedirs(os.path.join(runtime_dir, "others"))
    except OSError:
        pass
    try:
        os.makedirs(os.path.join(runtime_dir, "private"), 0700)
    except OSError:
        pass

    private_key = os.path.join(runtime_dir, "private", "private.key")
    private = os.path.dirname(private_key)
    _log.debug("new_runtime: %s" % runtime_dir)
    out = os.path.join(runtime_dir, "{}.csr".format(name))
    _log.debug("out dir: %s"% out)
    organization = domain
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




def verify_certificate_from_path(type, certpath, domain=None, security_dir=None):
    try:
        with open(certpath, 'rb') as fd:
            certstring = fd.read()
    except Exception as err:
        _log.error("Failed to open certificate, err={}".format(err))
    return verify_certificate(type, certstring, domain, security_dir)

def verify_certificate(type, certstring, domain=None, security_dir=None):
    """Verify certificate using the CA certificate"""
    _log.debug("verify_certificate: \n\ttype={}\n\tcertstring={}\n\tsecurity_dir={}".format(type, certstring, security_dir))
    #TODO: support of multiple ca-certs
    try:
        ca_cert_list_str, ca_cert_list_x509, trusted_certs = get_truststore(type, security_dir=security_dir)
    except Exception as e:
        _log.error("Failed to load trusted certificates: %s" % e)
        raise
    try:
        certx509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certstring)
    except Exception as e:
        _log.error("Failed to load certstring: certstring={}, error={}".format(certstring, e))
        raise Exception("Failed to load certstring")
    #Do sanity checks of cert
    subject = certx509.get_subject()
    serial = certx509.get_serial_number()
    if certx509.has_expired():
        _log.error("Certificate has expired")
        raise CertificateInvalid("Certificate has expired.")
    if serial < 0:
        _log.error("Serial number was negative")
        raise CertificateDeniedMalformed("Serial number was negative.")
    try:
        verify_certstr_with_policy(certstring)
        certx509.get_signature_algorithm()  # TODO: Check sig alg strength
    except ValueError as err:
        _log.error("Unknown signature algorithm, err={}".format(err))
        raise CertificateDeniedMalformed("Unknown signature algorithm.")
#    if domain:
#        if subject.organization is not domain:
#            raise CertificateDeniedConfiguration("Certificate organization"
#                                                 " is not domain.")
    try:
        store_ctx = OpenSSL.crypto.X509StoreContext(trusted_certs, certx509)
    except Exception as e:
        _log.error("Failed to create X509StoreContext: %s" % e)
    # Verify the certificate. Raises X509StoreContextError on error.
    try:
        store_ctx.verify_certificate()
    except Exception as e:
        _log.error("Failed to verify certificate: %s" % e)
    return certx509

def verify_cert_with_policy(certpath):
    """
    Confirm that a `cacert` is allowed in security configuration policy.
    Comparing with NIST:
    http://csrc.nist.gov/publications/PubsFIPS.html#fips186-3
    """
    certx509 = load_cert(certpath)
    verify_certdata_with_policy(certx509)

def verify_certstr_with_policy(certstring):
    """
    Confirm that a `cacert` is allowed in security configuration policy.
    Comparing with NIST:
    http://csrc.nist.gov/publications/PubsFIPS.html#fips186-3
    """
    certx509 = load_certdata(certstring)
    verify_certdata_with_policy(certx509)
    return certx509

def verify_certdata_with_policy(certx509):
    pubkey = certx509.get_pubkey()
    if pubkey.type() is TYPE_ECC and pubkey.bits() < 256:
        raise CertificateDeniedConfiguration("Too small ECC key in cert.")
    if pubkey.type() is OpenSSL.crypto.TYPE_RSA and pubkey.bits < 2048:
        raise CertificateDeniedConfiguration("Too small RSA key in cert.")
    if pubkey.type() is OpenSSL.crypto.TYPE_DSA and pubkey.bits < 2048:
        raise CertificateDeniedConfiguration("Too small DSA key in cert.")

def get_runtime_credentials(my_node_name, security_dir=None):
    _log.debug("get_runtime_credentials:: node_name={}".format(my_node_name))
    runtime_cert_chain = get_runtime_certificate_chain_as_string(my_node_name,security_dir=security_dir)
    private_key = get_private_key(my_node_name,security_dir=security_dir)
    return runtime_cert_chain + private_key


def get_certificate(my_node_name, cert_name):
    """Return certificate with name cert_name from disk for runtime my_node_name"""
    # TODO: get certificate from DHT (alternative to getting from disk).
    _log.debug("get_certificate: my_node_name={}, cert_name={}".format(my_node_name, cert_name))
    runtime_dir = get_own_credentials_path(my_node_name)
    try:
        # Check if the certificate is in the 'others' folder for runtime my_node_name.
        files = os.listdir(os.path.join(runtime_dir, "others"))
        matching = [s for s in files if cert_name in s]
        with open(os.path.join(runtime_dir, "others", matching[0]), 'rb') as f:
            certstr = f.read()
            verify_certificate(TRUSTSTORE_TRANSPORT, certstr)
            certificate = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certstr)
            return certificate
    except Exception:
        _log.debug("Certificate could not be found in others folder")
        try:
            _log.debug("Look for certificate in mine folder")
            # Check if cert_name is the runtime's own certificate.
            files = os.listdir(os.path.join(self.runtime_dir, "mine"))
            matching = [s for s in files if cert_name in s]
            with open(os.path.join(self.runtime_dir, "mine", matching[0]), 'rb') as f:
                certstr = f.read()
                certificate.verify_certificate(TRUSTSTORE_TRANSPORT, certstr,
                                               security_dir=self.configuration['RT_default']['security_dir'])
                self.verify_certificate(TRUSTSTORE_TRANSPORT, certstr)
                certificate = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certstr)
                return certificate
        except Exception:
            _log.debug("Certificate could not be found in mines folder")
            try:
                _log.debug("Look for certificate in storage")
                # Look for certificate in storage
                self.node.storage.get_index(['node','certificate',self.node_id],
                                            CalvinCB(self._register_node_cb))

            except Exception:
                _log.debug("Certificate could not be found in storage")
                raise

def get_certificate_from_storage_cb(self, key, value):
    _log.debug("get_certificate_from_storage_cb, \nkey={}\nvalue={}".format(key,value))
    if value:
        nbr = len(value)
    else:
        _log.error("The certificate can not be found")
        raise Exception("The certificate can not be found")



def get_private_key(node_name,security_dir=None):
    """Return the node's private key"""
    if not node_name:
        _log.error("No node_name supplied")
    _log.debug("get_private_key: node_name={}".format(node_name))
    runtime_dir = get_own_credentials_path(node_name,security_dir=security_dir)
    with open(os.path.join(runtime_dir, "private", "private.key"), 'rb') as f:
        return f.read()


def get_runtime_certificate_chain_as_list(my_node_name, security_dir=None):
    """Return certificate chain as a list of strings and as a list 
    of OpenSSL certificate objects
    """
    # TODO: make for flexible to support intermediate certificates
    _log.debug("get_runtime_certificate_chain_as_list: my_node_name={}".format(my_node_name))
    cert_chain_list_of_strings = []
    cert_chain_list_of_x509 = []
    try:
        cert_chain_str = get_runtime_certificate_chain_as_string(my_node_name, security_dir=security_dir)
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

def get_runtime_certificate_chain_as_string(my_node_name, security_dir=None):
    """Return certificate from disk for runtime my_node_name"""
    # TODO: get certificate from DHT (alternative to getting from disk).
    _log.debug("get_runtime_certificate_chain_as_string: my_node_name={}".format(my_node_name))
    runtime_dir = get_own_credentials_path(my_node_name, security_dir=security_dir)
    try:
        # Check if cert_name is the runtime's own certificate.
        files = os.listdir(os.path.join(runtime_dir, "mine"))
        with open(os.path.join(runtime_dir, "mine", files[0]), 'rb') as f:
            cert_str=f.read()
            return cert_str
    except Exception as err:
        _log.debug("Failed to get the runtimes certificate chain, err={}".format(err))
        raise Exception("Failed to get the runtimes certificate chain")

def get_own_cert(node_name, security_dir=None):
    """
    Return the signed runtime certificate
    in the "mine" folder
    """
    _log.debug("get_own_cert: node_name={}".format(node_name))
    runtime_dir = get_own_credentials_path(node_name, security_dir=security_dir)
    cert_dir = os.path.join(runtime_dir, "mine")
    try:
        filename = os.listdir(cert_dir)
        st_cert = open(os.path.join(cert_dir, filename[0]), 'rt').read()
        cert_part = st_cert.split(BEGIN_CRT_LINE)
        certstr = "{}{}".format(BEGIN_CRT_LINE, cert_part[1])
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                              certstr)
        return cert, certstr
    except:
        # Certificate not available
        _log.debug("No runtime certificate can be found")
        return None, None

def get_own_cert_name(node_name, security_dir=None):
    """Return the node's own certificate name without file extension"""
    _log.debug("get_own_cert_name: node_name={}".format(node_name))
    runtime_dir = get_own_credentials_path(node_name, security_dir=security_dir)
    return os.path.splitext(os.listdir(os.path.join(runtime_dir, "mine"))[0])[0]

def get_public_key_from_certpath(certpath):
    try:
        with open(certpath, 'rb') as fd:
            certstring = fd.read()
    except Exception as err:
        _log.debug("Certificate path {} cannot be opened, err={}".format(certpath, err))
    try:
        return get_public_key_from_certstr(certstring)
    except Exception as err:
        _log.debug("Error when trying to extract public key, err={}".format(err))

def get_public_key_from_certstr(certstring):
    certificate = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certstring)

    return get_public_key(certificate)

def get_public_key(certificate):
    """
    Return the public key from certificate
    certificate: certificate as a PEM formatted string
    """
    _log.info("get_public_key:\n\tcertificate={}".format(certificate))
    cert_pem = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, certificate)
    cert = load_pem_x509_certificate(cert_pem, default_backend())
    return cert.public_key()
    # The following line can replace the two lines above in pyOpenSSL version 16.0.0 (unreleased):
    # return OpenSSL.crypto.dump_publickey(OpenSSL.crypto.FILETYPE_PEM, certificate.get_pubkey())


###########################################################
# Linking a runtime name on a host to a persistent node-id
# This linkage is included in CSR and signed by CA
###########################################################

def obtain_cert_node_info(name, security_dir=None):
    """ Obtain node id based on name and domain from config
        Return dict with domain, node name and node id
    """
    _log.debug("obtain_cert_node_info: node_name={}".format(name))
    domain = _conf.get("security", "domain_name")
    if domain is None or name is None:
        # No security or name specified just use standard node UUID
        _log.debug("OBTAINING no security domain={}, name={}".format(domain, name))
        return {'domain': None, 'name': name, 'id': calvinuuid.uuid("NODE")}

    runtime_dir = get_own_credentials_path(name, security_dir=security_dir)
    # Does existing signed runtime certificate exist, return info
    try:
        filenames = os.listdir(os.path.join(runtime_dir, "mine"))
        content = open(os.path.join(runtime_dir, "mine", filenames[0]), 'rt').read()
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                              content)
        subject = cert.get_subject()
        if subject.commonName != name or subject.organizationName != domain:
            raise Exception("names of cert incorrect")
        _log.debug("OBTAINING existing security domain={}, name={}, id={}".format(domain, name, subject.dnQualifier))
        return {'domain': domain, 'name': name, 'id': subject.dnQualifier}
    except:
        pass
        #_log.exception("OBTAINING fail existing security domain={}, name={}".format(domain, name))
    # No valid signed cert available, create new node id and let user create certificate later
    nodeid = calvinuuid.uuid("NODE")
    return {'domain': domain, 'name': name, 'id': nodeid}




def store_trusted_root_cert(cert_file, type, security_dir=None):
    """
    Copy the certificate giving it the name that can be stored in
    trustStore for verification of signatures.
    file is the out file

    """
    commonName = cert_CN(certpath=cert_file)
    runtimes_dir = get_runtimes_credentials_path(security_dir=security_dir)
    if type not in [TRUSTSTORE_TRANSPORT,TRUSTSTORE_SIGN]:
        _log.exception("Incorrect value for type")
        raise Exception("Incorrect value for type")
    store_dir = os.path.join(runtimes_dir, type)
    if not os.path.isdir(store_dir):
        os.makedirs(store_dir)
    try:
        certificate_hash = cert_hash(certpath=cert_file)
    except:
        _log.exception("Failed to get certificate hash")
        raise Exception("Failed to get certificate hash")
    #if filename collides with another certificate, increase last number
    #E.g., if two certificates get same hasih, the first file is name <cert_hash>.0
    # and the second <cert_hash>.1
    i=0
    filename_exist=True
    while filename_exist:
        out_file = os.path.join(store_dir, certificate_hash+"."+`i`)
        if os.path.isfile(out_file):
            i += 1
        else:
            filename_exist=False

    shutil.copy(cert_file, store_dir)
    return



#TODO: to be deleted, dependencies in secure dht that should be removed
def store_own_cert(certstring=None, certpath=None, security_dir=None):
    """
    Store the signed runtime certificate
    in the "mine" folder
    """
    _log.debug("store_own_cert")
    if certpath:
        with open(certpath, 'r') as cert_fd:
            certdata = cert_fd.read()
    elif certstring:
        certdata=certstring
    commonName = cert_CN(certdata)
    runtime_dir = get_own_credentials_path(commonName, security_dir=security_dir)
    try:
        certx509 = load_certdata(certdata)
        subject = certx509.get_subject()
        fingerprint = certx509.digest("sha256")
        id = fingerprint.replace(":", "")[-40:]
        filename = "{}.pem".format(id)
        storepath = os.path.join(runtime_dir, "mine",
                                filename)
        _log.debug("Store signed cert as %s" % storepath)
        if certpath:
            shutil.copy(certpath, storepath)
        elif certstring:
            with open(storepath, 'w') as cert_fd:
                cert_fd.write(certdata)
    except (Exception), err:
        _log.exception("Storing signed cert failed")
        raise Exception("Storing signed cert failed")
    return



def get_security_credentials_path(security_dir=None):
    """Return the node's own certificate name without file extension"""
    _log.debug("get_security_credentials_path, security_dir={}".format(security_dir))
    security_dir_in_conf = _conf.get("security", "security_dir")
    if security_dir:
        _log.debug("get_security_credentials_path: security_dir supplied, security_dir={}".format(security_dir))
        return security_dir
    elif security_dir_in_conf:
        _log.debug("get_security_credentials_path: security_path in calvin.conf:%s" % security_dir_in_conf)
        return security_dir_in_conf
    else:
        _log.debug("use default path")
        homefolder = get_home()
        return os.path.join(homefolder, ".calvin", "security")

def get_runtimes_credentials_path(security_dir=None):
    """Return the node's own certificate name without file extension"""
    _log.debug("get_runtimes_credentials_path")
    return os.path.join(get_security_credentials_path(security_dir=security_dir), "runtimes")

def get_own_credentials_path(node_name, security_dir=None):
    """Return the node's own certificate name without file extension"""
    _log.debug("get_own_credentials_path")
    return os.path.join(get_runtimes_credentials_path(security_dir=security_dir),node_name)


# Generic helper functions.
def load_cert(cert_file):
    """
    Load the `cert_file` (can be CSR or CERT) to a
    OpenSSL X509 object and return it.

    Raise IOError if the file is missing.
    Raise OpenSSL.crypto.Error on OpenSSL errors.
    """
    _log.debug("load_cert: cert_file=%s" % cert_file)
    with open(cert_file, 'r') as cert_fd:
        certdata = cert_fd.read()
    return load_certdata(certdata)

def load_certdata(certdata):
    """
    Load the `cert_file` (can be CSR or CERT) to a
    OpenSSL X509 object and return it.

    Raise IOError if the file is missing.
    Raise OpenSSL.crypto.Error on OpenSSL errors.
    """
    if BEGIN_CRT_LINE in certdata:
        certdata_part = certdata.split(BEGIN_CRT_LINE)[1]
        certdatastr = "{}{}".format(BEGIN_CRT_LINE, certdata_part)
        load_certificate = OpenSSL.crypto.load_certificate
        try:
            certdata = load_certificate(OpenSSL.crypto.FILETYPE_PEM, certdatastr)
        except:
            raise
    elif BEGIN_CSR_LINE in certdata:
        certdata_part = certdata.split(BEGIN_CSR_LINE)[1]
        certdatastr = "{}{}".format(BEGIN_CSR_LINE, certdata_part)
        load_certificate = OpenSSL.crypto.load_certificate_request
        try:
            certdata = load_certificate(OpenSSL.crypto.FILETYPE_PEM, certdatastr)
        except:
            raise
    else:
        raise Exception("certificate is malformed")
    return certdata

def get_truststore(type, security_dir=None):
    """
    Returns the truststore for the type of usage as list of
    certificate strings, a list of OpenSSL objects and as a 
    OpenSSL truststore object
    """
    _log.debug("get_truststore: type={}".format(type))
    ca_cert_list_str = []
    ca_cert_list_x509 = []
    truststore = OpenSSL.crypto.X509Store()
    try:
        truststore_path = get_truststore_path(type, security_dir=security_dir)
        ca_files = [f for f in os.listdir(truststore_path) if not f.startswith('.')]
        for file_name in ca_files:
            filepath = os.path.join(truststore_path, file_name)
            with open(filepath, 'rb') as f:
                cert_str = f.read()
                ca_cert_list_str.append(cert_str)
                ca_cert_x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_str)
                ca_cert_list_x509.append(ca_cert_x509)
                truststore.add_cert(ca_cert_x509)
    except Exception as err:
        _log.exception("Failed to load truststore = %s",err)
        raise
    return ca_cert_list_str, ca_cert_list_x509, truststore

def get_truststore_path(type, security_dir=None):
    _log.debug("get_trust_store_path: type={}".format(type))
    try:
        runtime_dir = get_runtimes_credentials_path(security_dir=security_dir)
    except Exception as err:
        _log.error("Failed to determine trust store path" % err)
        raise
    if type not in [TRUSTSTORE_TRANSPORT, TRUSTSTORE_SIGN]:
       raise Exception("trust store type does not exist")
    return os.path.join(runtime_dir, type)

def export_cert(certpath, path):
    """
    Copy the certificate giving it the name that can be stored in
    trustStore for verification of signatures.
    file is the out file
    -certpath: path of the certificate to be exported
    -path: directory where the cert will be exported to
    """

    try:
        certificate_hash = cert_hash(certpath=certpath)
    except:
        _log.exception("Failed to get certificate hash")
        raise Exception("Failed to get certificate hash")
    i=0
    filename_exist=True
    #if filename collides with another certificate, increase last number
    #E.g., if two certificates get same has, the first file is name <cert_hash>.0
    # and the second <cert_hash>.1
    if not os.path.isdir(path):
        os.makedirs(path)
    while filename_exist:
        out_file = os.path.join(path, certificate_hash+"."+`i`)
        if os.path.isfile(out_file):
            i += 1
        else:
            filename_exist=False
    shutil.copyfile(certpath, out_file)
    return out_file


def wrap_object_with_symmetric_key(plaintext):
    import json
    import base64
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend

    #Pad data
    padder = padding.PKCS7(128).padder()
    padded_plaintext = padder.update(plaintext)
    padded_plaintext += padder.finalize()
    #Generate random symmetric key and intialization vector
    key = os.urandom(32)
    iv = os.urandom(16)
    #Encrypt object
    backend = default_backend()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()
    wrapped_object= {'ciphertext': base64.b64encode(ciphertext), 'symmetric_key':base64.b64encode(key), 'iv':base64.b64encode(iv)}
    return wrapped_object

def unwrap_object_with_symmetric_key(wrapped_object):
    import json
    import base64
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend

    backend = default_backend()
    #Decode base64
    key = base64.b64decode(wrapped_object['symmetric_key'])
    iv =  base64.b64decode(wrapped_object['iv'])
    ciphertext =  base64.b64decode(wrapped_object['ciphertext'])
    #Decrypt
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
    decryptor = cipher.decryptor()
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    #Remove padding
    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_plaintext)
    return plaintext + unpadder.finalize()

#TODO: Add integrity protection of object, i.e.,
# implement proper RSA-KEM+DEM1 or RSA-REACT
def encrypt_object_with_RSA(certificate, plaintext, unencrypted_data=None):
    """
    Encrypts an object using hybrid cryptography
    -certificate: PEM certificate
    -plaintext: string to be encrypted
    -unencrypted_data: data that will not be encrypted, but appended, e.g., usefull for debugging
    """
    import base64
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import padding,rsa
    from cryptography.hazmat.primitives import hashes

    #Wrap plaintext with a symmetric key
    wrapped_object = wrap_object_with_symmetric_key(plaintext)
    #Extract public key from certificate
    cert = x509.load_pem_x509_certificate(certificate, default_backend())
    message = wrapped_object['symmetric_key']
    public_key = cert.public_key()
    #Encrypt symmetric key with RSA public key
    ciphertext = public_key.encrypt(
         message,
         padding.OAEP(
             mgf=padding.MGF1(algorithm=hashes.SHA1()),
             algorithm=hashes.SHA1(),
             label=None
         )
     )
    encrypted_object = {'encrypted_symmetric_key':base64.b64encode(ciphertext),
                        'iv':wrapped_object['iv'],
                        'ciphertext':wrapped_object['ciphertext'],
                        'unencrypted_data':unencrypted_data}
    return encrypted_object


def decrypt_object_with_RSA(private_key, password, encrypted_object):
    import base64
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import padding,rsa
    from cryptography.hazmat.primitives import hashes
    #Decrypt private key
    _private_key = serialization.load_pem_private_key(
             private_key,
             password=password,
             backend=default_backend()
         )
    wrapped_object={}
    if 'iv' in encrypted_object:
        wrapped_object['iv']=encrypted_object['iv']
    else:
        _log.error("No IV in encrypted object, encrypted_object={}".format(encrypted_object))
        return None
    if 'ciphertext' in encrypted_object:
        wrapped_object['ciphertext']=encrypted_object['ciphertext']
    else:
        _log.error("No ciphertext in encrypted object, encrypted_object={}".format(encrypted_object))
        return None
    #Decrypt symmetric key
    wrapped_object['symmetric_key'] = _private_key.decrypt(
        base64.b64decode(encrypted_object['encrypted_symmetric_key']),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
                            algorithm=hashes.SHA1(),
                            label=None
            )
        )
    #Unwrap the plaintext using symmetric cryptography
    plaintext = unwrap_object_with_symmetric_key(wrapped_object)
    return plaintext

