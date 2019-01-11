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
from calvin.actorstore.newstore import Store

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
    