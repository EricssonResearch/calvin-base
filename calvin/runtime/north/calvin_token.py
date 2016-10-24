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

    def __init__(self, value=None):
        self.value = value

    def repr_for_coder(self):
        return {'type':self.__class__.__name__, 'data':self.value}

    def encode(self, coder=None):
        if not coder:
            return self.repr_for_coder()
        return coder.encode(self.repr_for_coder())

    @classmethod
    def decode(cls, data, coder=None):
        representaton = coder.decode(data) if coder else data
        token_type = representaton.get('type', '')
        class_ = {
            'Token':Token,
            'ExceptionToken':ExceptionToken,
            'EOSToken': EOSToken
        }.get(token_type, ExceptionToken)
        return class_(representaton.get('data', 'Bad Token'))

    def __str__(self):
        return "<%s> %s" % (self.__class__.__name__, str(self.value))

    def __repr__(self):
        # To get it printed nicely also in lists
        return self.__str__()

class ExceptionToken(Token):

    """ Base class for exception tokens """

    def __init__(self, value="Exception"):
        super(ExceptionToken, self).__init__(value)

class EOSToken(ExceptionToken):

    """ End of stream token """

    def __init__(self, value="End of stream"):
        super(EOSToken, self).__init__(value)


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

