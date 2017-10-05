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

class Token(object):

    """ Token class """

    def __init__(self, value=None, origin=None, timestamp=None, port_tag=None):
        self._value = value
        self._origin = origin
        self._timestamp = timestamp
        self._port_tag = port_tag

    @property
    def value(self):
        return self._value

    @property
    def origin(self):
        return self._origin

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def port_tag(self):
        return self._port_tag

    @value.setter
    def value(self, new_value):
        raise Exception("NICHT PILLEN!")
        # self._value = new_value

    def repr_for_coder(self):
        representation = {
            'type':self.__class__.__name__,
            'value':self._value
        }
        if self._origin:
            representation['origin'] = self._origin
        if self._timestamp:
            representation['self.timestamp'] = self._timestamp
        if self._port_tag:
            representation['self.port_tag'] = self._port_tag
        return representation

    def encode(self, coder=None):
        if not coder:
            return self.repr_for_coder()
        return coder.encode(self.repr_for_coder())

    @classmethod
    def decode(cls, data, coder=None):
        representaton = coder.decode(data) if coder else data
        token_type = representaton.pop('type', ExceptionToken)
        class_ = {
            'Token':Token,
            'ExceptionToken':ExceptionToken,
            'EOSToken': EOSToken
        }.get(token_type, ExceptionToken)
        return class_(**representaton)

    def __str__(self):
        return "<%s> %s" % (self.__class__.__name__, str(self._value))

    def __repr__(self):
        # To get it printed nicely also in lists
        return self.__str__()

class ExceptionToken(Token):

    """ Base class for exception tokens """

    def __init__(self, value="Exception", origin=None, timestamp=None, port_tag=None):
        super(ExceptionToken, self).__init__(value, origin, timestamp, port_tag)

class EOSToken(ExceptionToken):

    """ End of stream token """

    def __init__(self, value="End of stream", origin=None, timestamp=None, port_tag=None):
        super(EOSToken, self).__init__(value, origin, timestamp, port_tag)


if __name__ == '__main__':

    class Coder(object):
        """Base class for coders, does nothing"""
        def __init__(self):
            pass

        def encode(self, data):
            return data

        def decode(self, data):
            return data

    class FooCoder(Coder):
        """Fantastic Foo encoder"""
        def encode(self, data):
            return "<%s>" % str(data)

        def decode(self, data):
            return eval(data[1:-1])



    t = Token()
    print t

    t = ExceptionToken()
    print t

    t = EOSToken()
    print t

    t = ExceptionToken("Hello")
    print t

    t = Token(41)
    print t
    data = t.encode()
    print data
    t = Token.decode(data)
    print t


    t = Token(42)
    print t
    data = t.encode(coder=FooCoder())
    print data
    t = Token.decode(data, coder=FooCoder())
    print t

    t = EOSToken()
    print t
    data = t.encode(coder=FooCoder())
    print data
    t = Token.decode(data, coder=FooCoder())
    print t

    t = Token.decode("<{}>", coder=FooCoder())
    print t

