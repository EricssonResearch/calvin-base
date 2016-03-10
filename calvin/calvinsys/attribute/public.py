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

from calvin.utilities.calvinlogger import get_logger


_log = get_logger(__name__)


class PublicAttribute(object):
    """
        A calvinsys module for fetching private attributes.
        
        Takes an index and returns a dictionary of the form
            value 
        or 
            {}
        if no value found. 
        Returns None on error.
    """
    
    def __init__(self, node, actor):
        self._node = node
        self._actor = actor 
                
    def exists(self, index):
        """
            Returns True iff index exists as private attribute,
            returns None on error
        """
        return self._node.attributes.has_public_attribute(index)
    
    def get(self, index):
        """
            Returns value of public attribute 'index', or {}
            if no such attribute. Returns None on error
        """
        return self._node.attributes.get_public(index)


def register(node, actor):
    return PublicAttribute(node, actor)
