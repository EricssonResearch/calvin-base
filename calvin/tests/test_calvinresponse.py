# -*- coding: utf-8 -*-

# Copyright (c) 2016 Philip Ståhl
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

from calvin.requests.calvinresponse import RESPONSE_CODES, CalvinResponse

pytestmark = pytest.mark.unittest


def test_boolean_value():
    success_list = range(200, 207)
    for code in RESPONSE_CODES:
        response = CalvinResponse(code)
        if code in success_list:
            assert response
        else:
            assert not response


def test_comparisons():
    first = CalvinResponse(100)
    second = CalvinResponse(200)
    third = CalvinResponse(200)

    assert first < second
    assert second > first
    assert second == third
    assert first != second
    assert second <= third
    assert third <= second


def test_set_status():
    response = CalvinResponse(100)
    assert response.status == 100
    response.set_status(400)
    assert response.status == 400
    response.set_status(True)
    assert response.status == 200
    response.set_status(False)
    assert response.status == 500
