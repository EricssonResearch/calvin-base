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

def cert_CN(certstring=None, certpath=None):
    """Return the common name of the certificate subject"""
    cert = get_cert_data(certstring=certstring, certpath=certpath)
    return cert.get_subject().CN

def cert_DN_Qualifier(certstring=None, certpath=None):
    """Return the common name of the certificate subject"""
    cert = get_cert_data(certstring=certstring, certpath=certpath)
    return cert.get_subject().dnQualifier


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


def get_public_key_from_certpath(certpath):
    try:
        with open(certpath, 'rb') as fd:
            certstring = fd.read()
    except Exception as err:
        _log.error("Certificate path {} cannot be opened, err={}".format(certpath, err))
    try:
        return get_public_key_from_certstr(certstring)
    except Exception as err:
        _log.error("Error when trying to extract public key, err={}".format(err))

def get_public_key_from_certstr(certstring):
    try:
        certificate = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certstring)
    except Exception as err:
        _log.error("Error when trying to open cert string, err={}".format(err))
    return get_public_key(certificate)

def get_public_key(certificate):
    """
    Return the public key from certificate
    certificate: certificate as a PEM formatted string
    """
#    _log.info("get_public_key:\n\tcertificate={}".format(certificate))
    cert_pem = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, certificate)
    cert = load_pem_x509_certificate(cert_pem, default_backend())
    return cert.public_key()
    # The following line can replace the two lines above in pyOpenSSL version 16.0.0 (unreleased):
    # return OpenSSL.crypto.dump_publickey(OpenSSL.crypto.FILETYPE_PEM, certificate.get_pubkey())


def store_trusted_root_cert(cert_file, type, security_dir=None):
    """
    Copy the certificate giving it the name that can be stored in
    trustStore for verification of signatures.
    file is the out file

    """
    commonName = cert_CN(certpath=cert_file)
    runtimes_dir = get_runtimes_credentials_path(security_dir=security_dir)
    if type not in [TRUSTSTORE_TRANSPORT,TRUSTSTORE_SIGN]:
        _log.error("Incorrect value for type")
        raise Exception("Incorrect value for type")
    store_dir = os.path.join(runtimes_dir, type)
    if not os.path.isdir(store_dir):
        os.makedirs(store_dir)
    try:
        certificate_hash = cert_hash(certpath=cert_file)
    except:
        _log.error("Failed to get certificate hash")
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

def get_security_credentials_path(security_dir=None):
    """Return the path to the folder with all security credentials"""
#    _log.debug("get_security_credentials_path, security_dir={}".format(security_dir))
    security_dir_in_conf = _conf.get("security", "security_dir")
    if security_dir:
        return security_dir
    elif security_dir_in_conf:
        return security_dir_in_conf
    else:
        homefolder = get_home()
        return os.path.join(homefolder, ".calvin", "security")

def get_runtimes_credentials_path(security_dir=None):
    """Return the path to the shared runtimes credentials folder"""
#    _log.debug("get_runtimes_credentials_path")
    return os.path.join(get_security_credentials_path(security_dir=security_dir), "runtimes")

# Generic helper functions.
def load_cert(cert_file):
    """
    Load the `cert_file` (can be CSR or CERT) to a
    OpenSSL X509 object and return it.

    Raise IOError if the file is missing.
    Raise OpenSSL.crypto.Error on OpenSSL errors.
    """
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

def get_truststore_as_list_of_strings(type, security_dir=None):
    """
    Returns the truststore for the type of usage as list of
    certificate strings, a list of OpenSSL objects and as a 
    OpenSSL truststore object
    Args:
        type: either of [ceritificate.TRUSTSTORE_SIGN, certificate.TRUSTSTORE_TRANSPORT]
        security_dir: path to security directory, if other than default value (OPTIONAL)
    Return values:
        ca_cert_list_str: list of CA certitificate in string format
    """
#    _log.debug("get_truststore: type={}".format(type))
    ca_cert_list_str = []
    try:
        truststore_path = get_truststore_path(type, security_dir=security_dir)
        ca_files = [f for f in os.listdir(truststore_path) if not f.startswith('.')]
        for file_name in ca_files:
            if file_name.endswith(".pem"):
                filepath = os.path.join(truststore_path, file_name)
                with open(filepath, 'rb') as f:
                    cert_str = f.read()
                    ca_cert_list_str.append(cert_str)
    except Exception as err:
        _log.error("Failed to load truststore = %s",err)
        raise
    return ca_cert_list_str

