
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
def compile_script_check_security(source_text, filename, cb, credentials=None, verify=True, node=None):
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


    def _handle_authentication_decision(source_text, appname, verify, authentication_decision, security, org_cb, content=None):
        if not authentication_decision:
            _log.error("Authentication failed")
            # This error reason is detected in calvin control and gives proper REST response
            _exit_with_error(org_cb)

        verified, signer = security.verify_signature_content(content, "application")
        if not verified:
            # Verification not OK if sign or cert not OK.
            _log.error("Failed application verification")
            # This error reason is detected in calvin control and gives proper REST response
            _exit_with_error(org_cb)

        security.check_security_policy(
            CalvinCB(_handle_policy_decision, source_text, appname, verify, security=security, org_cb=org_cb),
            "application",
            signer=signer
        )

    def _handle_policy_decision(source_text, appname, verify, access_decision, org_cb, security=None):
        if not access_decision:
            _log.error("Access denied")
            # This error reason is detected in calvin control and gives proper REST response
            _exit_with_error(org_cb)

        deployable, issutracker = compile_script(source_text, appname)

        org_cb(deployable, issutracker, security=security)

    #
    # Actual code for compile_script
    #
    appname = appname_from_filename(filename)
    # FIXME: if node is None we bypass security even if enabled. Is that the intention?
    if node is not None and security_enabled():
        if credentials:
            content = Security.verify_signature_get_files(filename, skip_file=True)
            # content is ALWAYS a dict if skip_file is True
            content['file'] = source_text
        else:
            content = None
        # FIXME: If cb is None, we will return from this method with None instead of a tuple, failing silently
        sec = Security(node)
        sec.authenticate_subject(
            credentials,
            callback=CalvinCB(_handle_authentication_decision, source_text, appname, verify, security=sec, org_cb=cb, content=content)
        )
        return

    #
    # We get here if node is None, or security is disabled
    #
    # This used to be
    # _handle_policy_decision(source_text, filename, verify, access_decision=True, security=None, org_cb=cb)
    # but since _handle_policy_decision is called with access_decision=True, security=None only compile_script would be called
    deployable, issuetracker = compile_script(source_text, appname)
    cb(deployable, issuetracker, security=None)


