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

import functools
from base64 import b64decode
from calvin.requests import calvinresponse
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.issuetracker import IssueTracker
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.security import security_enabled


_log = get_logger(__name__)


def authentication_decorator(func):

    @functools.wraps(func)
    def wrapper(self, handle, connection, match, data, hdr):

        def _unauthorized_response():
            self.send_response(handle, connection, None, status=calvinresponse.UNAUTHORIZED)

        def _handle_authentication_decision(authentication_decision):
            _log.debug("control_apis.authentication::_handle_authentication_decision, authentication_decision={}".format(authentication_decision))
            if not authentication_decision:
                _unauthorized_response()
                return
            try:
                self.security.check_security_policy(
                    CalvinCB(_handle_policy_decision),
                    element_type="control_interface",
                    element_value=arguments['func'].__name__
                )
            except Exception as exc:
                _log.exception("Failed to check security policy, exc={}".format(exc))
                _unauthorized_response()

        def _handle_policy_decision(access_decision):
            if not access_decision:
                _unauthorized_response()
                return
            # Yay! We made it!
            func(self, handle, connection, match, data, hdr)

        #
        # Exit early if security disabled
        #
        if not security_enabled():
            func(self, handle, connection, match, data, hdr)
            return
        #
        # Verify the request against credentials and policy
        #
        credentials = None
        arguments={'func':func, 'self':self, 'handle':handle, 'connection':connection, 'match':match, 'data':data, 'hdr':hdr}
        try:
            if 'authorization' in hdr:
                cred = b64decode(hdr['authorization'].strip('Basic ')).split(':')
                credentials ={'user':cred[0], 'password':cred[1]}
        except TypeError as err:
            _log.error("_verify_permission: Missing or wrongly formatted credentials in request header")
            # Continue without credentials, policy might allow access
        try:
            self.security.authenticate_subject(credentials, callback=CalvinCB(_handle_authentication_decision))
        except Exception as exc:
            _log.exception("Failed to authenticate the subject, exc={}".format(exc))
            _unauthorized_response()

    return wrapper
