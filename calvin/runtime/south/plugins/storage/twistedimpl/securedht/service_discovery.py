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



class ServiceDiscoveryBase(object):
    def __init__(self, iface=''):
        pass

    def start(self):
        pass

    def start_search(self, callback=None, auto_stop=False):
        pass

    def stop_search(self):
        pass

    def set_client_filter(self, service):
        pass

    def register_service(self, service, ip, port):
        pass

    def unregister_service(self, service):
        pass

    def search(self):
        pass

    def stop(self):
        pass
