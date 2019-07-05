# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 Ericsson AB
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

import warnings

warnings.warn("calvin.common._enum should be replaced by python's enum.", DeprecationWarning)

# FIXME: Some of our code relies on the fact that enums are really ints, and  
#        that ENUM.FOO can be serialized over tunnels/rt2rt communication
#        This is probably easier to fix once we have modernized the code.
# FIXME: Somewhere in our code, an assumption is made that the first
#        enumeration index is 0 (test by changing start to 1 in code below)

def enum(*sequence):
    enums = {name:index for index, name in enumerate(sequence, start=0)}
    enums['reverse_mapping'] = {index:name for name, index in enums.items()}
    return type('Enum', (), enums)

