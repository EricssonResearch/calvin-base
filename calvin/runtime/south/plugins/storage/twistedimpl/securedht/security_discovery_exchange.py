"""
Security Discovery Exchange.
Transmit a Certificate Signature Request from a new node over multicast SSDP
to a Certificate Authority Cettificate Authority can sign request or not
depending on a configuration over unicast.
Node         Certificate Authority
 |------CSR,CA-FP---->|
 |                    | Signature()
 |<---Certificate,CA--|
 |                    |

The certificate discovery services are divided in two sections.
One for new clients and one for certificate authority functions.
By collecting and recording states for a Node and a Ca it is possible to
leave a Security Discovery Exchange at any time and continue later if a
temporary error has occured.
Errors generate exceptions and the exception handler manages the error state
unless successfull.
"""

import certificate
import configuration
import service_discovery_ssdp
import OpenSSL

"""
Use sphinx.ext.autodoc to extract comments.

Node state diagram behaviour:
digraph N {
    STATE_NEW -> STATE_CONFIGURED;
    STATE_CONFIGURED -> STATE_CSR_GENERATED;
    STATE_CONFIGURED -> STATE_CSR_GENERATE_FAILED;
    STATE_CSR_GENERATE_FAILED -> STATE_PANIC;
    STATE_CSR_GENERATED -> STATE_TRANSMIT;
    STATE_TRANSMIT -> STATE_CSR_REQUESTED;
    STATE_TRANSMIT -> STATE_TRANSMITTING_FAILED;
    STATE_TRANSMITTING_FAILED -> STATE_PANIC;
    STATE_CSR_REQUESTED -> STATE_LISTENING;
    STATE_LISTENING -> STATE_CERTIFICATE_RECEIVED;
    STATE_LISTENING -> STATE_LISTENING_TIMEOUT;
    STATE_LISTENING_TIMEOUT -> STATE_CSR_GENERATED;
    STATE_CERTIFICATE_RECEIVED -> STATE_CA_ACCEPTED_CONFIGURATION;
    STATE_CERTIFICATE_RECEIVED -> STATE_CA_DENIED_CONFIGURATION;
    STATE_CA_DENIED_CONFIGURATION -> STATE_LISTENING;
    STATE_CA_DENIED_MALFORMED -> STATE_LISTENING;
    STATE_CA_ACCEPTED_CONFIGURATION -> STATE_CERTIFICATE_ACCEPTED_CONFIGURATION;
    STATE_CA_ACCEPTED_CONFIGURATION -> STATE_CERTIFICATE_DENIED_CONFIGURATION;
    STATE_CERTIFICATE_DENIED_CONFIGURATION -> STATE_LISTENING;
    STATE_CERTIFICATE_ACCEPTED_CONFIGURATION -> STATE_CERTIFICATE_INVALID;
    STATE_CERTIFICATE_INVALID -> STATE_LISTENING;
    STATE_CERTIFICATE_ACCEPTED_CONFIGURATION -> STATE_CERTIFICATE_VALID;
    STATE_CERTIFICATE_VALID -> STATE_CA_STORED;
    STATE_CA_STORED -> STATE_STORE_FAILED;
    STATE_STORE_FAILED -> STATE_PANIC;
    STATE_CA_STORED -> STATE_CERTIFICATE_STORED;
    STATE_CERTIFICATE_STORED -> STATE_STORE_FAILED;
    STATE_CERTIFICATE_STORED -> STATE_SATISFIED;
    STATE_CERTIFICATE_STORED -> STATE_CSR_GENERATED;

}

Certificate Authority state diagram behaviour:
digraph C {
    STATE_NEW -> STATE_CONFIGURED;
    STATE_NEW -> STATE_CONFIGURAION_FAILED;
    STATE_CONFIGURAION_FAILED -> STATE_PANIC;
    STATE_CONFIGURED -> STATE_CA_GENERATED;
    STATE_CA_GENERATED -> STATE_LISTENING;
    STATE_LISTENING -> STATE_CSR_RECEIVED;
    STATE_CSR_RECEIVED -> STATE_CSR_ACCEPTED;
    STATE_CSR_RECEIVED -> STATE_CSR_ALREDY_SIGNED;
    STATE_CSR_ALREDY_SIGNED -> STATE_TRANSMIT;
    STATE_CSR_RECEIVED -> STATE_CSR_DENIED_CONFIGURATION;
    STATE_CSR_RECEIVED -> STATE_CSR_DENIED_MALLFORMED;
    STATE_CSR_ACCEPTED -> STATE_CSR_STORED;
    STATE_CSR_ACCEPTED -> STATE_STORE_FAILED;
    STATE_CSR_STORED -> STATE_CSR_SIGNED;
    STATE_CSR_SIGNED -> STATE_CERTIFICATE_GENERATED;
    STATE_CERTIFICATE_GENERATED -> STATE_STORE_FAILED;
    STATE_CSR_SIGNED -> STATE_STORE_FAILED;
    STATE_LISTENING -> STATE_LISTEN_FAILED;
    STATE_LISTEN_FAILED -> STATE_PANIC;
    STATE_STORE_FAILED -> STATE_PANIC;
    STATE_CERTIFICATE_GENERATED -> STATE_TRANSMIT;
    STATE_TRANSMIT -> STATE_TRANSMISSION_FAILED;
    STATE_TRANSMISSION_FAILED -> STATE_TRANSMIT;
    STATE_TRANSMIT -> STATE_CA_GENERATED;
}
"""

