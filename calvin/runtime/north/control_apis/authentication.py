from base64 import b64decode
from calvin.requests import calvinresponse
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.issuetracker import IssueTracker
from calvin.utilities.calvinlogger import get_logger


_log = get_logger(__name__)


def authentication_decorator(func):
    def _exit_with_error(issue_tracker):
        """Helper method to generate a proper error"""
        _log.debug("CalvinControl::_exit_with_error  add 401 to issuetracker")
        issue_tracker.add_error("UNAUTHORIZED", info={'status':401})
        return

    def _handle_authentication_decision(authentication_decision, arguments=None, security=None, org_cb=None, issue_tracker=None):
        _log.debug("CalvinControl::_handle_authentication_decision, authentication_decision={}".format(authentication_decision))
        if not authentication_decision:
            _log.error("Authentication failed")
            # This error reason is detected in calvin control and gives proper REST response
            # Authentication failure currently results in no subject attrbutes, which might still give access to the resource
            # , an alternative approach is to always deny access for authentication failure. Not sure what is best.
            _exit_with_error(issue_tracker)
        try:
            security.check_security_policy(
                CalvinCB(_handle_policy_decision,
                         arguments=arguments,
                         org_cb=org_cb,
                         issue_tracker=issue_tracker),
                element_type="control_interface",
                element_value=arguments['func'].func_name
            )
        except Exception as exc:
            _log.exception("Failed to check security policy, exc={}".format(exc))
            return _handle_policy_decision(access_decision=False, arguments=arguments, org_cb=org_cb, issue_tracker=issue_tracker)

    def _handle_policy_decision(access_decision, arguments=None, org_cb=None, issue_tracker=None):
        _log.debug("CalvinControl::_handle_policy_decision:\n\tauthorization_decision={}\n\targuments={}\n\ttorg_cb={}".format(access_decision, arguments, org_cb))
        if not access_decision:
            _log.error("Access denied")
            # This error reason is detected in calvin control and gives proper REST response
            _exit_with_error(issue_tracker)
        if issue_tracker.error_count:
            four_oh_ones = [e for e in issue_tracker.errors(sort_key='reason')]
            errors = issue_tracker.errors(sort_key='reason')
            for e in errors:
                if 'status' in e and e['status'] == 401:
                    _log.error("Security verification of script failed")
                    status = calvinresponse.UNAUTHORIZED
                    body = None
                    arguments['self'].send_response(arguments['handle'], arguments['connection'], body, status=status)
                    return
        return arguments['func'](arguments['self'], arguments['handle'], arguments['connection'], arguments['match'], arguments['data'], arguments['hdr'])

    def inner(self, handle, connection, match, data, hdr):
        _log.debug("authentication_decorator::inner, arguments were:"
                   "\n\tfunc={}"
                   "\n\thandle={}"
                   "\n\tconnection={}"
                   "\n\tmatch={}"
                   "\n\tdata={}"
                   "\n\thdr={}".format(func, handle, connection, match, data, hdr))

        issue_tracker = IssueTracker()
        credentials = None
        arguments={'func':func, 'self':self, 'handle':handle, 'connection':connection, 'match':match, 'data':data, 'hdr':hdr}
        try:
            if 'authorization' in hdr:
                cred = b64decode(hdr['authorization'].strip('Basic ')).split(':')
                credentials ={'user':cred[0], 'password':cred[1]}
            if data and 'sec_credentials' in data:
                deploy_credentials = data['sec_credentials']
        except TypeError as err:
            _log.error("inner: code not decode credentials in header")
            pass
        try:
            self.security.authenticate_subject(
                credentials,
                callback=CalvinCB(_handle_authentication_decision, arguments=arguments, security=self.security, org_cb=None, issue_tracker=issue_tracker)
            )
        except Exception as exc:
            _log.exception("Failed to authenticate the subject, exc={}".format(exc))
            _exit_with_error(issue_tracker)

    return inner
