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

from abc import ABCMeta, abstractmethod
import os
import glob
import json

# This is an abstract class for the PRP (Policy Retrieval Point)
class PolicyRetrievalPoint(object):
    __metaclass__ = ABCMeta  # Metaclass for defining Abstract Base Classes
    
    @abstractmethod
    def get_matching_policies(self, request):
        """Return policies where policy target matches request"""
        return

    @abstractmethod
    def get_policy(self, id):
        """Return a JSON representation of the policy identified by id"""
        return

    @abstractmethod
    def get_policies(self, filter):
        """Return a JSON representation of all policies found by using filter"""
        return

    @abstractmethod
    def create_policy(self, data):
        """Create policy based on the JSON representation in data"""
        return

    @abstractmethod
    def update_policy(self, data, id):
        """Change the content of the policy identified by id to data (JSON representation of policy)"""
        return

    @abstractmethod
    def delete_policy(self, id):
        """Delete the policy identified by id"""
        return


class FilePolicyRetrievalPoint(PolicyRetrievalPoint):

    def __init__(self, path):
        # TODO: path may be located on other server. How to handle that?
        # Replace ~ by the user's home directory and add trailing slash if it is not already there
        self.path = os.path.join(os.path.expanduser(path), '') 
    
    # Use get_policies instead and do the matching in policy_decision_point.py?
    def get_matching_policies(self, request, name_pattern):
        """Return policies where policy target matches request"""
        return

    def get_policy(self, filename):
        """Return the policy identified by filename"""
        with open(self.path + filename, 'rb') as data:
            return json.load(data)

    def get_policies(self, name_pattern='*.json'):
        """Return all policies found using the name_pattern"""
        policies = []
        for filename in glob.glob(self.path + name_pattern): 
            with open(filename, 'rb') as data:
                policies.append(json.load(data))
        return policies

    def create_policy(self, data, filename):
        """Create policy named filename based on the JSON representation in data"""
        file_path = self.path + filename
        if not os.path.isfile(file_path):
            with open(file_path, "w") as f:
                f.write(data)
        else:
            raise  # Raise exception if policy named filename already exists

    def update_policy(self, data, filename):
        """Change the content of the policy identified by filename to data (JSON representation of policy)"""
        file_path = self.path + filename
        if os.path.isfile(file_path):
            with open(file_path, "w") as f:
                f.write(data)
        else:
            raise  # Raise exception if policy named filename doesn't exist

    def delete_policy(self, filename):
        """Delete the policy named filename"""
        os.remove(self.path + filename)