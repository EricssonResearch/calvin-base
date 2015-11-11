#!/usr/bin/python

import certificate
import os
print "Trying to create a new domain configuration."
testconfig = certificate.Config(domain="test")
print "Reading configuration successfull."

print "Creating new domain."
certificate.new_domain(testconfig)
print "Created new domain."

print "Creating new phone runtime."
phone = certificate.new_runtime(testconfig, "phone")
print "Created phone runtime"

print "Creating new lamp runtime."
lamp = certificate.new_runtime(testconfig, "lamp")
print "Created lamp runtimes. "


print "Signing phone certificate requests."
certificate.sign_req(testconfig, os.path.basename(phone))
print "Certificaqte request signed."

print "Signing lamp certificate requests."
certificate.sign_req(testconfig, os.path.basename(lamp))
print "Certificaqte request signed."
