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

from calvin.Tools.cscompiler import compile_file
import unittest
import json
import glob
import os
# import difflib
import collections
import pytest

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

def _codegen(testname, ds, credentials):
    test_file = _filepath(testname, "calvin")
    # code, issuetracker = compile_file(filename, ds, ir, credentials=None)
    code, it = compile_file(test_file, ds, ir=False, credentials=credentials)
    code = json.loads(json.dumps(code)) # FIXME: Is there no other way of making this unicode???
    ref_file = _filepath(testname, "deployjson" if ds else "ref")
    ref_code = _read_file(ref_file)
    # print "ref_code", type(ref_code)
    ref_code = json.loads(ref_code)
    ref_code.setdefault('valid', True)
    # print code, ref_code

    return code, it, ref_code

def cs_codegen(testname):
    return _codegen(testname, ds=False, credentials=None)

def ds_codegen(testname):
    return _codegen(testname, ds=True, credentials=None)

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
def testCalvinScriptCodegen(test):
    code, it, ref = cs_codegen(test)
    assert it.error_count == 0
    compare(ordered(code), ordered(ref))

@pytest.mark.parametrize("test", test_list)
def testCalvinScriptDeploygen(test):
    code, it, ref = ds_codegen(test)
    assert it.error_count == 0
    compare(ordered(code), ordered(ref))