#TODO Make states into ENUM...
"""Shared states 0x00000000"""
STATE_NEW = 0x00000000 # Object is initiated but not loaded or started.
STATE_CONFIGURED = 0x00000001 # Requirements for satisfaction and fingerprints have been loaded.
STATE_LISTENING = 0x00000002 # Node or Ca is listening for request or response.
STATE_TRANSMIT = 0x0000003 # Node or Ca is transmitting a request or response.

"""Node states 0x00001000 """
STATE_SATISFIED = 0x00001000 # The node does not need to transmit further CSR it is sufficiently certified.
STATE_CSR_GENERATED = 0x00001001 # CSR has been generated.
STATE_CSR_REQUESTED = 0x00001003 # CSR have been requested.
STATE_CERTIFICATE_RECEIVED = 0x00001004 # Certificate has been received.
STATE_CERTIFICATE_VALID = 0x00001005 # Certificate is validly signed by cacert.
STATE_CA_ACCEPTED_CONFIGURATION = 0x00001006 # CAcert meets configuration requirements.
STATE_CERTIFICATE_ACCEPTED_CONFIGURATION = 0x00001007 # Certificate meets configuration requirements.
STATE_CA_STORED = 0x00001008 # CA is stored.
STATE_CERTIFICATE_STORED = 0x000010009 # Certificate is stored-

"""Ca states 0x00002000 """
STATE_CA_GENERATED
STATE_CSR_RECEIVED = 0x00002000 # A CSR have been received.
STATE_CSR_ACCEPTED = 0x00002001 # A CSR is accepted according to configuration and openssl policy.
STATE_CSR_SIGNED = 0x00002002 # A CSR is signed by Ca.
STATE_CSR_ALREDY_SIGNED = 0x00002003 # A received CSR have already been signed.
STATE_CERTIFICATE_GENERATED = 0x00002004 # A certificate have been generated.

"""Exceptions"""

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

class CertificateDeniedMalformed(Exception):
    """Ca cert is denied as it is malformed."""
    pass

class CertificateDeniedConfiguration(Exception):
    """Certificate is denied due to restrictions in configuration."""
    pass

class CsrDeniedConfiguration(Exception):
    """A CSR is rejected due to Calvin security configuration."""
    pass

class CsrDeniedConfiguration(Exception):
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