#Deprecated, to be removed
def get_truststore(type, security_dir=None):
    """
    Returns the truststore for the type of usage as list of
    certificate strings, a list of OpenSSL objects and as a 
    OpenSSL truststore object
    Args:
        type: either of [ceritificate.TRUSTSTORE_SIGN, certificate.TRUSTSTORE_TRANSPORT]
        security_dir: path to security directory, if other than default value (OPTIONAL)
    Return values:
        ca_cert_list_str: list of CA certitificate in string format
        ca_cert_list_x509: list of CA certificate as OpenSSL certificate objects
        truststore: OpenSSL X509 store object with trusted CA certificates
    """
#    _log.debug("get_truststore: type={}".format(type))
    ca_cert_list_str = []
    ca_cert_list_x509 = []
    truststore = OpenSSL.crypto.X509Store()
    try:
        truststore_path = get_truststore_path(type, security_dir=security_dir)
        ca_files = [f for f in os.listdir(truststore_path) if not f.startswith('.')]
        for file_name in ca_files:
            if file_name.endswith(".pem"):
                filepath = os.path.join(truststore_path, file_name)
                with open(filepath, 'rb') as f:
                    cert_str = f.read()
                    ca_cert_list_str.append(cert_str)
                    ca_cert_x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_str)
                    ca_cert_list_x509.append(ca_cert_x509)
                    truststore.add_cert(ca_cert_x509)
    except Exception as err:
        _log.error("Failed to load truststore = %s",err)
        raise
    return ca_cert_list_str, ca_cert_list_x509, truststore

def _get_truststore_context(type, certificate, security_dir=None):
    """
    Returns a OpenSSL truststore context usefull for verification of X.509 certificate verification
    Args:
        type: either of [ceritificate.TRUSTSTORE_SIGN, certificate.TRUSTSTORE_TRANSPORT]
        certificate: certificate to be verified, should be OpenSSL X509 object
        security_dir: path to security directory, if other than default value (OPTIONAL)
    Return values:
        truststore_ctx: OpenSSL X509 store context object with trusted CA certificates
    """
    try:
        ca_cert_list_str, ca_cert_list_x509, truststore = get_truststore(type, security_dir=security_dir)
    except Exception as e:
        _log.error("Failed to load trusted certificates:"
                   "type={}"
                   "security_dir={}"
                   "e={}".format(type, security_dir, e))
        raise
    try:
        store_ctx = OpenSSL.crypto.X509StoreContext(truststore, certificate)
        return store_ctx
    except Exception as e:
        _log.error("Failed to create X509StoreContext: %s" % e)
        raise

def verify_certificate_chain(type, certificate, security_dir=None):
    """
    Verifies a certificate chain using the truststore for a given type. Raise exception
    if verification fails
    Args:
        type: either of [ceritificate.TRUSTSTORE_SIGN, certificate.TRUSTSTORE_TRANSPORT]
        certificate: certificate to be verified, should be OpenSSL X509 object
        security_dir: path to security directory, if other than default value (OPTIONAL)
    """
    store_ctx = _get_truststore_context(type, certificate, security_dir=None)
    try:
        store_ctx.verify_certificate()
    except Exception as e:
        _log.error("Failed to verify certificate:"
                   "\n\terr={}"
                   "\n\ttype={}"
                   "\n\tsecurity_dir={}"
                   "".format(err, type, security_dir))
 
def get_truststore_path(type, security_dir=None):
#    _log.debug("get_trust_store_path: type={}".format(type))
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

    if not os.path.isdir(path):
        os.makedirs(path)
    #If the file exist, overwrite it
    out_file = os.path.join(path, cert_O(certpath=certpath) + ".pem")
    shutil.copyfile(certpath, out_file)
    return out_file

def c_rehash(type, security_dir=None):
    """
    Copy the certificate giving it the name that can be stored in
    trustStore for verification of signatures.
    file is the out file
    -certpath: path of the certificate to be exported
    -path: directory where the cert will be exported to
    """
    ts_strlist, ts_opensslist, openssl_ts_object = get_truststore(type=type, security_dir=security_dir)
    path = get_truststore_path(type=type, security_dir=security_dir)
    for filename in os.listdir(path):
        if filename.endswith(".pem"):
            try:
                certificate_hash = cert_hash(certpath=os.path.join(path, filename))
            except Exception as err:
                print "Failed to get certificate hash, err={}".format(err)
                _log.error("Failed to get certificate hash, err={}".format(err))
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
        os.symlink(filename, out_file)
    return


def _wrap_object_with_symmetric_key(plaintext):
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

