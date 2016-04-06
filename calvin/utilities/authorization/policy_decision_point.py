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
from calvin.utilities.authorization.policy_information_point import PolicyInformationPoint

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class PolicyDecisionPoint(object):

    def __init__(self, config=None):
        # Default config
        self.config = {
            "policy_combining": "permit_overrides",
            "policy_storage": "files",
            "policy_storage_path": "~/.calvin/security/policies",
            "policy_name_pattern": "*"
        }
        if config is not None:
            # Change some of the default values of the config.
            self.config.update(config)
        # TODO: implement other policy storage alternatives
        # if self.config["policy_storage"] == "db":
        #     self.prp = DbPolicyRetrievalPoint(self.config["policy_storage_path"])
        # else:
        self.prp = FilePolicyRetrievalPoint(self.config["policy_storage_path"])
        self.pip = PolicyInformationPoint()
        self.registered_nodes = {}

    def register_node(self, node_id, node_attributes):
        """
        Register node attributes for authorization.

        Node attributes example:
        {
            "node_name.name": "testNode",
            "node_name.organization": "com.ericsson",
            "owner.organization": "com.ericsson",
            "address.country": "SE"
        }
        """
        self.registered_nodes[node_id] = node_attributes

    def authorize(self, request):
        """
        Use policies to return access decision for the request.

        The request and response format is inspired by the XACML JSON Profile 
        but has been simplified to be more compact.

        Request (example):
        {
            "subject": {
                "user": ["user1"],
                "actor_signer": ["signer"]
            },
            "action": {
                "requires": ["runtime", "calvinsys.events.timer"]
            },
            "resource": {
                "node_id": "a77c0687-dce8-496f-8d81-571333be6116"
            }
        }

        Response (example):
        {
            "decision": "permit",
            "obligations": [
                {
                    "id": "time_range",
                    "attributes": {
                        "start_time": "09:00",
                        "end_time": "17:00"
                    }
                }
            ]
        }
        """
        _log.info("Authorization request received: %s" % request)
        if "resource" in request and "node_id" in request["resource"]:
            try:
                request["resource"] = self.registered_nodes[request["resource"]["node_id"]]
            except Exception:
                request["resource"] = {}
        if "action" in request and "requires" in request["action"]:
            requires = request["action"]["requires"]
            _log.debug("PolicyDecisionPoint: Requires %s" % requires)
            if len(requires) > 1:
                decisions = []
                obligations = []
                # Create one request for each requirement.
                for req in requires:
                    requirement_request = request.copy()
                    requirement_request["action"]["requires"] = [req]
                    policy_decision, policy_obligations = self.combined_policy_decision(requirement_request)
                    decisions.append(policy_decision)
                    if policy_obligations:
                        obligations.append(policy_obligations)
                # If the policy decisions for all requirements are the same, respond with that decision.
                if all(x == decisions[0] for x in decisions):
                    return self.create_response(decisions[0], obligations)
                else:
                    return self.create_response("indeterminate", [])
        return self.create_response(*self.combined_policy_decision(request))

    def combined_policy_decision(self, request):
        """
        Return (decision, obligations) for request using policy combining algorithm in config.

        Possible decisions: permit, deny, indeterminate, not_applicable

        Policy format (example):
        {
            "id": "policy1",
            "description": "Security policy for user1/user2 with 
                            actor signed by 'signer'",
            "rule_combining": "permit_overrides",
            "target": {
                "subject": {
                    "user": ["user1", "user2"],
                    "actor_signer": "signer"
                }
            },
            "rules": [
                {
                    "id": "policy1_rule1",
                    "description": "Permit access to 'calvinsys.events.timer', 
                                    'calvinsys.io.*' and 'runtime' between 
                                    09:00 and 17:00 if condition is true",
                    "effect": "permit",
                    "target": {
                        "action": {
                            "requires": ["calvinsys.events.timer", 
                                         "calvinsys.io.*", "runtime"]
                        }
                    },
                    "condition": {
                        "function": "and",
                        "attributes": [
                            {
                                "function": "equal",
                                "attributes": ["attr:resource:address.country", 
                                               ["SE", "DK"]]
                            },
                            {
                                "function": "greater_than_or_equal",
                                "attributes": ["attr:environment:current_date", 
                                               "2016-03-04"]
                            } 
                        ]
                    },
                    "obligations": [
                        {
                            "id": "time_range",
                            "attributes": {
                                "start_time": "09:00",
                                "end_time": "17:00"
                            }
                        }
                    ]
                }
            ]
        }
        """
        policy_decisions = []
        policy_obligations = []
        try:
            # Get policies from PRP (Policy Retrieval Point). 
            # TODO: policy needs to be signed if external PRP is used.
            # In most cases the PRP and the PDP will be located on the same physical machine.
            # TODO: if database is used, policies should be indexed based on their Target constraints
            policies = self.prp.get_policies(self.config["policy_name_pattern"])
            for policy_id in policies: 
                policy = policies[policy_id]
                # Check if policy target matches (policy without target matches everything).
                if "target" not in policy or self.target_matches(policy["target"], request):
                    # Get a policy decision if target matches.
                    decision, obligations = self.policy_decision(policy, request)
                    if ((decision == "permit" and not obligations and self.config["policy_combining"] == "permit_overrides") or 
                      (decision == "deny" and self.config["policy_combining"] == "deny_overrides")):
                        # Stop checking further rules.
                        # If "permit" with obligations, continue since "permit" without obligations may be found.
                        return (decision, [])
                    policy_decisions.append(decision)
                    policy_obligations += obligations
            if "indeterminate" in policy_decisions:
                return ("indeterminate", [])
            if not all(x == "not_applicable" for x in policy_decisions):
                if self.config["policy_combining"] == "deny_overrides" or policy_obligations:
                    return ("permit", policy_obligations)
                else:
                    return ("deny", [])
            else:
                return ("not_applicable", [])
        except Exception:
            return ("indeterminate", [])

    def create_response(self, decision, obligations):
        """Return authorization response including decision and obligations."""
        # TODO: include more information to make it possible to send the response to other nodes within the domain 
        # when an actor is migrated, e.g. node IDs for which the decision is valid.
        response = {}
        response["decision"] = decision
        if obligations:
            response["obligations"] = obligations
        return response

    def target_matches(self, target, request):
        """Return True if policy target matches request, else False."""
        for attribute_type in target:
            for attribute in target[attribute_type]:
                try:
                    request_value = request[attribute_type][attribute]
                except KeyError:
                    try:
                        # Try to fetch missing attribute from Policy Information Point (PIP).
                        # TODO: cache this value. 
                        # Same value should be used for future tests in this policy or other policies when handling this request.
                        request_value = self.pip.get_attribute_value(attribute_type, attribute)
                    except KeyError:
                        _log.debug("PolicyDecisionPoint: Attribute not found: %s %s" % (attribute_type, attribute))
                        return False  # Or 'indeterminate' (if MustBePresent is True and none of the other targets return False)?
                # Accept both single object and lists by turning single objects into a list.
                if not isinstance(request_value, list):
                    request_value = [request_value]
                policy_value = target[attribute_type][attribute]
                if not isinstance(policy_value, list):
                    policy_value = [policy_value]
                try:
                    # If the lists contain many values, only one of the values need to match.
                    # Regular expressions are allowed for strings in policies 
                    # (re.match checks for a match at the beginning of the string, $ marks the end of the string).
                    if not any([re.match(r+'$', x) for r in policy_value for x in request_value]):
                        _log.debug("PolicyDecisionPoint: Not matching: %s %s %s" % (attribute_type, attribute, policy_value))
                        return False
                except TypeError:  # If the value is not a string
                    if set(request_value).isdisjoint(policy_value):
                        _log.debug("PolicyDecisionPoint: Not matching: %s %s %s" % (attribute_type, attribute, policy_value))
                        return False
        # True is returned if every attribute in the policy target matches the corresponding request attribute.
        return True

    def policy_decision(self, policy, request):
        """Use policy to return (access decision, obligations) for the request."""
        rule_decisions = []
        rule_obligations = []
        for rule in policy["rules"]:
            # Check if rule target matches (rule without target matches everything).
            if "target" not in rule or self.target_matches(rule["target"], request):
                # Get a rule decision if target matches.
                decision, obligations = self.rule_decision(rule, request)
                if ((decision == "permit" and not obligations and policy["rule_combining"] == "permit_overrides") or 
                  (decision == "deny" and policy["rule_combining"] == "deny_overrides")):
                    # Stop checking further rules.
                    # If "permit" with obligations, continue since "permit" without obligations may be found.
                    return (decision, [])
                rule_decisions.append(decision)
                if decision == "permit" and obligations:
                    # Obligations are only accepted if the decision is "permit".
                    rule_obligations += obligations
        if "indeterminate" in rule_decisions:
            return ("indeterminate", [])
        if not all(x == "not_applicable" for x in rule_decisions):
            if policy["rule_combining"] == "deny_overrides" or rule_obligations:
                return ("permit", rule_obligations)
            else:
                return ("deny", [])
        else:
            return ("not_applicable", [])

    def rule_decision(self, rule, request):
        """Return (rule decision, obligations) for the request"""
        # Check condition if it exists.
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
                    return (rule["effect"], rule.get("obligations", []))
                else:
                    return ("not_applicable", [])
            except Exception:
                return ("indeterminate", [])
        else:
            # If no condition in the rule, return the rule effect directly.
            return (rule["effect"], rule.get("obligations", []))
        
    def evaluate_function(self, func, args, request):
        """
        Return result of function func with arguments args.

        If a function argument starts with 'attr', e.g. 'attr:resource:address.country',
        the value is retrieved from the request or the Policy Information Point.
        """
        # Check each function argument
        for index, arg in enumerate(args):
            if isinstance(arg, basestring):
                if arg.startswith("attr"):
                    # Get value from request if the argument starts with "attr".
                    path = arg.split(":")
                    try:
                        args[index] = request[path[1]][path[2]]  # path[0] is "attr"
                    except KeyError:
                        # TODO: check in attribute cache first
                        try:
                            # Try to fetch missing attribute from Policy Information Point (PIP).
                            # TODO: cache this value. 
                            # Same value should be used for future tests in this policy or other policies when handling this request
                            args[index] = self.pip.get_attribute_value(path[1], path[2])
                        except KeyError:
                            _log.debug("PolicyDecisionPoint: Attribute not found: %s %s" % (path[1], path[2]))
                            return False
                # Accept both strings and lists by turning strings into single element lists.
                if isinstance(args[index], basestring):
                    args[index] = [args[index]]
        if func == "equal":
            try:
                # If the lists contain many values, only one of the values need to match.
                # Regular expressions (has to be args[1]) are allowed for strings in policies
                # (re.match checks for a match at the beginning of the string, $ marks the end of the string).
                return any([re.match(r+'$', x) for r in args[1] for x in args[0]])
            except TypeError:  # If the value is not a string
                return not set(args[0]).isdisjoint(args[1])
        elif func == "not_equal":
            try:
                # If the lists contain many values, only one of the values need to match.
                # Regular expressions (has to be args[1]) are allowed for strings in policies
                # (re.match checks for a match at the beginning of the string, $ marks the end of the string).
                return not any([re.match(r+'$', x) for r in args[1] for x in args[0]])
            except TypeError:  # If the value is not a string
                return set(args[0]).isdisjoint(args[1])
        elif func == "and":
            return all(args)  # True if all elements of the list are True
        elif func == "or":
            return True in args  # True if any True exists in the list
        elif func == "less_than_or_equal":
            return args[0] <= args[1]
        elif func == "greater_than_or_equal":
            return args[0] >= args[1]