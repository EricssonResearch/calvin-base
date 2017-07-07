from calvin.runtime.south.calvinlib.jsonlib import Json
import json

import pytest
import unittest

pytest_unittest = pytest.mark.unittest
    
@pytest_unittest
class TestJson(unittest.TestCase):
    
    def setUp(self):
        self.json = Json.Json(None, None)
        self.json.init()
        
    def test_encode_ok(self):
        data = {"key": "value"}
        
        our_json = self.json.tostring(data)
        real_json = json.dumps(data)
        
        self.assertEqual(our_json, real_json)
    
    def test_decode_ok(self):
        data = json.dumps({"key": "value"})
        
        our_json = self.json.fromstring(data)
        real_json = json.loads(data)
        
        self.assertEqual(our_json, real_json)
