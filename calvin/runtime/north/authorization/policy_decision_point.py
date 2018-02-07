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
import os
from calvin.runtime.north.authorization.policy_information_point import PolicyInformationPoint
from calvin.runtime.north.plugins.authorization_checks import check_authorization_plugin_list
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class PolicyDecisionPoint(object):

    def __init__(self, node, config=None):
        # Default config
        self.config = {
            "policy_combining": "permit_overrides",
            "policy_storage": "files",
            "policy_storage_path": os.path.join(os.path.expanduser("~"), ".calvin", "security", "policies"),
            "policy_name_pattern": "*"
        }
        if config is not None:
            # Change some of the default values of the config.
            self.config.update(config)
        self.node = node
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
        _log.debug("Register node:\n\tnode_id={}\n\tnode_attributes={}".format(node_id, node_attributes))
        self.registered_nodes[node_id] = node_attributes

    def authorize(self, request, callback):
        """
        Use policies to return access decision for the request.

        The request and response format is inspired by the XACML JSON Profile
        but has been simplified to be more compact.

        Request (example):
        {
            "subject": {
                "first_name": "Tomas",
                "last_name": "Nilsson",
                "actor_signer": "signer"
            },
            "action": {
                "requires": ["runtime", "sys.timer.repeating"]
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
        alternatevly for control interface:
        {
            "subject": {
                "first_name": "Tomas",
                "last_name": "Nilsson",
                "control_interface": "handle_deploy"
            },
            "resource": {
                "node_id": "a77c0687-dce8-496f-8d81-571333be6116"
            }
        }

        """
        _log.debug("Authorization request received:\n\t request={}\n\tcallback={}".format(request, callback))
        # Create a new PolicyInformationPoint instance for every request.
        pip = PolicyInformationPoint(self.node, request)
        if ("subject" in request) and ("actorstore_signature" in request["subject"]):
            try:
                # Get actor_desc from storage if actorstore_signature is included in request.
                pip.actor_desc_lookup(request["subject"]["actorstore_signature"],
                                      callback=CalvinCB(self._authorize_cont, request, callback=callback))
            except Exception as err:
                _log.error("authorize, failed to lookup actor_desc, err={}".format(err))
                self._authorize_cont(request, pip, callback)
        else:
            self._authorize_cont(request, pip, callback)
            # Wait for PolicyInformationPoint to be ready, then continue with authorization.

    def _authorize_cont(self, request, pip, callback):
        _log.debug("_authorize_cont: \n\trequest={}\n\tpip={}\n\tcallback={}".format(request, pip, callback))
        try:
            node_id = request["resource"]["node_id"]
            request["resource"] = self.registered_nodes[node_id]
            request["resource"]["node_id"] = node_id
        except Exception as err:
            _log.debug("_authorize_cont: node_id is not registered at this authorization server\n\tregistered_nodes={}\n\tnode_id={}\n\terr={}".format(self.registered_nodes, node_id, err))
            pass
        if ("action" in request) and ("requires" in request["action"]):
            requires = request["action"]["requires"]
        else:
            try:
                # Try to fetch missing attribute from Policy Information Point (PIP).
                requires = pip.get_attribute_value("action", "requires")
                request["action"] = {
                    "requires": requires
                }
            except Exception as err:
                _log.debug("_authorize_cont, failed to fetch missing attribute from PIP, err={}".format(err))
                requires = None
        if requires is not None and len(requires) > 1:
            decisions = []
            obligations = []
            # Create one request for each requirement.
            _log.debug("_authorize_cont, create one request for each requirement")
            for req in requires:
                _log.debug("_authorize_cont req \n\treq={}".format(req))
                requirement_request = request.copy()
                requirement_request["action"]["requires"] = [req]
                policy_decision, policy_obligations = self.combined_policy_decision(requirement_request, pip)
                decisions.append(policy_decision)
                if policy_obligations:
                    obligations.append(policy_obligations)
            # If the policy decisions for all requirements are the same, respond with that decision.
            if all(x == decisions[0] for x in decisions):
                callback(authz_response=self.create_response(decisions[0], obligations))
                return
            else:
                callback(authz_response=self.create_response("indeterminate", []))
                return
        callback(authz_response=self.create_response(*self.combined_policy_decision(request, pip)))

    def combined_policy_decision(self, request, pip):
        """
        Return (decision, obligations) for request using policy combining algorithm in config.

        Possible decisions: permit, deny, indeterminate, not_applicable

        Policy format (example):
        {
            "id": "policy1",
            "description": "Security policy for user Tomas or Gustav
                            Nilsson with actor signed by signer.",
            "rule_combining": "permit_overrides",
            "target": {
                "subject": {
                    "first_name": ["Tomas", "Gustav"],
                    "last_name": "Nilsson",
                    "actor_signer": "signer"
                }
            },
            "rules": [
                {
                    "id": "policy1_rule1",
                    "description": "Permit access to 'sys.timer.repeating',
                                    'calvinsys.io.*' and 'runtime' between
                                    09:00 and 17:00 if condition is true.",
                    "effect": "permit",
                    "target": {
                        "action": {
                            "requires": ["sys.timer.repeating", 
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
        _log.debug("\n********************************************************\n"
                   "combined_policy_decision: \n\trequest={}".format(request))
        policy_decisions = []
        policy_obligations = []
        try:
            try:
                # Get policies from PRP (Policy Retrieval Point).
                policies = self.node.authorization.prp.get_policies(self.config["policy_name_pattern"])
            except Exception as err:
                _log.error("Failed to get policies from PRP, exc={}".format(err))
                raise
            _log.debug("For each policy, check result")
            for policy_id in policies:
                policy = policies[policy_id]
                _log.debug("\n\n\nLet's check a policy:\n\tpolicy_id={}\n\tpolicy={}".format(policy_id, policy))
                # Check if policy target matches (policy without target matches everything).
                _log.debug("Check if policy target matches (policy without target matches everything)")
                if "target" not in policy or self.target_matches(policy["target"], request, pip):
                    if 'id' in policy:
                        _log.debug("Policy target matches for policy_id={}".format(policy['id']))
                    else:
                        _log.debug("Policy target matches for policy={}".format(policy))
                    # Get a policy decision if target matches.
                    try:
                        decision, obligations = self.policy_decision(policy, request, pip)
                    except Exception as err:
                        _log.error("Failed to get policy decision, err={}".format(err))
                        raise
                    _log.debug("Policy decision\n\tdecision={}\n\tobligations={}\n".format(decision, obligations))
                    if ((decision == "permit" and not obligations and self.config["policy_combining"] == "permit_overrides") or
                      (decision == "deny" and self.config["policy_combining"] == "deny_overrides")):
                        # Stop checking further rules.
                        # If "permit" with obligations, continue since "permit" without obligations may be found.
                        _log.debug("Stop checking futher rules:\n\tpolicy_decisions={}".format(decision))
                        return (decision, [])
                    policy_decisions.append(decision)
                    policy_obligations += obligations
            _log.debug("combined_policy_decision, we now have all decsions"
                       "\n\tpolicy_decisions={}"
                       "\n\tpolicy_obligations={}".format(policy_decisions, policy_obligations))
            if "indeterminate" in policy_decisions:
                _log.debug("combined_policy_decision  Indeterminate in policy_decisions,  so let's deny")
                return ("indeterminate", [])
            if not all(x == "not_applicable" for x in policy_decisions):
                if self.config["policy_combining"] == "deny_overrides" or policy_obligations:
                    _log.debug("combined_policy_decision At least one policy_decision not not_applicable, deny_overrides or policy_obligations, so let's permit")
                    return ("permit", policy_obligations)
                else:
                    _log.debug("combined_policy_decision  At least one policy_decision not not_applicable, permit_overrides or not policy_obligations, so let's deny:\n\tpolicy_decisions={}".format(policy_decisions))
                    return ("deny", [])
            else:
                _log.debug("combined_policy_decision  All policy_decision not_applicable,  so let's deny")
                return ("not_applicable", [])
        except Exception as err:
            _log.error("Error, exc={}".format(err))
            return ("indeterminate", [])

    def create_response(self, decision, obligations):
        """Return authorization response including decision and obligations."""
        response = {}
        response["decision"] = decision
        if obligations:
            response["obligations"] = obligations
        return response

    def target_matches(self, target, request, pip):
        """Return True if policy target matches request, else False."""
#        _log.debug("target_matches: \n\ttarget={}\n\trequest={}".format(target,request))
        for attribute_type in target:
#            _log.debug("target_matches::attribute_type\n\tattribute_type={}".format(attribute_type))
            for attribute in target[attribute_type]:
                try:
                    request_value = request[attribute_type][attribute]
#                    _log.debug("target_matches::request_value={}".format(request_value))
                except KeyError:
#                    _log.debug("target_matches: attribute not in request, let's also try PIP")
                    try:
                        # Try to fetch missing attribute from Policy Information Point (PIP).
                        request_value = pip.get_attribute_value(attribute_type, attribute)
                    except Exception as err:
#                        _log.debug("target_matches: Attribute not in request and not found at PIP, return False:"
#                                   "\n\tattribute_type={}"
#                                   "\n\tattribute={}"
#                                   "\n\terr={}".format(attribute_type, attribute, err))
                        return False  # Or 'indeterminate' (if MustBePresent is True and none of the other targets return False)?
                # Accept both single object and lists by turning single objects into a list.
#                _log.info("target_matches, we have a request_value \n\trequest_value={}".format(request_value))
                if not isinstance(request_value, list):
                    request_value = [request_value]
                try:
                    policy_value = target[attribute_type][attribute]
                except Exception as err:
#                    _log.error("Failed to parse policy_value"
#                               "\n\ttarget={}"
#                               "\n\tattribute_type={}"
#                               "\n\tattribute={}".format(target, attribute_type, attribute))
                    pass
                if not isinstance(policy_value, list):
                    policy_value = [policy_value]
                try:
                    # If the lists contain many values, only one of the values need to match.
                    # Regular expressions are allowed for strings in policies
                    # (re.match checks for a match at the beginning of the string, $ marks the end of the string).
                    if not any([re.match(r+'$', x) for r in policy_value for x in request_value]):
                        _log.debug("No attributes are matching: %s %s %s" % (attribute_type, attribute, policy_value))
                        return False
                except TypeError:  # If the value is not a string
                    if set(request_value).isdisjoint(policy_value):
                        _log.debug("No attributes values are matching: %s %s %s" % (attribute_type, attribute, policy_value))
                        return False
        # True is returned if every attribute in the policy target matches the corresponding request attribute.
#        _log.debug("target_matches: will return True")
        return True

    def policy_decision(self, policy, request, pip):
        """Use policy to return (access decision, obligations) for the request."""
        rule_decisions = []
        rule_obligations = []
        if not 'rules' in policy:
            _log.error("No rules in policy")
            raise Exception("No rules in policy")
        for rule in policy["rules"]:
            _log.debug("\n-----------\n"
                       "Check if rule target matches (rule without target matches everything)\n\trule={}".format(rule))
            # Check if rule target matches (rule without target matches everything).
            try:
                self.target_matches(rule["target"], request, pip)
            except Exception as err:
                _log.error("Target matches failed, err={}".format(err))
            if ("target" not in rule) or (self.target_matches(rule["target"], request, pip)):
                # Get a rule decision if target matches.
                _log.debug("Rule target matched, let's get a rule decision")
                decision, obligations = self.rule_decision(rule, request, pip)
                _log.debug("Rule decison ready:"
                           "\n\tdecisons={}"
                           "\n\tobligations={}".format(decision, obligations))
                if not "rule_combining" in policy:
                    _log.error("No rule_combining in policy")
                    raise Exception("No rule_combining in policy")
                if ((decision == "permit" and not obligations and policy["rule_combining"] == "permit_overrides") or
                  (decision == "deny" and policy["rule_combining"] == "deny_overrides")):
                    # Stop checking further rules.
                    # If "permit" with obligations, continue since "permit" without obligations may be found.
                    _log.debug("policy_decision {} and {}".format(decision, policy["rule_combining"]))
                    return (decision, [])
                rule_decisions.append(decision)
                if decision == "permit" and obligations:
                    _log.debug("Rule says permit with obligations")
                    # Obligations are only accepted if the decision is "permit".
                    rule_obligations += obligations
            else:
                _log.debug("Rule_target did not match")
        _log.debug("Rule_decisions\n\trule_decisions={}".format(rule_decisions))
        if "indeterminate" in rule_decisions:
            _log.debug("Indeterminate in rule_decisions, policy={},  request={}".format(policy, request))
            return ("indeterminate", [])
        if not all(x == "not_applicable" for x in rule_decisions):
            if policy["rule_combining"] == "deny_overrides" or rule_obligations:
                _log.debug("At least one rule_decision not not_applicable, deny_overrides or rule_obligations, so let's permit\n\tpolicy={}\n\trequest={}".format(policy, request))
                return ("permit", rule_obligations)
            else:
                _log.debug("At least on rule_decision not not_applicable, permit_overrides or not rule_obligations, so let's deny\n\tpolicy={}\n\trequest={}".format(policy, request))
                return ("deny", [])
        else:
            _log.debug("All rule_decisions not_applicable, so let's deny\n\tpolicy={}\n\trequest={}".format(policy, request))
            return ("not_applicable", [])

    def rule_decision(self, rule, request, pip):
        """Return (rule decision, obligations) for the request"""
        # Check condition if it exists.
        if "condition" in rule:
            _log.debug("There are conditions in the rule, let's check if they are fulfilled")
            try:
                args = []
                for attribute in rule["condition"]["attributes"]:
                    if isinstance(attribute, dict):  # Contains another function
                        args.append(self.evaluate_function(attribute["function"],
                                    attribute["attributes"], request, pip))
                    else:
                        args.append(attribute)
                rule_satisfied = self.evaluate_function(rule["condition"]["function"], args, request, pip)
                if rule_satisfied:
                    _log.debug("Rule satisfied")
                    return (rule["effect"], rule.get("obligations", []))
                else:
                    _log.debug("Rule NOT satisfied\n\trule={}\n\trequest={}".format(rule, request))
                    return ("not_applicable", [])
            except Exception as err:
                _log.exception("Rule decision exception, exc={}".format(err))
                return ("indeterminate", [])
        else:
            # If no condition in the rule, return the rule effect directly.
            _log.debug("No condition in rule, return effect directly\n\trule id={}\n\trule effect={}\n\trule obligations={}".format(rule["id"],rule["effect"], rule.get("obligations", [])))
            return (rule["effect"], rule.get("obligations", []))

    def evaluate_function(self, func, args, request, pip):
        """
        Return result of function func with arguments args.

        If a function argument starts with 'attr', e.g. 'attr:resource:address.country',
        the value is retrieved from the request or the Policy Information Point.
        """
        args = args[:]  # Copy list to prevent editing original list.

        # Check each function argument
        for index, arg in enumerate(args):
            if isinstance(arg, basestring):
                if arg.startswith("attr"):
                    # Get value from request if the argument starts with "attr".
                    path = arg.split(":")
                    try:
                        args[index] = request[path[1]][path[2]]  # path[0] is "attr"
                    except KeyError:
                        try:
                            # Try to fetch missing attribute from Policy Information Point (PIP).
                            args[index] = pip.get_attribute_value(path[1], path[2])
                        except Exception as err:
                            _log.debug("evaluate_function: Attribute not found: %s %s, err=%s" % (path[1], path[2], err))
                            return False
            if func not in ["and", "or"]:
                if isinstance(args[index], list):
                    # Handle everything as strings.
                    args[index] = [self._to_string(arg) for arg in args[index]]
                else:
                    # Accept both single object and lists by turning single objects into a list.
                    # Handle all objects as strings.
                    args[index] = [self._to_string(args[index])]
        if func == "equal":
            # If the lists contain many values, only one of the values need to match.
            # Regular expressions (has to be args[1]) are allowed for strings in policies
            # (re.match checks for a match at the beginning of the string, $ marks the end of the string).
            return any([re.match(r+'$', x) for r in args[1] for x in args[0]])
        elif func == "not_equal":
            # If the lists contain many values, only one of the values need to match.
            # Regular expressions (has to be args[1]) are allowed for strings in policies
            # (re.match checks for a match at the beginning of the string, $ marks the end of the string).
            return not any([re.match(r+'$', x) for r in args[1] for x in args[0]])
        elif func == "and":
            return all(args)  # True if all elements of the list are True
        elif func == "or":
            return True in args  # True if any True exists in the list
        elif func == "less_than_or_equal":
            return args[0] <= args[1]
        elif func == "greater_than_or_equal":
            return args[0] >= args[1]

    def _to_string(self, value):
        if isinstance(value, str):
            return value.decode("UTF-8")
        elif isinstance(value, unicode):
            return value
        else:
            return str(value).decode("UTF-8")

    def runtime_search(self, request, runtime_whitelist, callback):
        """
        Search for runtime where the decision for the request is 'permit'.

        Request (example):
        {
            "subject": {
                "user": ["user1"],
                "actorstore_signature: "84d582e5e5c3a95bf20849693d7758370fc724809ffdcb0a4a5be1e96673ac21"
            }
        }

        Response contains (node_id, authorization response) for the first match
        or None if no runtime is found.
        """
        _log.debug("runtime_search \n\trequest={}\n\truntime_whitelist={}\n\tcallback={}".format(request, runtime_whitelist, callback))
        # TODO: translate subject attributes when crossing domain.
        # Other runtime might have other actor_signer and other requires list.
        forbidden_keys = [("subject", "actor_signer"), ("action", "requires")]
        for key in forbidden_keys:
            try:
                del request[key[0]][key[1]]
            except Exception as err:
                _log.debug("runtime_search: could not delete key from request (hopefully because it was not in the request):\n\trequest={}\n\tkey={}\n\terr={}".format(request,key, err))
                pass
        if not runtime_whitelist:
            # Use all registered nodes as possible nodes when no whitelist is provided.
            runtime_whitelist = self.registered_nodes
        possible_nodes = [node for node in self.registered_nodes if node in runtime_whitelist]
        self._runtime_search_authorize(request, possible_nodes, callback)

    def _runtime_search_authorize(self, request, possible_nodes, callback, counter=0):
        _log.debug("_runtime_search_authorize:\n\trequest={}\n\tpossible_nodes={}\n\tcallback={}\n\tcounter={}".format(request, possible_nodes, callback, counter))
        node_id = possible_nodes[counter]
        node_request = request.copy()
        node_request["resource"] = {
            "node_id": node_id
        }
        self.authorize(node_request,
                       callback=CalvinCB(self._runtime_search_cont, node_id, callback=callback,
                                         request=request, possible_nodes=possible_nodes, counter=counter))

    def _runtime_search_cont(self, node_id, authz_response, callback, request, possible_nodes, counter):
        _log.debug("_runtime_search_cont:\n\tnode_id={}\n\tauthz_response={}\n\tcallback={}\n\trequest={}\n\tpossible_nodes={}\n\tcounter={}".format(node_id, authz_response, callback, request, possible_nodes, counter))
        if authz_response["decision"] == "permit":
            valid = True
            if authz_response.get("obligations", []):
                # Look at obligations to check if authorization decision is valid right now.
                if any(isinstance(elem, list) for elem in authz_response["obligations"]):
                    # If list of lists, True must be found in each list.
                    for plugin_list in authz_response["obligations"]:
                        if not check_authorization_plugin_list(plugin_list):
                            valid = False
                            break
                else:
                    if not check_authorization_plugin_list(authz_response["obligations"]):
                        valid = False
            if valid:
                callback(search_result=(node_id, authz_response))
                return
        counter += 1
        if counter < len(possible_nodes):
            # Continue searching
            self._runtime_search_authorize(request, possible_nodes, callback, counter)
            return
        else:
            _log.info("Did not find any runtime where actor is allowed to execute")
            callback(search_result=None)
