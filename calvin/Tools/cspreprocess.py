import os
import re
from calvin.utilities.issuetracker import IssueTracker

def _expand_path(path):
    return os.path.abspath(os.path.expanduser(path))

class Preprocessor(object):
    """docstring for Preprocessor"""

    INCL_REGEX = r'\s*include\s+([^\s/\\:\*\?]+)'

    def __init__(self, include_paths=None):
        super(Preprocessor, self).__init__()
        paths = include_paths or []
        self.include_paths = [_expand_path(path) for path in paths]

    def process(self, source_file, issuetracker=None):
        path = os.path.dirname(source_file)
        self.path = _expand_path(path)
        self.source_file = _expand_path(source_file)
        self.issuetracker = issuetracker or IssueTracker()
        self.line_number = 0
        return self._process(), self.issuetracker

    def _process(self):
        source_text = self._read_file(self.source_file)
        source_lines = []
        for line in source_text.split("\n"):
            self.line_number += 1
            match = re.match(self.INCL_REGEX, line)
            if match:
                include_file = "{}.calvin".format(match.group(1))
                note = "# {}".format(line)
                source_lines.append(note)
                source_lines.append(self._read_include_file(include_file))
            else:
                source_lines.append(line)
        source_text = "\n".join(source_lines)
        return source_text

    def _read_file(self, filepath):
        source_text = ""
        try:
            with open(filepath, 'r') as source:
                source_text = source.read()
        except:
            self.issuetracker.add_error(reason="Could not read file {}.".format(filepath), info={})
        return source_text

    def _read_include_file(self, filename):
        source_text = ""
        for include_path in [self.path] + self.include_paths:
            filepath = os.path.join(include_path, filename)
            if os.path.isfile(filepath):
                return self._read_file(filepath)
        self.issuetracker.add_error(reason="Could not find file {}.".format(filename), info={'line':self.line_number, 'col':0})
        return ""



if __name__ == '__main__':
    FILE = "~/Source/calvin-base/calvin/examples/sample-scripts/fibo_main.calvin"
    pp = Preprocessor()
    source_text, it = pp.process(FILE)
    print source_text
    print "Errors:", it.error_count
    for err in it.formatted_errors():
        print err

