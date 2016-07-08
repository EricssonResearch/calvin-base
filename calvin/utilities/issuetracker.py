import sys
import string

class IssueFormatter(string.Formatter):
    """
    Custom string formatter, adds
        u : uppercase
        l : lowercase
        c : capitalize
    to string formatting, e.g.
        issue_formatter.format("{foo!c}", foo="hello world!")
    returns "HELLO WORLD!"

    Note that autonumbering, i.e. use of {}, is not possible.
    """

    # http://stackoverflow.com/q/17848202/1007047
    # http://stackoverflow.com/q/21664318/1007047

    def __init__(self):
        super(IssueFormatter, self).__init__()

    def convert_field(self, value, conversion):
        if conversion == 'c':
            return value.capitalize()
        elif conversion == 'u':
            return value.upper()
        elif conversion == 'l':
            return value.lower()
        return super(IssueFormatter, self).convert_field(value, conversion)



class IssueTracker(object):
    """
    A pretty generic issue tracker that can sort, format, and report back issues.

    An issue is a dict with information, guaranteed to have keys, 'type' and 'reason',
    where value of 'type' is either 'error' or 'warning', and the value of 'reason'
    is (should be) a human readable string explaining the issue.
    """

    issue_types = ['error', 'warning']

    def __init__(self, allow_duplicates=False):
        """
        If allow_duplicates is True issues identical to an already tracked issue
        will be added, default is to discard duplicates.
        """
        super(IssueTracker, self).__init__()
        self.allow_duplicates = allow_duplicates
        self._issues = []
        self._err_count = 0
        self._warn_count = 0
        self._default_format = "{type!c}: {reason}"

    def _add_issue(self, issue_type, reason, info):
        if issue_type not in self.issue_types:
            raise Exception("issue_type should be one of {}".format(str(self.issue_types)))

        issue = {
            'type': issue_type,
            'reason': reason,
        }
        if type(info) is dict:
            issue.update(info)
        elif hasattr(info, 'debug_info'):
            issue.update(info.debug_info or {})

        if self.allow_duplicates or issue not in self._issues:
            self._issues.append(issue)
            if issue['type'] == 'error':
                self._err_count += 1
            else:
                self._warn_count += 1

    def add_error(self, reason, info=None):
        """
        Add an error.

        Mandatory argument reason should be a human readable string.
        Optional argument info is a dictionary with information like line number etc.
        """
        self._add_issue('error', reason, info)

    def add_warning(self, reason, info=None):
        """
        Add an error.

        Mandatory argument reason should be a human readable string.
        Optional argument info is a dictionary with information like line number etc.
        """
        self._add_issue('warning', reason, info)

    @property
    def error_count(self):
        """Number of errors tracked"""
        return self._err_count

    @property
    def warning_count(self):
        """Number of warnings tracked"""
        return self._warn_count

    @property
    def issue_count(self):
        """Total number of issues tracked"""
        return self._warn_count + self._err_count

    def issues(self, issue_type=None, sort_key=None):
        """
        Return a list of issues.

        If issue_type is given, only return issues of that type.
        If sort_key is given, use that to retrieve a value from each issue
        used to sort the result. If sort_key is not present in issue, sort
        order is undefined.
        """
        if issue_type:
            issues = [i for i in self._issues if i['type'] == issue_type]
        else:
            issues = self._issues[:]
        if sort_key:
            # Sort in place since we have a copy
            # If sort_key not in issue(s) order is undefined
            # Note: Won't work on python3
            issues.sort(key=lambda k: k.get(sort_key))
        return issues

    def errors(self, sort_key=None):
        """
        Return a list of errors.

        If sort_key is given, use that to retrieve a value from each error
        used to sort the result. If sort_key is not present in error, sort
        order is undefined.
        """
        return self.issues(issue_type='error', sort_key=sort_key)
        # return [e for e in self._issues if e['type'] == 'error']

    def warnings(self, sort_key=None):
        """
        Return a list of warnings.

        If sort_key is given, use that to retrieve a value from each warning
        used to sort the result. If sort_key is not present in warning, sort
        order is undefined.
        """
        return self.issues(issue_type='warning', sort_key=sort_key)
        # return [e for e in self._issues if e['type'] == 'warning']

    def _format_items(self, items, item_format, **kwargs):
        if not item_format:
            item_format = self._default_format
        did_warn = False
        fmt = IssueFormatter()
        result = []
        for item in items:
            combined = {}
            combined.update(kwargs)
            combined.update(item)
            try:
                x = fmt.format(item_format, **combined)
            except:
                # This should not fail
                if not did_warn:
                    sys.stderr.write("Bad format string '{}', using default.\n".format(str(item_format)))
                    sys.stderr.write("Available keys: {}\n".format(str(combined.keys())))
                    did_warn = True
                x = fmt.format(self._default_format, **combined)

            result.append(x)

        return result

    def formatted_issues(self, issue_type=None, sort_key=None, custom_format=None, **kwargs):
        """
        Return a list of issues formatted as strings.

        Optional parameters issue_type and sort_key behaves as for issues().
        If custom_format is given it should follow string.format() rules, with the
        additional string conversion options 'u', 'l', and 'c' for upper, lower,
        and capitalize, respectively, e.g. "{foo!u}" for uppercasing. The default format is
        "{type!c}: {reason}", which is also the fallback format in case of any errors.
        Any additional key-value arguments will be available to the formatter, e.g.
        custom_format="{type!c}: {reason} {filename}:{line}", filename="foo/bar.calvin".
        Values from the actual issue will take precedence over additional values for the same key.

        Note that autonumbering, i.e. use of {}, is not allowed in the format strings, and while
        indexed references, i.e. {0} {1}, are allowed they make no sense in this context.
        """
        return self._format_items(self.issues(sort_key=sort_key), custom_format, **kwargs)

    def formatted_errors(self, sort_key=None, custom_format=None, **kwargs):
        """
        Return a list of errors formatted as strings.

        Optional parameter sort_key behaves as for issues(). Custom_format and extra
        key-value arguments are explained in formatted_issues().
        """
        return self._format_items(self.errors(sort_key=sort_key), custom_format, **kwargs)

    def formatted_warnings(self, sort_key=None, custom_format=None, **kwargs):
        """
        Return a list of warnings formatted as strings.

        Optional parameter sort_key behaves as for issues(). Custom_format and extra
        key-value arguments are explained in formatted_issues().
        """
        return self._format_items(self.warnings(sort_key=sort_key), custom_format, **kwargs)


