#!/usr/bin/python

from calvin.utilities import certificate
import os
print "Trying to create a new domain configuration."
testconfig = certificate.Config(domain="test")
# testconfig2 = certificate.Config(domain="evil")
print "Reading configuration successfull."

print "Creating new domain."
certificate.new_domain(testconfig)
# certificate.new_domain(testconfig2)
print "Created new domain."

for i in range(1, 5):
    for j in range(0, 6):
        name = "node{}:{}".format(i, j)
        certreq = certificate.new_runtime(testconfig, name)
        certificate.sign_req(testconfig, os.path.basename(certreq), name)
certreq = certificate.new_runtime(testconfig, "evil")
certificate.sign_req(testconfig, os.path.basename(certreq), "evil")
# certreq = certificate.new_runtime(testconfig, "evil2")
# certificate.sign_req(testconfig2, os.path.basename(certreq), "evil2")
