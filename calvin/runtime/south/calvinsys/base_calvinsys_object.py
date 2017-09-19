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

from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)

class BaseCalvinsysObject(object):

    def __init__(self, calvinsys, name, actor):
        super(BaseCalvinsysObject, self).__init__()
        self.calvinsys = calvinsys
        self.name = name
        self.actor = actor

    def init(self, **kwargs):
        """
        Init object

        Args:
            **kwargs: Key word init arguments
        """
        raise NotImplementedError()

    def can_write(self):
        """
        Check if data can be written

        Returns:
            True if data can be written, otherwise False
        """
        raise NotImplementedError()

    def write(self, data):
        """
        Write data

        Args:
            data: JSON formatted data to be written
        """
        raise NotImplementedError()

    def can_read(self):
        """
        Check if data can be read

        Returns:
            True if data can be read/is available, otherwise False
        """
        raise NotImplementedError()

    def read(self):
        """
        Read data

        Returns:
            Data
        """
        raise NotImplementedError()

    def close(self):
        """
        Close object
        """
        raise NotImplementedError()

    def scheduler_wakeup(self):
        """
        Trigger the scheduler
        """
        self.calvinsys.scheduler_wakeup(self.actor)

    def serialize(self):
        """
            Serialize calvinsys object (not always meaningful, hence default is empty serialization)
        """
        return None
    
    def deserialize(self, state, **kwargs):
        """
            Deserialize calvinsys object (not always meaningful, hence default is create new object)
        """
        self.init(**kwargs)
        return self