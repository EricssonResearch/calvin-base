#!/usr/bin/python

from calvin.utilities import certificate
from calvin.utilities import certificate_authority
import os

print "Creating new domain."
testca = certificate_authority(domain="test")
print "Created new domain."

for i in range(1, 5):
    for j in range(0, 6):
        name = "node{}:{}".format(i, j)
        certreq = certificate.new_runtime(name, "test")
        testca.sign_csr(os.path.basename(certreq), name)
certreq = certificate.new_runtime("evil", "test")
testca.sign_csr(os.path.basename(certreq))
# certreq = certificate.new_runtime(name, "evil2")
# certificate.sign_csr(testconfig2, os.path.basename(certreq), "evil2")
