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

import pytest
import os
import json
import yaml
import jsonschema
from jsonschema.exceptions import ValidationError
from calvin.actorstore.store import Store
from  calvin.utilities.actor_signature import signature
import hashlib


# Helpers
def actor_files():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path = os.path.join(dir_path, "../systemactors")
    for dirpath, dirnames, filenames in os.walk(dir_path):
        filenames = [os.path.join(dirpath, f) for f in filenames if f.endswith('.py') and f != '__init__.py']
        for f in filenames:
            yield f

def read_file(filepath):
    with open(filepath, 'r') as f:
        src = f.read()
    return src

def _create_signature(actor_type, metadata):
    # Create the actor signature to be able to look it up in the GlobalStore if neccessary
    signature_desc = {
        'is_primitive': True,
        'actor_type': actor_type,
        'inports': [port['name'] for port in metadata['ports'] if port['direction'] == 'in'],
        'outports': [port['name'] for port in metadata['ports'] if port['direction'] == 'out']
    }
    return signature_old(signature_desc)

def signature_old(desc):
    """ Takes actor/component description and
        generates a signature string
    """
    if 'is_primitive' not in desc or desc['is_primitive']:
        signature = {u'actor_type': unicode(desc['actor_type']),
                     u'inports': sorted([unicode(i) for i in desc['inports']]),
                     u'outports': sorted([unicode(i) for i in desc['outports']])}
    else:
        if type(desc['component']) is dict:
            signature = {u'actor_type': unicode(desc['actor_type']),
                         u'inports': sorted([unicode(i) for i in desc['component']['inports']]),
                         u'outports': sorted([unicode(i) for i in desc['component']['outports']])}
        else:
            signature = {u'actor_type': unicode(desc['actor_type']),
                         u'inports': sorted([unicode(i) for i in desc['component'].inports]),
                         u'outports': sorted([unicode(i) for i in desc['component'].outports])}
    return hashlib.sha256(json.dumps(signature, separators=(',', ':'), sort_keys=True)).hexdigest()


@pytest.fixture(scope='module')
def store():
    store = Store()
    return store


@pytest.mark.parametrize('actor_file', actor_files())
def test_valid_docstring(actor_file):
    src = read_file(actor_file)
    _, docs, _ = src.split('"""', 2)
    data = yaml.load(docs)
    result = True
    try:
        jsonschema.validate(data, Store.actor_properties_schema)
    except ValidationError:
        result = False
    assert result

    
@pytest.mark.parametrize('actor_file', actor_files())
def test_valid_docstring(store, actor_file):
    print actor_file
    basepath, _ = os.path.splitext(actor_file)
    _, ns, name = basepath.rsplit('/', 2)
    actor_type = "{}.{}".format(ns, name)
    metadata = store.get_metadata(actor_type)
    
    new_sign = signature(metadata)
    ref_sign = _create_signature(actor_type, metadata)
    
    assert new_sign == ref_sign

    
    