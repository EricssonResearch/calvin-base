# -*- coding: utf-8 -*-

# Copyright (c) 2018 Ericsson AB
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

import json
from calvin.requests import calvinresponse
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.north.control_apis.routes import handler
from calvin.runtime.north.control_apis.authentication import authentication_decorator

_log = get_logger(__name__)

# No authentication decorator, this is called by the runtimes when deployed
# without a certificate
@handler(method="POST", path="/certificate_authority/certificate_signing_request")
def handle_post_certificate_signing_request(self, handle, connection, match, data, hdr):
    """
    POST /certificate_authority/certificate_signing_request
    Send CSR to CA, that creates a x509 certificate and returns it
    Response status code: OK or INTERNAL_ERROR
    Response:
    {"certificate":<value>}
    """
    try:
        jsondata = json.loads(data)
        csr = jsondata["csr"]
        enrollment_password = jsondata["enrollment_password"]
        cert = self.node.certificate_authority.sign_csr(csr, enrollment_password)
        status = calvinresponse.OK
    except:
        _log.exception("handle_post_certificate_signing_request")
        status = calvinresponse.INTERNAL_ERROR
    self.send_response(handle, connection, json.dumps({"certificate": cert}) if status == calvinresponse.OK else None,
                       status=status)

#Only authorized users, e.g., an admin, should be allowed to query certificate enrollment passwords
# from the CA runtime
@handler(method="GET", path="/certificate_authority/certificate_enrollment_password/{path}")
@authentication_decorator
def handle_get_certificate_enrollment_password(self, handle, connection, match, data, hdr):
    """
    GET /certiticate_authority/certificate_enrollment_password/{node_name}
    Request a password to be later user as authorization for the Certificate Signing Request from the runtime
    Response status code: OK or INTERNAL_ERROR
    Response:
    {"enrollment_password":<value>}
    """
    try:
        password = self.node.certificate_authority.get_enrollment_password(node_name=match.group(1))
        status = calvinresponse.OK
    except:
        _log.exception("handle_post_certificate_enrollment_password")
        status = calvinresponse.INTERNAL_ERROR
    self.send_response(handle, connection, json.dumps({"enrollment_password": password}) if status == calvinresponse.OK else None,
                       status=status)


#Only authorized users, e.g.,an admin, should be allowed to query certificate enrollment passwords
# from the CA runtime
@handler(method="PUT", path="/certificate_authority/certificate_enrollment_password/{path}")
@authentication_decorator
def handle_edit_certificate_enrollment_password(self, handle, connection, match, data, hdr):
    """
    PUT /certiticate_authority/certificate_enrollment_password/{node_name}
    Set a password to be later user as authorization for the Certificate Signing Request from the runtime
    Body:
    {
        "value": <string>
    }
    Response status code: OK or INTERNAL_ERROR
    Response: none
    """
    try:
        password = self.node.certificate_authority.set_enrollment_password(node_name=match.group(1), password=data['enrollment_password'])
        status = calvinresponse.OK
    except:
        _log.exception("handle_post_certificate_enrollment_password")
        status = calvinresponse.INTERNAL_ERROR
    self.send_response(handle, connection, None, status=status)


@handler(method="GET", path="/authentication/users_db")
@authentication_decorator
def handle_get_authentication_users_db(self, handle, connection, match, data, hdr):
    """
    GET /authentication/users_db
    Get user database on this runtime
    Response status code: OK or INTERNAL_ERROR
    Response:
    {
        "policies": {
            <policy-id>: policy in JSON format,
            ...
        }
    }
    """

    """Get all authorization policies on this runtime"""
    try:
        users_db = self.node.authentication.arp.get_users_db()
        status = calvinresponse.OK
    except:
        _log.exception("handle_get_authentication_users_db")
        status = calvinresponse.INTERNAL_ERROR
    self.send_response(handle, connection, json.dumps({"users_db": users_db}) if status == calvinresponse.OK else None,
                       status=status)


@handler(method="PUT", path="/authentication/users_db")
@authentication_decorator
def handle_edit_authentication_users_db(self, handle, connection, match, data, hdr):
    """
    PUT /authentication/users_db
    Update user database
    Body: new policy in JSON format
    Response status code: OK, INTERNAL_ERROR or NOT_FOUND
    Response: none
    """
    if 'users_db'in data:
        try:
#            self.node.authentication.arp.update_users_db(data, match.group(1))
            self.node.authentication.arp.update_users_db(data['users_db'])
            status = calvinresponse.OK
        except IOError as err:
            _log.exception("handle_edit_authentication_users_db, err={}".format(err))
            status = calvinresponse.NOT_FOUND
        except Exception as err:
            _log.exception("handle_edit_authentication_users_db, err={}".format(err))
            status = calvinresponse.INTERNAL_ERROR
    else:
        _log.exception("handle_edit_authentication_users_db: no users_db in data\n\tdata={}".format(data))
        status = calvinresponse.NOT_FOUND
    self.send_response(handle, connection, None, status=status)


