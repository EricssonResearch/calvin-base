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
import json

from mock import patch, Mock

from calvin.utilities import calvinlogger

pytestmark = pytest.mark.unittest


@patch('calvin.utilities.calvinlogger.logging')
def test_get_logger(logging_mock):
    calvinlogger._log = None
    log_mock = Mock()
    logging_mock.getLogger = Mock(return_value=log_mock)

    log = calvinlogger.get_logger()
    assert logging_mock.getLogger.called
    log_mock.setLevel.assert_called_with(logging_mock.INFO)
    assert log == log_mock

    log = calvinlogger.get_logger(name="abc")
    assert log == log_mock.getChild("abc")


@patch('calvin.utilities.calvinlogger._create_logger')
def test_get_actor_logger(create_logger):
    log_mock = Mock()
    create_logger.return_value = log_mock
    log = calvinlogger.get_actor_logger("abc")

    assert create_logger.called
    assert log == log_mock.getChild("abc")


@patch('calvin.utilities.calvinlogger._create_logger')
def test_set_file(create_logger):
    calvinlogger.set_file("filename")
    create_logger.assert_called_with("filename")


@pytest.mark.parametrize("node_id,func,param,peer_node_id,tb,mute,args,kwargs", [
    (1, "func", "param", 2, False, False, (1, 2, 3), {"kwargs": 1}),
    (1, "func", "param", 2, True, True, (1, 2, 3), {"kwargs": 1}),
    (1, "func", "param", 2, True, False, (1, 2, 3), {"kwargs": 1}),
    (1, "func", "param", 2, True, False, None, None)
])
@patch.object(calvinlogger.traceback, "extract_stack", return_value="stack")
def test_analyze(extract_stack, node_id, func, param, peer_node_id, tb, mute, args, kwargs):
    calvinlogger._log = None
    log = calvinlogger.get_logger()
    log.isEnabledFor = Mock(return_value=True)
    log._log = Mock()
    log.analyze(node_id=node_id, func=func, param=param, peer_node_id=peer_node_id, tb=tb, mute=mute,
                args=args, kwargs=kwargs)

    if mute:
        assert not log._log.called
    else:
        expected_stack = None
        if tb:
            expected_stack = "stack"

        correct_msg = {
            "peer_node_id": peer_node_id,
            "node_id": node_id,
            "func": func,
            "param": param,
            "stack": expected_stack
        }
        # JSON might reorder the dict hence need detailed assert
        assert log._log.call_args[0][0] == 5
        assert log._log.call_args[0][1].startswith("[[ANALYZE]]")
        test_msg = json.loads(log._log.call_args[0][1][11:])
        assert correct_msg == test_msg
        assert log._log.call_args[0][2] == ()
        assert log._log.call_args[1]['args'] == args
        assert log._log.call_args[1]['kwargs'] == kwargs
        if tb:
            assert extract_stack.called
        else:
            assert not extract_stack.called
