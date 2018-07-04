from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *
from calvin.runtime.south.calvinlib.base64lib import Base64
import base64

import pytest
import unittest

pytest_unittest = pytest.mark.unittest
    
@pytest_unittest
class TestBase64(unittest.TestCase):
    
    def setUp(self):
        self.base64 = Base64.Base64(None, None)
        self.base64.init()
        
    def test_encode_ok(self):
        data = b'somebinarydata'
        our_b64 = self.base64.encode(data)
        decode = base64.b64decode(our_b64)
        
        self.assertEqual(data, decode)
    
    def test_decode_ok(self):
        data = b'somebinarydata'
        encoded = base64.b64encode(data)
        decoded = self.base64.decode(encoded)
        
        self.assertEqual(data, decoded)