if __name__ == '__main__':

    myfmt = IssueFormatter()
    print myfmt.format("{foo!u} {foo!c}", foo="hello")
    print myfmt.format("{0!u} {0!c}", "hello")



    t = IssueTracker()
    t.add_error("Foo")
    t.add_warning("Bar")

    print t.issues()
    print t.error_count, t.errors()
    print t.warning_count, t.warnings()
    print t.issue_count, t.issues()
    t.add_warning("Bar")
    assert t.warning_count == 1
    t.allow_duplicates = True
    t.add_warning("Bar")
    assert t.warning_count == 2

    for f in t.formatted_issues():
        print f

    for f in t.formatted_warnings():
        print f

    for f in t.formatted_errors():
        print f

    for f in t.formatted_issues(custom_format="{reason}"):
        print f

    for f in t.formatted_warnings(custom_format="{type!u} - {reason}"):
        print f

    for f in t.formatted_errors(custom_format="{type} - {reason!u}"):
        print f

    for f in t.formatted_issues(custom_format="{no_reason}"):
        print f

    t.add_error("Line", {'line':0, 'col':0, 'extra':42})

    for f in t.formatted_issues(custom_format="{no_reason}"):
        print f

    t.add_error("Apa")
    t.add_error("Ara")
    print "--- Sorted (type) ---"
    for f in t.formatted_issues(custom_format="{no_reason}", sort_key="type"):
        print f
    print "--- Sorted (reason) ---"
    for f in t.formatted_issues(custom_format="{no_reason}", sort_key="reason"):
        print f
    print "--- Sorted (BAD: no_reason) ---"
    for f in t.formatted_issues(sort_key="no_reason"):
        print f
    print "--- Sorted (line) ---"
    for f in t.formatted_errors(custom_format="{type!c}: {reason} {line}:{col}", sort_key="line"):
        print f

    print "--- Sorted (extras) ---"
    for f in t.formatted_errors(custom_format="{type!c}: {reason} {filename}, line: {line}", sort_key="line", filename="baz.calvin", line="bogus"):
        print f





