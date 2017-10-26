
import os
from codegen import calvin_codegen
from calvin.utilities.security import Security, security_enabled
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.issuetracker import IssueTracker

_log = get_logger(__name__)

def appname_from_filename(filename):
    appname = os.path.splitext(os.path.basename(filename))[0]
    # Dot . is invalid in application names (interpreted as actor path separator),
    # so replace any . with _
    appname = appname.replace('.', '_')
    return appname


# FIXME: filename is sometimes an appname and sometimes a path to a file, see
#        code calling Security.verify_signature_get_files below
def compile_script(source_text, filename, credentials=None, verify=True):
    """
    Compile a script and return a tuple (deployable, errors, warnings)

    N.B 'credentials' and 'verify' are intended for actor store access, currently unused
    """
    appname = appname_from_filename(filename)
    return calvin_codegen(source_text, appname, verify=verify)


# FIXME: It might make sense to turn this function into a plain asynchronous security check.
#        Caller can then call compile_script based on status
def compile_script_check_security(data, filename, cb, security=None, content=None, verify=True, node=None, signature=None):
    """
    Compile a script and return a tuple (deployable, errors, warnings).

    'credentials' are optional security credentials(?)
    'verify' is deprecated and will be removed
    'node' is the runtime performing security check(?)
    'cb' is a CalvinCB callback

    N.B. If callback 'cb' is given, this method calls cb(deployable, errors, warnings) and returns None
    N.B. If callback 'cb' is given, and method runs to completion, cb is called with additional parameter 'security' (?)
    """
    def _exit_with_error(callback):
        """Helper method to generate a proper error"""
        it = IssueTracker()
        it.add_error("UNAUTHORIZED", info={'status':401})
        callback({}, it)
        return

    def _handle_policy_decision(data, appname, verify, access_decision, org_cb, security=None):
        if not access_decision:
            _log.error("Access denied")
            # This error reason is detected in calvin control and gives proper REST response
            _exit_with_error(org_cb)
            return
        if 'app_info' not in data and 'script' in data:
            deployable, issuetracker = compile_script(data['script'], appname)
        elif 'app_info' in data:
            deployable = data['app_info']
            issuetracker = IssueTracker()
        else:
            _log.error("Neither app_info or script supplied")
            # This error reason is detected in calvin control and gives proper REST response
            _exit_with_error(org_cb)
            return
        org_cb(deployable, issuetracker, security=security)

    #
    # Actual code for compile_script
    #
    appname = appname_from_filename(filename)
    # FIXME: if node is None we bypass security even if enabled. Is that the intention?
    if node is not None and security_enabled():
        # FIXME: If cb is None, we will return from this method with None instead of a tuple, failing silently
        if security:
            sec = security
        else:
            sec = Security(node)


        verified, signer = sec.verify_signature_content(content, "application")
        if not verified:
            # Verification not OK if sign or cert not OK.
            _log.error("Failed application verification")
            # This error reason is detected in calvin control and gives proper REST response
            _exit_with_error(cb)
            return
        sec.check_security_policy(
            CalvinCB(_handle_policy_decision, data, appname, verify, security=security, org_cb=cb),
            element_type = "application",
            element_value = signer
        )
        return

    #
    # We get here if node is None, or security is disabled
    #
    # This used to be
    # _handle_policy_decision(data, filename, verify, access_decision=True, security=None, org_cb=cb)
    # but since _handle_policy_decision is called with access_decision=True, security=None only compile_script would be called
    if 'app_info' not in data and 'script' in data:
        deployable, issuetracker = compile_script(data['script'], appname)
    elif 'app_info' in data:
        deployable = data['app_info']
        issuetracker = IssueTracker()
    else:
        _log.error("Neither app_info or script supplied")
        # This error reason is detected in calvin control and gives proper REST response
        _exit_with_error(org_cb)
        return
    cb(deployable, issuetracker, security=None)


