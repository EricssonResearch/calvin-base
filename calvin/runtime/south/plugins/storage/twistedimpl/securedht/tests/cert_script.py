#!/usr/bin/python

from calvin.utilities import certificate
from calvin.utilities.certificate_authority import CA
from calvin.utilities.utils import get_home
import os
import shutil


homefolder = get_home()
domain = "sec-dht-security-test"
testdir = os.path.join(homefolder, ".calvin","sec_dht_security_test")
configdir = os.path.join(testdir, domain)
runtimesdir = os.path.join(testdir,"runtimes")
runtimes_truststore = os.path.join(runtimesdir,"truststore_for_transport")
try:
    shutil.rmtree(testdir)
except:
    print "Failed to remove old tesdir"
    pass

print "Creating new domain."
testca = CA(domain="test", commonName="sec-dht-test-security-CA", security_dir=testdir)
print "Created new domain."

print "Generate runtime credentials and sign their certificates"
for i in range(1, 5):
    for j in range(0, 6):
        name = "node{}:{}".format(i, j)
        certreq = certificate.new_runtime(name, "test", security_dir=testdir)
        certpath = testca.sign_csr(certreq)
        certificate.store_own_cert(certpath=certpath, security_dir=testdir)
certreq = certificate.new_runtime("evil", "test", security_dir=testdir)
certpath = testca.sign_csr(certreq)
certificate.store_own_cert(certpath=certpath, security_dir=testdir)
testca.export_ca_cert(runtimes_truststore)

