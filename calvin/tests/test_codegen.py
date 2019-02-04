# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from calvinservices.csparser.cscompiler import compile_file
import unittest
import json
import glob
import os
# import difflib
import collections
import pytest
import subprocess
import shlex


def absolute_filename(filename):
    return os.path.join(os.path.dirname(__file__), filename)

def _read_file(file):
    try:
        with open(file, 'r') as source:
            # print source.encoding
            text = str(source.read())
            # print type(text), type(unicode(text))
    except Exception as e:
        print "Error: Could not read file: '%s'" % file
        raise e
    return text

def _filepath(testname, ext):
    return "{}{}.{}".format(absolute_filename('codegen/'), testname, ext)

def codegen(testname):
    test_file = _filepath(testname, "calvin")
    code, it = compile_file(test_file, include_paths=None)
    code = json.loads(json.dumps(code)) # FIXME: Is there no other way of making this unicode???
    
    ref_file = _filepath(testname, "ref")
    ref_code = _read_file(ref_file)
    # print "ref_code", type(ref_code)
    ref_code = json.loads(ref_code)
    ref_code.setdefault(u'valid', True)
    
    ref_file = _filepath(testname, "deployjson")
    ref_deploy = _read_file(ref_file)
    # print "ref_code", type(ref_code)
    ref_deploy = json.loads(ref_deploy)
    ref_deploy.setdefault(u'valid', True)
    
    ref_code = {u'app_info':ref_code, u'deploy_info':ref_deploy}
    ref_code.setdefault(u'app_info_signature', None)

    return code, it, ref_code


# Since the ds contains nested lists we cannot simply use == to check for equality
def compare(dut, ref):
    if isinstance(ref, basestring):
        # print "basestring"
        # print "Comparing {} and {}".format(dut, ref)
        assert dut == ref
    elif isinstance(ref, collections.Mapping):
        # print "mapping"
        # print "Comparing {} and {}".format(dut, ref)
        keys = set(ref.keys())
        assert set(dut.keys()) == keys
        for key in keys:
            compare(dut[key], ref[key])
    elif isinstance(ref, collections.Iterable):
        # print "iterable"
        # print "Comparing {} and {}".format(dut, ref)
        assert len(dut) == len(ref)
        pairs = zip(dut, ref)
        for pair in pairs:
            compare(*pair)
    else:
        # print "other"
        # print "Comparing {} and {}".format(dut, ref)
        assert dut == ref

# See https://stackoverflow.com/a/25851972
def ordered(obj):
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj


test_list = [os.path.basename(x)[:-7] for x in glob.glob("{}/*.calvin".format(absolute_filename('codegen')))]

@pytest.mark.parametrize("test", test_list)
def testCalvinScriptCodegen(actorstore, test):
    code, it, ref = codegen(test)
    assert it.error_count == 0
    compare(ordered(code), ordered(ref))