@handler(method="GET", path="/authentication/groups_db")
@authentication_decorator
def handle_get_authentication_groups_db(self, handle, connection, match, data, hdr):
    """
    GET /authentication/groups_db
    Get user database on this runtime
    Response status code: OK or INTERNAL_ERROR
    Response:
    {
        "policies": {
            <policy-id>: policy in JSON format,
            ...
        }
    }
    """
    # TODO:to be implemented
    pass

@handler(method="PUT", path="/authentication/groups_db")
@authentication_decorator
def handle_edit_authentication_groups_db(self, handle, connection, match, data, hdr):
    """
    PUT /authentication/groups_db
    Update user database
    Body: new policy in JSON format
    Response status code: OK, INTERNAL_ERROR or NOT_FOUND
    Response: none
    """
    # TODO:to be implemented
    pass


@handler(method="POST", path="/authorization/policies")
@authentication_decorator
def handle_new_authorization_policy(self, handle, connection, match, data, hdr):
    """
    POST /authorization/policies
    Create a new policy
    Body: policy in JSON format
    Response status code: OK or INTERNAL_ERROR
    Response: {"policy_id": <policy-id>}
    """
    # TODO: need some kind of authentication for policy management
    try:
        policy_id = self.node.authorization.prp.create_policy(data)
        status = calvinresponse.OK
    except:
        policy_id = None
        _log.exception("handle_new_authorization_policy")
        status = calvinresponse.INTERNAL_ERROR
    self.send_response(handle, connection, None if policy_id is None else json.dumps({'policy_id': policy_id}),
                       status=status)


@handler(method="GET", path="/authorization/policies")
@authentication_decorator
def handle_get_authorization_policies(self, handle, connection, match, data, hdr):
    """
    GET /authorization/policies
    Get all policies on this runtime
    Response status code: OK or INTERNAL_ERROR
    Response:
    {
        "policies": {
            <policy-id>: policy in JSON format,
            ...
        }
    }
    """
    try:
        policies = self.node.authorization.prp.get_policies()
        status = calvinresponse.OK
    except:
        _log.exception("handle_get_authorization_policies")
        status = calvinresponse.INTERNAL_ERROR
    self.send_response(handle, connection, json.dumps({"policies": policies}) if status == calvinresponse.OK else None,
                       status=status)


@handler(method="GET", path="/authorization/policies/{policy_id}")
@authentication_decorator
def handle_get_authorization_policy(self, handle, connection, match, data, hdr):
    """
    GET /authorization/policies/{policy-id}
    Get policy
    Response status code: OK, INTERNAL_ERROR or NOT_FOUND
    Response: {"policy": policy in JSON format}
    """
    try:
        data = self.node.authorization.prp.get_policy(match.group(1))
        status = calvinresponse.OK
    except IOError:
        _log.exception("handle_get_authorization_policy")
        status = calvinresponse.NOT_FOUND
    except:
        _log.exception("handle_get_authorization_policy")
        status = calvinresponse.INTERNAL_ERROR
    self.send_response(handle, connection, json.dumps({"policy": data}) if status == calvinresponse.OK else None,
                       status=status)

@handler(method="PUT", path="/authorization/policies/{policy_id}")
@authentication_decorator
def handle_edit_authorization_policy(self, handle, connection, match, data, hdr):
    """
    PUT /authorization/policies/{policy-id}
    Update policy
    Body: new policy in JSON format
    Response status code: OK, INTERNAL_ERROR or NOT_FOUND
    Response: none
    """
    # TODO: need some kind of authentication for policy management
    try:
        self.node.authorization.prp.update_policy(data, match.group(1))
        status = calvinresponse.OK
    except IOError:
        _log.exception("handle_edit_authorization_policy")
        status = calvinresponse.NOT_FOUND
    except:
        _log.exception("handle_edit_authorization_policy")
        status = calvinresponse.INTERNAL_ERROR
    self.send_response(handle, connection, None, status=status)

@handler(method="DELETE", path="/authorization/policies/{policy_id}")
@authentication_decorator
def handle_del_authorization_policy(self, handle, connection, match, data, hdr):
    """
    DELETE /authorization/policies/{policy-id}
    Delete policy
    Response status code: OK, INTERNAL_ERROR or NOT_FOUND
    Response: none
    """
    # TODO: need some kind of authentication for policy management
    try:
        self.node.authorization.prp.delete_policy(match.group(1))
        status = calvinresponse.OK
    except OSError:
        _log.exception("handle_del_authorization_policy")
        status = calvinresponse.NOT_FOUND
    except:
        _log.exception("handle_del_authorization_policy")
        status = calvinresponse.INTERNAL_ERROR
    self.send_response(handle, connection, None, status=status)
