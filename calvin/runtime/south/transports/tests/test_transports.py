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
import sys
import os
import traceback
import random
import time
import json
import Queue
from mock import Mock

from calvin.utilities import calvinlogger
from calvin.utilities.calvin_callback import *

from twisted.internet import reactor

_log = calvinlogger.get_logger(__name__)


@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    def fin():
        reactor.callFromThread(reactor.stop)
    request.addfinalizer(fin)

@pytest.mark.essential
class TestTransportServer(object):

    def test_start_stop(self, monkeypatch):
        pass

    def test_callbacks(self, monkeypatch):
        pass

@pytest.mark.essential
class TestTransport(object):

    def test_connect(self, monkeypatch):
        pass

    def test_data(self, monkeypatch):
        pass

    def test_callback(self, monkeypatch):
        pass
