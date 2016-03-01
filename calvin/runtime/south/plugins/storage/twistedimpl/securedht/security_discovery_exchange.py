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

"""
Use sphinx.ext.autodoc to extract comments.

Node state diagram behaviour:
digraph N {
    STATE_NEW -> STATE_CONFIGURED;
    STATE_CONFIGURED -> STATE_CSR_GENERATED;
    STATE_CONFIGURED -> STATE_CSR_GENERATE_FAILED;
    STATE_CSR_GENERATE_FAILED -> STATE_PANIC;
    STATE_CSR_GENERATED -> STATE_TRANSMITTING;
    STATE_TRANSMITTING -> STATE_CSR_REQUESTED;
    STATE_TRANSMITTING -> STATE_TRANSMITTING_FAILED;
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
"""

"""Shared states 0x00000000"""
STATE_NEW = 0x00000000 # Object is initiated but not loaded or started.
STATE_CONFIGURED = 0x00000001 # Requirements for satisfaction and fingerprints have been loaded.
STATE_LISTENING = 0x00000002 # Node or Ca is listening for request or response.
STATE_TRANSMITTING = 0x0000003 # Node or Ca is transmitting a request or response.

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
STATE_CSR_RECEIVED = 0x00002000 # A CSR have been received.
STATE_CSR_ACCEPTED = 0x00002001 # A CSR is accepted according to configuration and openssl policy.
STATE_CSR_SIGNED = 0x00002002 # A CSR is signed by Ca.
STATE_CSR_ALREDY_SIGNED = 0x00002003 # A received CSR have already been signed.
STATE_CERTIFICATE_GENERATED = 0x00002004 # A certificate have been generated.

"""Exceptions"""
STATE_CONFIGURAION_FAILED = 0x00000004 # Configuration is missing required attributes to set policy.
STATE_CSR_GENERATE_FAILED = 0x00001002 # CSR generation failed.

STATE_CA_DENIED_CONFIGURATION = 0x0000100B # Ca cert is rejected due to Calvin security configuration.
STATE_CA_DENIED_MALFORMED = 0x0000100C # Ca cert is denied as it is malformed.
STATE_CERTIFICATE_INVALID = # Certificate is not validly signed by CA.
STATE_CERTIFICATE_DENIED_MALFORMED
STATE_CERTIFICATE_DENIED_CONFIGURATION

STATE_CSR_DENIED_OPENSSL_POLICY = 0x00002005 # A CSR is rejected due to openssl policy (see openssl.conf)
STATE_CSR_DENIED_CONFIGURATION = 0x00002006 # A CSR is rejected due to Calvin security configuration.
STATE_CSR_DENIED_MALLFORMED = 0x00002007 # A CSR is denied as it is malformed.

STATE_STORE_FAILED # Storing failed.
STATE_TRANSMISSION_FAILED = 0x00000005 # Failed to transmit.
STATE_LISTEN_TIMEOUT = 0x00000006 # Listening timed out before receiving anything.
STATE_PANIC = 0x00000007 # A critical error that cannot be resolved.
class Node(Object):
    """
    A node client with state and methods to maintain the Node
    procedures in a security discovery exchange.
    """
    def __init__(self, configuration):
        """Maintain state of a Node and store `configuration`."""
        self.state = STATE_NEW
        self.configuration = configuration
        if self.verify_configuration():
            try:
                self.state = STATE_CONFIGURED
            except 
    def verify_configuration(self):
        """
        Verify that the self.confifguration contains required fields.
        """
        raise NotImplemented
        self.state = STATE_CONFIGURED

    def generate_csr(self, path):
        """
        Generate CSR store csr on disk at `path`.
        """
        raise NotImplemented
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
        """
        raise NotImplemented
        self.state = STATE_CERTIFICATE_RECEIVED

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
        self.state = STATE_CA_STORED

    def store_certificate(self, cert):
        """
        Store a `cert` in path defined by configuration.
        raise IOError if path is not found.
        raise OSError if permissions are insuficcient.
        """
        raise NotImplemented
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
