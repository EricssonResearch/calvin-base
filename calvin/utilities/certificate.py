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
BEGIN_LINE = "-----BEGIN CERTIFICATE-----"
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

def get_cert_data(certstring=None, certpath=None):
    """Return the hash of the certificate subject"""
    if certpath:
        try:
            with open(certpath, 'r') as cert_fd:
                certdata = cert_fd.read()
        except:
            errormsg = "Error opening " \
                       "certificate file. {}".format(stderr)
            raise IOError(errormsg)
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

def cert_CN(certstring=None, certpath=None):
    """Return the common name of the certificate subject"""
    cert = get_cert_data(certstring=certstring, certpath=certpath)
    return cert.get_subject().CN

def cert_DN_Qualifier(ccertstring=None, certpath=None):
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




def verify_certificate(type, certstring, domain=None):
    """Verify certificate using the CA certificate"""
    # Create a certificate store and add the CA certificate
    #TODO: support of multiple ca-certs
    #TODO: ca cert should have appropriate names
    trusted_certs = OpenSSL.crypto.X509Store()
    if type in [TRUSTSTORE_TRANSPORT,TRUSTSTORE_SIGN]:
        runtimes_dir = get_runtimes_credentials_path()
        cacert_path = os.path.join(runtimes_dir, type)
    else:
        _log.error("Certificate type not supported")
        raise IOErros("Certificate type not supported")
    try:
        files = os .listdir(cacert_path)
        for file_name in files:
            filepath = os.path.join(cacert_path, file_name)
            with open(filepath, 'rb') as f:
                cacert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, f.read())
                trusted_certs.add_cert(cacert)
    except Exception as e:
        _log.error("Failed to load trusted certificates: %s" % e)
        #list of trusted CAs will be empty and verification will fail
        pass
    try:
        certx509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certstring)
    except Exception as e:
        _log.error("Failed to load certstring: certstring={}, error={}".format(certstring, e))
        raise Exception("Failed to load certstring")
    #Do sanity checks of cert
    subject = certx509.get_subject()
    serial = certx509.get_serial_number()
    if certx509.has_expired():
        raise CertificateInvalid("Certificate has expired.")
    if serial < 0:
        raise CertificateDeniedMalformed("Serial number was negative.")
    try:
        verify_certstr_with_policy(certstring)
        certx509.get_signature_algorithm()  # TODO: Check sig alg strength
    except ValueError:
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
        # Check if cert_name is the runtime's own certificate.
        files = os.listdir(os.path.join(runtime_dir, "mine"))
        matching = [s for s in files if cert_name in s]
        with open(os.path.join(runtime_dir, "mine", matching[0]), 'rb') as f:
            certstr = f.read()
            verify_certificate(TRUSTSTORE_TRANSPORT, certstr)
            certificate = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certstr)
            return certificate


def get_private_key(node_name):
    """Return the node's private key"""
    if not node_name:
        _log.error("No node_name supplied")
    _log.debug("get_private_key: node_name={}".format(node_name))
    runtime_dir = get_own_credentials_path(node_name)
    with open(os.path.join(runtime_dir, "private", "private.key"), 'rb') as f:
        return f.read()

def get_own_cert(node_name):
    """
    Return the signed runtime certificate
    in the "mine" folder
    """
    _log.debug("get_own_cert: node_name={}".format(node_name))
    runtime_dir = get_own_credentials_path(node_name)
    cert_dir = os.path.join(runtime_dir, "mine")
    try:
        filename = os.listdir(cert_dir)
        st_cert = open(os.path.join(cert_dir, filename[0]), 'rt').read()
        cert_part = st_cert.split(BEGIN_LINE)
        certstr = "{}{}".format(BEGIN_LINE, cert_part[1])
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                              certstr)
        return cert, certstr
    except:
        # Certificate not available
        _log.debug("No runtime certificate can be found")
        return None, None

def get_own_cert_name(node_name):
    """Return the node's own certificate name without file extension"""
    _log.debug("get_own_cert_name: node_name={}".format(node_name))
    runtime_dir = get_own_credentials_path(node_name)
    return os.path.splitext(os.listdir(os.path.join(runtime_dir, "mine"))[0])[0]

def get_public_key(certificate):
    """Return the public key from certificate"""
    cert_pem = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, certificate)
    cert = load_pem_x509_certificate(cert_pem, default_backend())
    return cert.public_key()
    # The following line can replace the two lines above in pyOpenSSL version 16.0.0 (unreleased):
    # return OpenSSL.crypto.dump_publickey(OpenSSL.crypto.FILETYPE_PEM, certificate.get_pubkey())


###########################################################
# Linking a runtime name on a host to a persistent node-id
# This linkage is included in CSR and signed by CA
###########################################################

def obtain_cert_node_info(name):
    """ Obtain node id based on name and domain from config
        Return dict with domain, node name and node id
    """
    _log.debug("obtain_cert_node_info: node_name={}".format(name))
    domain = _conf.get("security", "security_domain_name")
    if domain is None or name is None:
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




