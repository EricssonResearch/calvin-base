# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
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

import numbers
from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)

RESPONSE_CODES = {
    # Information
    100: 'Continue',
    101: 'Switching Protocols',
    # Success
    200: 'OK',  # Preferred
    201: 'Created',
    202: 'Accepted',  # Preferred
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    # Redirect
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    306: '(Unused)',
    307: 'Temporary Redirect',
    # Client errors
    400: 'Bad Request',  # Preferred
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',  # Preferred
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',  # Preferred
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request-URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    # Server error
    500: 'Internal Server Error',  # Preferred
    501: 'Not Implemented',  # Preferred
    502: 'Bad Gateway',  # Preferred
    503: 'Service Unavailable',  # Preferred
    504: 'Gateway Timeout',  # Preferred
    505: 'HTTP Version Not Supported'
}

OK = 200
CREATED = 201
ACCEPTED = 202
BAD_REQUEST = 400
UNAUTHORIZED = 401
NOT_FOUND = 404
GONE = 410
INTERNAL_ERROR = 500
NOT_IMPLEMENTED = 501
BAD_GATEWAY = 502
SERVICE_UNAVAILABLE = 503
GATEWAY_TIMEOUT = 504

class CalvinResponseException(Exception):
    """ CalvinResponseException"""
    def __init__(self, response):
        super(CalvinResponseException, self).__init__()
        self.response = response

    @property
    def status(self):
        return self.response.status

    @property
    def data(self):
        return self.response.data

    @property
    def success_list(self):
        return self.response.success_list

    def __str__(self):
        return "Exception(%s)" % str(self.response)


class CalvinResponse(object):
    """A generic class for handling all responses between entities"""
    def __init__(self, status=OK, data=None, encoded=None):
        super(CalvinResponse, self).__init__()
        if encoded:
            self.set_status(encoded['status'])
            self.data = encoded['data']
            self.success_list = encoded['success_list']
        else:
            self.set_status(status)
            self.data = data
            self.success_list = range(200, 207)

    def __nonzero__(self):
        return self._status()

    def __bool__(self):
        return self._status()

    def _status(self):
        return self.status in self.success_list

    def __eq__(self, other):
        """ When need to check if response is equal to specific code
            other can be another CalvinResponse object,
            a status code
        """
        if isinstance(other, CalvinResponse):
            return self.status == other.status
        elif isinstance(other, numbers.Number):
            return self.status == other
        else:
            return False

    def __lt__(self, other):
        if isinstance(other, CalvinResponse):
            return self.status < other.status
        elif isinstance(other, numbers.Number):
            return self.status < other
        else:
            return False

    def __le__(self, other):
        if isinstance(other, CalvinResponse):
            return self.status <= other.status
        elif isinstance(other, numbers.Number):
            return self.status <= other
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, CalvinResponse):
            return self.status != other.status
        elif isinstance(other, numbers.Number):
            return self.status != other
        else:
            return False

    def __gt__(self, other):
        if isinstance(other, CalvinResponse):
            return self.status > other.status
        elif isinstance(other, numbers.Number):
            return self.status > other
        else:
            return False

    def __ge__(self, other):
        if isinstance(other, CalvinResponse):
            return self.status >= other.status
        elif isinstance(other, numbers.Number):
            return self.status >= other
        else:
            return False

    def set_status(self, status):
        if isinstance(status, bool):
            status = 200 if status else 500
        if status == 500 or status == 404:
            _log.debug("Setting failure status %s on CalvinResponse", status)
            # For debuging!!
            # import traceback
            # traceback.print_stack(limit=10)
        self.status = status

    def encode(self):
        return {'status': self.status, 'data': self.data, 'success_list': self.success_list}

    def __str__(self):
        return str(self.status) + ", " + RESPONSE_CODES[self.status] + ((", " + str(self.data)) if self.data else "")


def isfailresponse(obj):
    if isinstance(obj, CalvinResponse):
        return not bool(obj)
    else:
        return False


def isnotfailresponse(obj):
    if isinstance(obj, CalvinResponse):
        return bool(obj)
    else:
        return True


if __name__ == '__main__':
    r = CalvinResponse(OK)
    r2 = CalvinResponse(OK)
    r3 = CalvinResponse(BAD_REQUEST)
    r.data = {'foo': 42}
    if r:
        print "CORRECT", r
    else:
        print "INCORRECT", r

    if r3:
        print "INCORRECT", r3
    else:
        print "CORRECT", r3

    if r == OK:
        print "EQ CORRECT1"
    else:
        print "EQ INCORRECT1"

    if r in [OK, BAD_REQUEST]:
        print "EQ CORRECT2"
    else:
        print "EQ INCORRECT2"

    if r == r2:
        print "EQ CORRECT3"
    else:
        print "EQ INCORRECT3"

    if r == r3:
        print "EQ INCORRECT4"
    else:
        print "EQ CORRECT4"

    if min([r, r2, r3]):
        print "EQ CORRECT5"
    else:
        print "EQ INCORRECT5"

    if max([r, r2, r3]):
        print "EQ INCORRECT6"
    else:
        print "EQ CORRECT6"

    print max([r, r2, r3])