class Node(Object):
    """
    A node client with state and methods to maintain the Node
    procedures in a security discovery exchange.
    """
    def __init__(self, configuration):
        """Maintain state of a Node and store `configuration`."""
        self.state = STATE_NEW
        self.configuration = configuration
        self.discover()

    def discover(self):
        try:
            if self.state == STATE_NEW:
                self.verify_configuration():

            if self.state == STATE_CONFIGURED:
                csrfile = self.configuration("NEWCERT + CSRNAME")
                self.generate_csr(csrfile)

            if self.state == STATE_CSR_GENERATED:
                self.csrdata = open(csrfile, 'r').read()
                cafp = self.configuration("CA-Fingerprint")
                self.transmit_csr(self.csrdata, cafp)

            if self.state == STATE_TRANSMIT:
                self.certdata, self.cadata = self.receive_cert()

            if self.state == STATE_CERTIFICATE_RECEIVED:
                self.validate_cert(self.certdata, self.cadata)

            if self.state == STATE_CERTIFICATE_VALID:
                self.store_certificate(self.certdata)

            self.state = self.check_configuration()

            if self.state == STATE_SATISFIED:
                return self.state

        except (ConfigurationMalformed,
               CsrGenerationFailed,
               TransmissionFailed,
               ReceiveFailed,
               StoreFailed):
            # Fatal error, cause panic!
            raise
        except (CaDeniedConfiguration,
               CaDeniedMalformed,
               CertificateInvalid,
               CertificateDeniedMalformed,
               CertificateDeniedConfiguration):
            # Non fatal error, should cause retry STATE_CSR_GENERATED
            self.state = STATE_CSR_GENERATED
            self.discover()

    def verify_configuration(self):
        """
        Verify that the self.confifguration contains required fields.
        Raise ConfigurationMalformed is any required field is missing.
        """
        raise NotImplemented
        self.state = STATE_CONFIGURED

    def generate_csr(self, path):
        """
        Generate CSR store csr on disk at `path`.
        Rasie CsrGenerationFailed if csr generation fails.
        """
        raise NotImplemented
        raise CsrGenerationFailed
        self.state = STATE_CSR_GENERATED

    def transmit_csr(self, csr, cafp):
        """
        Transmit `csr` certificate on multicast group
        using SSDP with a desired `cafp` as a certificate authority
        fingerprint.
        """
        raise NotImplemented
        self.state = STATE_CSR_REQUESTED

    def receive_cert(self):
        """
        Listen for a signed certificate and a CA certificate response.
        Satisfy state STATE_CERTIFICATE_RECEIVED by receiving a certificates.
        Raise ListenFailed if listening failed.
        Return cert as string.
        """
        raise NotImplemented
        raise ListenFailed
        self.state = STATE_CERTIFICATE_RECEIVED
        cert = ""
        return cert

    def validate_cert(self, cert, cacert):
        """
        Confirm that a `cert` is verifiably signed with the `cacert`.
        """
        raise NotImplemented
        self.state = STATE_CERTIFICATE_VALID

    def verify_certificate_with_policy(self, cert):
        """
        Confirm that a certificate has a verifiable subject, expiry-time,
        signature strength, and domain belonging as defined by
        security configuration policy.
        """
        raise NotImplemented
        self.state = STATE_CERTIFICATE_ACCEPTED_POLICY

    def verify_ca_with_policy(self, cacert):
        """
        Confirm that a `cacert` is allowed in security configuration policy.
        """
        raise NotImplemented
        self.state = STATE_CA_ACCEPTED_POLICY

    def store_ca(self, cacert):
        """
        Store `cacert` is accordance with the path defined in configuration.
        """
        raise NotImplemented
        raise StoreFailed
        self.state = STATE_CA_STORED

    def store_certificate(self, cert):
        """
        Store a `cert` in path defined by configuration.
        raise StoreFailed if storing failed.
        raise IOError if path is not found.
        raise OSError if permissions are insuficcient.
        """
        raise NotImplemented
        raise StoreFailed
        self.state = STATE_CERTIFICATE_STORED

    def satisfied(self):
        """
        Check Node security configuration requirements and
        verify that this Node object is satisfied with its current state.
        Return True and set self.state = STATE_SATISFIED if satisfactory
        requirements are met otherwise return False and set state to desired
        next action.
        """
        raise NotImplemented
        self.state = STATE_SATISFIED

class Ca(Object):
    """Certificate Authority class."""

    def __init__(self, configuration):
        """Hold Ca state."""
        self.state = STATE_NEW
        self.configuration = configuration

    def discover(self):
        """State table traverser."""
        try:
            if self.state == STATE_NEW:
                self.verify_configuration()
            if self.state == STATE_CONFIGURED:
                self.cafile = self.find_ca(self.configuration("CA"))
            if self.state == STATE_LISTENING: #TODO Continue here...
            if self.state == STATE_CSR_RECEIVED:
            if self.state == STATE_CSR_ACCEPTED:
            if self.state == STATE_CSR_SIGNED:
            if self.state == STATE_CERTIFICATE_GENERATED:
            if self.state == STATE_TRANSMIT:
                self.state = STATE_CA_GENERATED
                self.discover()
        except CaNotFound:
            self.generate_ca()
            self.state = STATE_CONFIGURED

    def verify_configuration(self):
        """
        Verify that the self.confifguration contains required fields.
        """
        raise NotImplemented
        self.state = STATE_CONFIGURED

    def listen_csr(self):
        """
        Listen for `csr` certificate on multicast group
        using SSDP.
        Return csrdata, cadata.
        """
        raise NotImplemented
        csrdata = ""
        raise ListenFailed
        self.state = STATE_CSR_RECEIVED
        return csrdata, cadata

    def store_csr(self, csr):
        """
        Store `csr` in newcerts location from configuration.
        Raise store failed if there was problems storing.
        Return path to csr-file.
        """
        raise NotImplemented
        raise StoreFailed
        csrfile = ""
        return csrfile

    def validate_csr(self, csr):
        """
        Validate that the `csr` matches with configuration.
        Raise CsrDeniedConfiguration if the CSR did not satisfy the
        configuration.
        """
        raise NotImplemented
        raise CsrDeniedConfiguration

    def sign_csr(self, csrfile):
        """
        Sign the `csrfile`, return certificate file path.
        Raise StoreFailed if there was a problem storing the certificate.
        """
        raise NotImplemented
        raise StoreFailed
        certfile = ""
        return certfile

    def transmit_cert(self, cert):
        """
        Transmit `cert` certificate, and certificate authority
        to a multicast group using SSDP.
        """
        raise NotImplemented
        raise TransmissionFailed
