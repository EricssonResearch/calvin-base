
# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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


class ActorState(object):
    """
    Class to let actors manipulate serialized actor state before
    a replication.
    Exposes managed attributes and 'replication_count'
    as attributes of the object.
    """

    def __init__(self, state, replication_data):
        super(ActorState, self).__init__()
        self.__dict__['state'] = state
        self.__dict__['replication_data'] = replication_data

    def __getattr__(self, name):
        if name[0] != "_" and name in self.state['private']['_managed']:
            return self.state['managed'][name]
        elif name == "replication_count":
            return self.replication_data.counter
        else:
            raise AttributeError("ActorState does not have access to %s" % name)

    def __setattr__(self, name, value):
        if name[0] != "_" and name in self.state['private']['_managed']:
            self.__dict__['state']['managed'][name] = value
        else:
            raise AttributeError("ActorState does not have access to %s" % name)
