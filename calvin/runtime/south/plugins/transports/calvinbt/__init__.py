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

import traceback

factories = {}


def register(_id, callbacks, schemas, formats):
    ret = {}
    if 'calvinbt' in schemas:
        try:
            import calvinbt_transport
            f = calvinbt_transport.CalvinTransportFactory(_id, callbacks)
            factories[_id] = f
            ret['calvinbt'] = f
        except ImportError:
            traceback.print_exc()
    return ret
