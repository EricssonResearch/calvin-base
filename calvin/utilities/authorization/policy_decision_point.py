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

import re
from calvin.utilities.authorization.policy_retrieval_point import FilePolicyRetrievalPoint

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class PolicyDecisionPoint(object):

    def __init__(self, config=None):
        # Default config
        self.config = {
            "policy_combining": "permit_overrides",
            "policy_storage": "files",
            "policy_storage_path": "~/.calvin/security/policies",
            "policy_name_pattern": "policy*.json"
            # "attribute_finder_modules": ["attribute_finder"]
        }
        if config is not None:
            # Change some of the default values of the config
            self.config.update(config)
        # TODO: implement other policy storage alternatives
        #if self.config["policy_storage"] == "db":
        #    self.prp = DbPolicyRetrievalPoint(self.config["policy_storage_path"])
        #else:
        self.prp = FilePolicyRetrievalPoint(self.config["policy_storage_path"])
        # TODO: write AttributeFinder()
        #self.pip = AttributeFinder()

    def authorize(self, request):
        if "action" in request and "requires" in request["action"]:
            requires = request["action"]["requires"]
            _log.debug("PolicyDecisionPoint: Requires %s" % requires)
            if len(requires) > 1:
                decisions = []
                # Create one request for each requirement
                for req in requires:
                    requirement_request = request.copy()
                    requirement_request["action"]["requires"] = [req]
                    decisions.append(self.combined_policy_decision(requirement_request))
                # If the policy decisions for all requirements are the same, respond with that decision
                if all(x == decisions[0] for x in decisions):
                    return self.create_response(decisions[0])
                else:
                    return self.create_response("indeterminate")
        return self.create_response(self.combined_policy_decision(request))

    def combined_policy_decision(self, request):
        # Get policies from PRP (Policy Retrieval Point). Policy needs to be signed if external PRP is used.
        # In most cases the PRP and the PDP will be located on the same physical machine.
        # If database is used: policies are indexed based on their Target constraints
        policy_decisions = []
        try:
            policies = self.prp.get_policies(self.config["policy_name_pattern"])
            for policy in policies: 
                # Check policy target
                if "target" not in policy or self.target_matches(policy["target"], request):
                    decision = self.policy_decision(policy, request)
                    if ((decision == "permit" and self.config["policy_combining"] == "permit_overrides") or 
                      (decision == "deny" and self.config["policy_combining"] == "deny_overrides")):
                        return decision  # Stop checking further policies
                    policy_decisions.append(decision)
            if "indeterminate" in policy_decisions:
                return "indeterminate"
            if not all(x == "not_applicable" for x in policy_decisions):
                return "deny" if self.config["policy_combining"] == "permit_overrides" else "permit"
            else:
                return "not_applicable"
        except:
            return "indeterminate"

    def create_response(self, decision):
        # The following JSON code is inspired by the XACML JSON Profile but has been simplified (to be more compact).
        # TODO: include more information to make it possible to send the response to other nodes within the domain when an actor is migrated
        return {
            "decision": decision
        }

    def target_matches(self, target, request):     
        for attribute_type in target:
            for attribute in target[attribute_type]:
                # Accept both single object and lists by turning single objects into a list
                try:
                    request_value = request[attribute_type][attribute]
                except KeyError:
                    return False
                    # TODO: Try to fetch missing attribute from AttributeFinder (PIP)
                    #try:
                    #    # TODO: cache this value. Same value should be used for future tests in this policy or other policies when handling this request
                    #    request_value = self.pip.get_attribute_value(attribute_type, attribute)
                    #except KeyError:
                    #    _log.debug("PolicyDecisionPoint: Attribute not found: %s %s" % (attribute_type, attribute))
                    #    return False # Or indeterminate (if MustBePresent is True and none of the other targets return False)?
                if not isinstance(request_value, list):
                    request_value = [request_value]
                policy_value = target[attribute_type][attribute]
                if not isinstance(policy_value, list):
                    policy_value = [policy_value]
                try:
                    # If the lists contain many values, only one of the values need to match
                    # Regular expressions are allowed for strings in policies 
                    # (re.match checks for a match at the beginning of the string, $ marks the end of the string)
                    if not any([re.match(r+'$', x) for r in policy_value for x in request_value]):
                        _log.debug("PolicyDecisionPoint: Not matching: %s %s %s" % (attribute_type, attribute, policy_value))
                        return False
                except TypeError:  # If the value is not a string
                    if set(request_value).isdisjoint(policy_value):
                        _log.debug("PolicyDecisionPoint: Not matching: %s %s %s" % (attribute_type, attribute, policy_value))
                        return False
        return True

    def policy_decision(self, policy, request):
        rule_decisions = []
        for rule in policy["rules"]:
            # Check rule target
            if "target" not in rule or self.target_matches(rule["target"], request):
                effect = self.rule_decision(rule, request)
                if ((effect == "permit" and policy["rule_combining"] == "permit_overrides") or 
                  (effect == "deny" and policy["rule_combining"] == "deny_overrides")):
                    return effect
                rule_decisions.append(effect)
        if "indeterminate" in rule_decisions:
            return "indeterminate"
        if not all(x == "not_applicable" for x in rule_decisions):
            return "deny" if policy["rule_combining"] == "permit_overrides" else "permit"
        else:
            return "not_applicable"

    def rule_decision(self, rule, request):
        if "condition" in rule:
            try:
                args = []
                for attribute in rule["condition"]["attributes"]:
                    if isinstance(attribute, dict):  # Contains another function
                        args.append(self.evaluate_function(attribute["function"], attribute["attributes"], request))
                    else:
                        args.append(attribute)
                rule_satisfied = self.evaluate_function(rule["condition"]["function"], args, request)
                if rule_satisfied:
                    return rule["effect"]
                else:
                    return "not_applicable"
            except:
                return "indeterminate"
        else:
            return rule["effect"]
        
    def evaluate_function(self, func, args, request):
        # Check each function argument
        for index, arg in enumerate(args):
            if isinstance(arg, basestring):
                if arg.startswith("attr"):
                    # Get value from request if the argument starts with "attr"
                    path = arg.split(":")
                    try:
                        args[index] = request[path[1]][path[2]]  # path[0] is "attr"
                    except KeyError:
                        return False
                        # TODO: check in attribute cache first
                        # TODO: Try to fetch missing attribute from AttributeFinder (PIP)
                        # args[index] = self.pip.get_attribute_value(path[1], path[2])
                # Accept both strings and lists by turning strings into single element lists
                if isinstance(args[index], basestring):
                    args[index] = [args[index]]
        if func == "equal":
            try:
                # If the lists contain many values, only one of the values need to match
                # Regular expressions (has to be args[1]) are allowed for strings in policies
                # (re.match checks for a match at the beginning of the string, $ marks the end of the string)
                return any([re.match(r+'$', x) for r in args[1] for x in args[0]])
            except TypeError:  # If the value is not a string
                return not set(args[0]).isdisjoint(args[1])
        elif func == "not_equal":
            try:
                # If the lists contain many values, only one of the values need to match
                # Regular expressions (has to be args[1]) are allowed for strings in policies
                # (re.match checks for a match at the beginning of the string, $ marks the end of the string)
                return not any([re.match(r+'$', x) for r in args[1] for x in args[0]])
            except TypeError:  # If the value is not a string
                return set(args[0]).isdisjoint(args[1])
        elif func == "and":
            return all(args)  # True if all elements of the list are True
        elif func == "or":
            return True in args  # True if any True exists in the list
        elif func == "less_than_or_equal":
            # FIXME: What should happen here if request_value and/or policy_value is a list?
            # FIXME: compare date/time should be supported. Enough with string comparison if standard date/time format is used?
            return args[0] <= args[1]
        elif func == "greater_than_or_equal":
            # FIXME: What should happen here if request_value and/or policy_value is a list?
            # FIXME: compare date/time should be supported. Enough with string comparison if standard date/time format is used?
            return args[0] >= args[1]