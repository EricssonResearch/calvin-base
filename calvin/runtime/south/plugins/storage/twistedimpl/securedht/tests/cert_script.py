#!/usr/bin/python
import os
import shutil
from calvin.utilities import certificate
from calvin.utilities import certificate_authority
from calvin.utilities import runtime_credentials
from calvin.utilities.utils import get_home
from calvin.utilities import calvinuuid


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
testca = certificate_authority.CA(domain="test", commonName="sec-dht-test-security-CA", security_dir=testdir)
print "Created new domain."

print "Import CA cert into truststore."
testca.export_ca_cert(runtimes_truststore)

print "Generate runtime credentials and sign their certificates"
for i in range(1, 5):
    for j in range(0, 6):
        name = "node{}:{}".format(i, j)
        enrollment_password = testca.cert_enrollment_add_new_runtime(name)
        nodeid = calvinuuid.uuid("NODE")
        rt_cred = runtime_credentials.RuntimeCredentials(name, domain="test", 
                                        security_dir=testdir,
                                        nodeid=nodeid,
                                        enrollment_password=enrollment_password)
        csr_path = os.path.join(rt_cred.runtime_dir, name + ".csr")
        try:
            with open(csr_path +".challenge_password", 'w') as csr_fd:
                csr_fd.write(enrollment_password)
        except Exception as err:
            _log.exception("Failed to write challenge password to file, err={}".format(err))
            raise
        certpath = testca.sign_csr(csr_path)
        rt_cred.store_own_cert(certpath=certpath)

print "Generate evil node runtime credentials and sign certificate"
enrollment_password = testca.cert_enrollment_add_new_runtime("evil")
nodeid = calvinuuid.uuid("NODE")
rt_cred = runtime_credentials.RuntimeCredentials("evil", domain="test",
                                security_dir=testdir,
                                nodeid=nodeid,
                                enrollment_password=enrollment_password)
csr_path = os.path.join(rt_cred.runtime_dir, "evil.csr")
try:
    with open(csr_path +".challenge_password", 'w') as csr_fd:
        csr_fd.write(enrollment_password)
except Exception as err:
    _log.exception("Failed to write challenge password to file, err={}".format(err))
    raise
certpath = testca.sign_csr(csr_path)
rt_cred.store_own_cert(certpath=certpath)


