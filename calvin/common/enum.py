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

warnings.warn("calvin.common.enum should be replaced by python's enum.", DeprecationWarning)

def enum(*sequential, **named):
    enums = dict(list(zip(sequential, list(range(len(sequential))))), **named)
    reverse = dict((value, key) for key, value in iter(enums.items()))
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)

