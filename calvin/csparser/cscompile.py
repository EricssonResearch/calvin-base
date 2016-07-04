
import os
from parser import calvin_parser
from codegen import CodeGen
from calvin.utilities.security import Security, security_enabled
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


def compile_script(source_text, filename, credentials=None, verify=True, node=None, cb=None):
    # Steps taken:
    # 1) Authenticate subject, verify signature and check security policy if security is enabled
    # 2) parser .calvin file -> IR. May produce syntax errors/warnings
    # 3) checker IR -> IR. May produce syntax errors/warnings
    # 4) analyzer IR -> app. Should not fail. Sets 'valid' property of IR to True/False


    def _compile_cont1(source_text, filename, verify, authentication_decision, security, org_cb=None, content=None):
        deployable = {'valid': False, 'actors': {}, 'connections': {}}
        errors = [] # TODO: fill in something meaningful
        warnings = []
        if not authentication_decision:
            _log.error("Authentication failed")
            # This error reason is detected in calvin control and gives proper REST response
            errors.append({'reason': "401: UNAUTHORIZED", 'line': None, 'col': None})
            if org_cb:
                org_cb(deployable, errors, warnings)
                return
            else:
                return deployable, errors, warnings

        verified, signer = security.verify_signature_content(content, "application")
        if not verified:
            # Verification not OK if sign or cert not OK.
            _log.error("Failed application verification")
            # This error reason is detected in calvin control and gives proper REST response
            errors.append({'reason': "401: UNAUTHORIZED", 'line': None, 'col': None})
            if org_cb:
                org_cb(deployable, errors, warnings)
                return
            else:
                return deployable, errors, warnings
        security.check_security_policy(CalvinCB(_compile_cont2, source_text, filename, verify,
                                           security=security, org_cb=org_cb), "application", signer=signer)

    def _compile_cont2(source_text, filename, verify, access_decision, security=None, org_cb=None):
        deployable = {'valid': False, 'actors': {}, 'connections': {}}
        errors = [] # TODO: fill in something meaningful
        warnings = []
        if not access_decision:
            _log.error("Access denied")
            # This error reason is detected in calvin control and gives proper REST response
            errors.append({'reason': "401: UNAUTHORIZED", 'line': None, 'col': None})
            if org_cb:
                org_cb(deployable, errors, warnings)
                return
            else:
                return deployable, errors, warnings
        _log.debug("Parsing...")
        ir, errors, warnings = calvin_parser(source_text, filename)
        _log.debug("Parsed %s, %s, %s" % (ir, errors, warnings))

        app_name = os.path.splitext(os.path.basename(filename))[0]
        codegen = CodeGen(ir, app_name, verify=verify)
        codegen.run()
        deployable = codegen.app_info
        errors.extend([issue for issue in codegen.issues if issue['type'] == 'error'])
        warnings.extend([issue for issue in codegen.issues if issue['type'] == 'warning'])


        _log.debug("Compiled %s, %s, %s" % (deployable, errors, warnings))
        if org_cb:
            org_cb(deployable, errors, warnings, security=security)
        else:
            return deployable, errors, warnings


    content = None
    if credentials:
        content = Security.verify_signature_get_files(filename, skip_file=True)
        # content is ALWAYS a dict if skip_file is True
        content['file'] = source_text

    deployable = {'valid': False, 'actors': {}, 'connections': {}}
    errors = [] # TODO: fill in something meaningful
    warnings = []
    if node is not None and security_enabled():
        sec = Security(node)
        sec.authenticate_subject(credentials, callback=CalvinCB(_compile_cont1, source_text,
                                                filename, verify, security=sec, org_cb=cb, content=content))
    else:
        if cb:
            _compile_cont2(source_text, filename, verify, True, org_cb=cb)
        else:
            return _compile_cont2(source_text, filename, verify, True)
