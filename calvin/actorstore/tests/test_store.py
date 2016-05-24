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

import pytest
import timeit

from calvin.actorstore.store import ActorStore


class TestActorStore(object):

    def setup_class(self):
        self.ms = ActorStore()
        pass

    def teardown_class(self):
        pass

    def test_find_modules(self):

        # Valid
        module = self.ms.lookup("std.Sum")
        assert len(module) is 4
        assert module[0]

        # Fail
        module = self.ms.lookup("non.ExistantActor")
        assert not module[0]

        # Sys module
        module = self.ms.lookup("os")
        assert not module[0]

    def test_load_modules(self):
        pass

    @pytest.mark.xfail  # May or may not pass. Not that important
    def test_perf(self):
        time = timeit.timeit(lambda: self.ms.lookup("std.Sum"), number=1000)
        assert time < .2