def store_trusted_root_cert(cert_file, trusted_root, security_dir=None):
    """
    Copy the certificate giving it the name that can be stored in
    trustStore for verification of signatures.
    file is the out file

    """
    commonName = cert_CN(certpath=cert_file)
    runtimes_dir = get_runtimes_credentials_path(security_dir=security_dir)
    if trusted_root==TRUSTSTORE_TRANSPORT:
        storepath = os.path.join(runtimes_dir, TRUSTSTORE_TRANSPORT)
    elif trusted_root==TRUSTSTORE_SIGN:
        storepath = os.path.join(runtimes_dir, TRUSTSTORE_SIGN)
    else:
        _log.exception("Incorrect value for trusted_root")
        raise Exception("Incorrect value for trusted_root")
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
        out_file = os.path.join(storepath, certificate_hash+"."+`i`)
        if os.path.isfile(out_file):
            i += 1
        else:
            filename_exist=False

    shutil.copy(cert_file, storepath)
    return


def store_cert(type, node_name, cert_id=None, certstring=None, certpath=None, security_dir=None):
    """
    Store the signed runtime certificate
    in the "mine" folder
    """
    _log.debug("store_cert")
    if certpath:
        with open(certpath, 'r') as cert_fd:
            certdata = cert_fd.read()
    elif certstring:
        certdata=certstring
    commonName = cert_CN(certdata)
    runtime_dir = get_own_credentials_path(node_name, security_dir=security_dir)
    try:
        certx509 = load_certdata(certdata)
        subject = certx509.get_subject()
        fingerprint = certx509.digest("sha256")
        id = cert_id if not None else fingerprint.replace(":", "")[-40:]
        filename = "{}.pem".format(id)
        if type not in ["mine","others"]:
            _log.error("type not supported")
            raise Exception("type not supported")
        storepath = os.path.join(runtime_dir, type, filename)
        _log.debug("Store signed cert as %s" % storepath)
        if certpath:
            shutil.copy(certpath, storepath)
        elif certstring:
            with open(storepath, 'w') as cert_fd:
                cert_fd.write(certdata)
    except (Exception), err:
        _log.exception("Storing signed cert failed")
        raise Exception("Storing signed cert failed")
    return storepath

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

def store_others_cert(node_name, id, certstring=None, certpath=None):
    _log.debug("store_others_cert, node_name={}".format(node_name))
    return store_cert("others", node_name, id, certstring=certstring, certpath=certpath)
#    name_dir = get_own_credentials_path(node_name)
#    _log.debug("name_dir:{}".format(name_dir))
#    file_path = os.path.join(name_dir, "others", "{}.pem".format(id) )
#    _log.debug("store others cert as:{}".format(file_path))
#    if certstring:
#        with open(file_path.format(id), 'w') as file:
#            file.write(certString)
#            file.close()
#    elif certpath:
#        os.util.copy(certpath, file_path)


def get_security_credentials_path(security_dir=None):
    """Return the node's own certificate name without file extension"""
    _log.debug("get_runtimes_credentials_path")
    security_path = _conf.get("security", "security_path")
    if security_dir:
        _log.debug("security_dir supplied")
        return security_dir
    elif security_path:
        _log.debug("security_path in calvin.conf:%s" % security_path)
        return security_path
    else:
        _log.debug("use default path")
        homefolder = get_home()
        return os.path.join(homefolder, ".calvin", "security")

def get_runtimes_credentials_path(security_dir=None):
    """Return the node's own certificate name without file extension"""
    _log.debug("get_runtimes_credentials_path")
    return os.path.join(get_security_credentials_path(security_dir), "runtimes")

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
    if BEGIN_LINE in certdata:
        certdata_part = certdata.split(BEGIN_LINE)[1]
        certdatastr = "{}{}".format(BEGIN_LINE, certdata_part)
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

def get_truststore_path(nodename, type, security_dir=None):
    _log.debug("get_trust_store_path: nodename={}, type={}".format(nodename, type))
    try:
        runtime_dir = get_runtimes_credentials_path(security_dir)
    except Exception as err:
        _log.error("Failed to determine trust store path" % err)
        raise Exception("Failed to determine trust store path")
    if type==TRUSTSTORE_SIGN:
       return os.path.join(runtime_dir, TRUSTSTORE_SIGN)
    elif type==TRUSTSTORE_TRANSPORT:
        return os.path.join(runtime_dir, TRUSTSTORE_TRANSPORT)
    else:
       raise Exception("trust store type does not exist")
   
def export_cert(certpath, path):
    """
    Copy the certificate giving it the name that can be stored in
    trustStore for verification of signatures.
    file is the out file

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
    while filename_exist:
        out_file = os.path.join(path, certificate_hash+"."+`i`)
        if os.path.isfile(out_file):
            i += 1
        else:
            filename_exist=False
    shutil.copyfile(certpath, out_file)
    return out_file

