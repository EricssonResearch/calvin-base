#!/usr/bin/python

import certificate
import os
print "Reading configuration."
a = certificate.Config()
print "Conf read successfull."

print "Creating new runtime."
new = certificate.new_runtime(a)
print "Created new runtime. " + new

print "Creating new domain."
certificate.new_domain(a)
print "Created new domain."

print "Signing certificate request."
certificate.sign_req(a, os.path.basename(new))
print "Certificaqte request signed."
