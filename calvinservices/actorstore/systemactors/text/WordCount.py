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


from calvin.actor.actor import Actor, manage, condition, stateguard
from calvin.runtime.north.calvin_token import EOSToken

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class WordCount(Actor):
    """
    documentation:
    - Count occurances of words in a stream of words.
    ports:
    - direction: in
      help: a word
      name: in
    - direction: out
      help: count for each word
      name: out
    """

    @manage([])
    def init(self):
        self.word_counts = {}
        self.finished = False

    def exception_handler(self, action, args):
        self.finished = True

    @condition(['in'], [])
    def count_word(self, word):
        self.word_counts[word] = self.word_counts.setdefault(word, 0) + 1


    @stateguard(lambda self: self.finished is True)
    @condition(action_output=['out'])
    def output_counts(self):
        self.finished = False
        return (self.word_counts,)

    action_priority = (count_word, output_counts)

    test_set = [
        {
            'inports': {'in': ['a', 'b', 'a', EOSToken()]},
            'outports': {'out': [{'a': 2, 'b': 1}]}
        }
    ]