def _unwrap_object_with_symmetric_key(wrapped_object):
    import json
    import base64
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend

    backend = default_backend()
    #Decode base64
    try:
        key = base64.b64decode(wrapped_object['symmetric_key'])
        iv =  base64.b64decode(wrapped_object['iv'])
        ciphertext =  base64.b64decode(wrapped_object['ciphertext'])
    except Exception as err:
        _log.error("Failed to decode base64 encoding of key, IV or ciphertext, err={}".format(err))
        raise
    #Decrypt
    try:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    except Exception as err:
        _log.error("_unwrap_object_with_symmetric_key: Failed to decrypt, err={}".format(err))
        raise
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
    wrapped_object = _wrap_object_with_symmetric_key(plaintext)
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
    try:
        wrapped_object['symmetric_key'] = _private_key.decrypt(
            base64.b64decode(encrypted_object['encrypted_symmetric_key']),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                                algorithm=hashes.SHA1(),
                                label=None
                )
            )
    except Exception as err:
        _log.error("decrypt_object_with_RSA: Failed to decrypt, err={} \n{}".format(err, base64.b64decode(encrypted_object['encrypted_symmetric_key'])))
        raise
    #Unwrap the plaintext using symmetric cryptography
    plaintext = _unwrap_object_with_symmetric_key(wrapped_object)
    return plaintext

class TrustStore():
    def __init__(self, truststore_dir):
        self.truststore_dir=truststore_dir
        self.truststore = self._initialize_truststore()

    def _initialize_truststore(self):
        truststore = OpenSSL.crypto.X509Store()
        try:
            ca_files = [f for f in os.listdir(self.truststore_dir) if not f.startswith('.')]
            for file_name in ca_files:
                if file_name.endswith(".pem"):
                    filepath = os.path.join(self.truststore_dir, file_name)
                    with open(filepath, 'rb') as f:
                        cert_str = f.read()
                        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_str)
                        truststore.add_cert(cert)
        except Exception as err:
            _log.error("Failed to load truststore = %s",err)
            raise
        return truststore

    def _get_truststore_context(self, certificate):
        """
        Returns a OpenSSL truststore context usefull for verification of X.509 certificate verification
        Args:
            certificate: certificate to be verified, should be OpenSSL X509 object
        Return values:
            truststore_ctx: OpenSSL X509 store context object with trusted CA certificates
        """
        try:
            store_ctx = OpenSSL.crypto.X509StoreContext(self.truststore, certificate)
            return store_ctx
        except Exception as e:
            _log.error("_get_truststore_context::Failed to create X509StoreContext: %s" % e)
            raise

    def verify_certificate_from_path(self, certpath):
        try:
            with open(certpath, 'rb') as fd:
                certstring = fd.read()
        except Exception as err:
            _log.error("verify_certificate_from_path::Failed to open certificate, err={}".format(err))
        return self.verify_certificate_str(certstring)

    def verify_certificate_str(self, certstring):
        """Verify certificate using the CA certificate"""
    #    _log.debug("verify_certificate: \n\tcertstring={}".format(certstring))
        try:
            cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certstring)
        except Exception as e:
            _log.error("verify_certificate_str::Failed to load certstring: certstring={}, error={}".format(certstring, e))
            raise Exception("verify_certificate_str::Failed to load certstring")
        return self.verify_certificate(cert)

    def verify_certificate(self, cert):
        """Verify certificate using the CA certificate
        Args:
            cert: a X509 PyOpenSSL object
        Return values:
            cert: a X509 PyOpenSSL object
        """
    #    _log.debug("verify_certificate: \n\tcertstring={}".format(certstring))
        subject = cert.get_subject()
        serial = cert.get_serial_number()
        if cert.has_expired():
            _log.error("Certificate has expired")
            raise CertificateInvalid("Certificate has expired.")
        if serial < 0:
            _log.error("Serial number was negative")
            raise CertificateDeniedMalformed("Serial number was negative.")
        try:
            self._verify_cert_with_policy(cert)
            cert.get_signature_algorithm()  # TODO: Check sig alg strength
        except ValueError as err:
            _log.error("Unknown signature algorithm, err={}".format(err))
            raise CertificateDeniedMalformed("Unknown signature algorithm.")
        # Verify the certificate chain using truststore.
        try:
            self._verify_certificate_chain(cert)
        except Exception as e:
            _log.error("Failed to create X509StoreContext: %s" % e)
            raise
        return cert

    def _verify_cert_with_policy(self, cert):
        pubkey = cert.get_pubkey()
        if pubkey.type() is TYPE_ECC and pubkey.bits() < 256:
            raise CertificateDeniedConfiguration("Too small ECC key in cert.")
        if pubkey.type() is OpenSSL.crypto.TYPE_RSA and pubkey.bits < 2048:
            raise CertificateDeniedConfiguration("Too small RSA key in cert.")
        if pubkey.type() is OpenSSL.crypto.TYPE_DSA and pubkey.bits < 2048:
            raise CertificateDeniedConfiguration("Too small DSA key in cert.")

    def _verify_certificate_chain(self, certificate):
        """
        Verifies a certificate chain using the truststore. Raise exception
        if verification fails
        Args:
            certificate: certificate to be verified, should be OpenSSL X509 object
        """
        store_ctx = self._get_truststore_context(certificate)
        try:
            store_ctx.verify_certificate()
        except Exception as e:
            _log.error("Failed to verify certificate:"
                       "\n\terr={}"
                       "".format(err))

    def store_trusted_root_cert(self, cert_file):
        """
        Copy the certificate giving it the name that can be stored in
        trustStore for verification of signatures.
        file is the out file

        """
        try:
            certificate_hash = cert_hash(certpath=cert_file)
        except:
            _log.error("Failed to get certificate hash")
            raise Exception("Failed to get certificate hash")
        name = os.path.basename(cert_file)
        new_path = os.path.join(self.truststore_dir, name)
        shutil.copy(cert_file, self.truststore_dir)
        self._ce_rehash_file(new_path)
        return

    def _c_rehash_file(self, path):
        """
        """
        if path.endswith(".pem"):
            try:
                certificate_hash = cert_hash(path)
            except Exception as err:
                print "Failed to get certificate hash, err={}".format(err)
                _log.error("Failed to get certificate hash, err={}".format(err))
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
            os.symlink(path, out_file)
            return
        else:
            raise Exception("File does not exist or does not have a .pem")

    def c_rehash(self):
        """
        Copy the certificate giving it the name that can be stored in
        trustStore for verification of signatures.
        file is the out file
        -certpath: path of the certificate to be exported
        -path: directory where the cert will be exported to
        """
        for filename in os.listdir(self.truststore_dir):
            self._c_rehash_file(filename)
        return

    def verify_signature(self, data, signature, certstring):
        """Verify signed data"""
        try:
            cert = self.verify_certificate_str(certstring)
        except:
            raise
        try:
            # Verify signature
            OpenSSL.crypto.verify(cert, signature, data, 'sha256')
        except Exception as e:
            _log.error("Signature verification failed, err={}".format(e))
            raise
        return cert


