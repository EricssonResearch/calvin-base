
def get_runtime(value):
    if isinstance(value, basestring):
        return Runtime(value)
    else:
        return value


class Runtime(object):
    def __init__(self, control_uri):
        self.control_uri = control_uri
