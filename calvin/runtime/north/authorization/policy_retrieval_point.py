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
from calvin.utilities import calvinuuid
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

# This is an abstract class for the PRP (Policy Retrieval Point)
class PolicyRetrievalPoint(object):
    __metaclass__ = ABCMeta  # Metaclass for defining Abstract Base Classes

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
        # Replace ~ by the user's home directory.
        self.path = os.path.expanduser(path)
        if not os.path.exists(self.path):
            try:
                os.makedirs(self.path)
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

    def get_policy(self, policy_id):
        """Return the policy identified by policy_id"""
        try:
            with open(os.path.join(self.path, policy_id + ".json"), 'rt') as data:
                return json.load(data)
        except Exception as err:
            _log.error("Failed to open policy file for policy_id={}".format(policy_id))
            raise

    def get_policies(self, name_pattern='*'):
        """Return all policies found using the name_pattern"""
        policies = {}
        for filename in glob.glob(os.path.join(self.path, name_pattern + ".json")): 
            try:
                with open(filename, 'rb') as data:
                    policy_id = os.path.splitext(os.path.basename(filename))[0]
                    policies[policy_id] = json.load(data)
            except ValueError as err:
                _log.error("Failed to parse policy as json, file={}".format(filename))
                raise
            except (OSError, IOError) as err:
                _log.error("Failed to open file={}".format(filename))
                raise
        return policies

    def create_policy(self, data):
        """Create policy based on the JSON representation in data"""
        policy_id = calvinuuid.uuid("POLICY")
        with open(os.path.join(self.path, policy_id + ".json"), "w") as file:
            json.dump(data, file)
        return policy_id

    def update_policy(self, data, policy_id):
        """Change the content of the policy identified by policy_id to data (JSON representation of policy)"""
        file_path = os.path.join(self.path, policy_id + ".json")
        if os.path.isfile(file_path):
            with open(file_path, "w") as file:
                json.dump(data, file)
        else:
            raise IOError  # Raise exception if policy named filename doesn't exist

    def delete_policy(self, policy_id):
        """Delete the policy named policy_id"""
        os.remove(os.path.join(self.path, policy_id + ".json"))
