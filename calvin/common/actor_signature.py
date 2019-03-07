# -*- coding: utf-8 -*-

# Copyright (c) 2015-2019 Ericsson AB
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

import json
import hashlib


def signature(metadata):
    signature = {
        'actor_type': str("{ns}.{name}".format(**metadata)),
        'inports': sorted([str(port['name']) for port in metadata['ports'] if port['direction'] == 'in']),
        'outports': sorted([str(port['name']) for port in metadata['ports'] if port['direction'] == 'out'])
    }
    data = json.dumps(signature, separators=(',', ':'), sort_keys=True)
    return hashlib.sha256(data.encode('utf-8')).hexdigest()