class Certificate():
    def __init__(self, security_dir=None):
        homefolder = get_home()
        default_path = os.path.join(homefolder, ".calvin", "security")
        self.security_dir = security_dir if security_dir else self._get_security_credentials_path()
        self.runtimes_dir = os.path.join(self.security_dir, "runtimes")
        self.truststore_transport_dir = os.path.join(self.runtimes_dir, TRUSTSTORE_TRANSPORT)
        if not os.path.isdir(self.truststore_transport_dir):
            try:
                os.makedirs(self.truststore_transport_dir)
            except OSError:
                pass
        self.truststore_sign_dir = os.path.join(self.runtimes_dir, TRUSTSTORE_SIGN)
        if not os.path.isdir(self.truststore_sign_dir):
            try:
                os.makedirs(self.truststore_sign_dir)
            except OSError:
                pass
        self.truststore_transport = TrustStore(self.truststore_transport_dir)
        self.truststore_sign = TrustStore(self.truststore_sign_dir)

    def _get_security_credentials_path(self):
        security_dir_in_conf = _conf.get("security", "security_dir")
        if security_dir_in_conf:
            return security_dir_in_conf
        else:
            homefolder = get_home()
            return os.path.join(homefolder, ".calvin", "security")

    def get_runtimes_credentials_path(self):
        return self.runtimes_dir

    def get_truststore_path(self, type):
        if type==TRUSTSTORE_TRANSPORT:
            return self.truststore_transport_dir
        elif type==TRUSTSTORE_SIGN:
            return self.truststore_sign_dir
        else:
           raise Exception("trust store type does not exist")

    def verify_certificate_str(self, type, cert_str):
        if type==TRUSTSTORE_TRANSPORT:
            return self.truststore_transport.verify_certificate_str(cert_str)
        elif type==TRUSTSTORE_SIGN:
            return self.truststore_sign.verify_certificate_str(cert_str)
        else:
           raise Exception("trust store type does not exist")


