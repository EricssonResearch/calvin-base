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


# Parsers
from calvin.runtime.south.storage import dht, securedht, sql
from calvin.runtime.north.plugins.storage.proxy import StorageProxy
from calvin.runtime.north.plugins.storage.storage_dict_local import StorageLocal

def get(type_, node=None):
    if type_ == "sql":
        return sql.SqlClient()
    if type_ == "dht":
        return dht.AutoDHTServer(node.id, node.control_uri)
    elif type_ == "securedht":
        return securedht.AutoDHTServer(node.id, node.control_uri, node.runtime_credentials)
    elif type_ == "proxy":
        return StorageProxy(node)
    elif type_ == "local":
        return None
    elif type_ == "test_local":
        # This is used in transport tests without full runtimes, does not work for full runtimes!
        return StorageLocal(node)

    raise Exception("Parser {} requested is not supported".format(type_))
