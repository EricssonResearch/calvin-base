import pytest
import json

from mock import patch, Mock

from calvin.utilities import calvinlogger


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

        msg = "[[ANALYZE]]" + json.dumps({
            "peer_node_id": peer_node_id,
            "node_id": node_id,
            "func": func,
            "param": param,
            "stack": expected_stack
        })
        log._log.assert_called_with(5, msg, (), args=args, kwargs=kwargs)

        if tb:
            assert extract_stack.called
        else:
            assert not extract_stack.called
