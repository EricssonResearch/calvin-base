import pytest

from mock import patch

from calvin.utilities import nodecontrol

URI = "http://localhost:5001"
CONTROL_URI = "http://localhost:5002"


@patch('calvin.runtime.north.calvin_node.create_tracing_node')
@patch('calvin.runtime.north.calvin_node.create_node')
def test_start_node(create_node, create_tracing_node):
    nodecontrol.start_node(URI, CONTROL_URI, attributes={'a': 1})
    create_node.assert_called_with(URI, CONTROL_URI, {'a': 1})
    assert not create_tracing_node.called

    create_node.reset_mock()
    nodecontrol.start_node(URI, CONTROL_URI, trace=True, attributes={'a': 1})
    create_tracing_node.assert_called_with(URI, CONTROL_URI, True, {'a': 1})
    assert not create_node.called


@patch('calvin.runtime.north.calvin_node.Node.run')
def test_start_node_runs_node(run):
    nodecontrol.start_node(URI, CONTROL_URI, attributes={'a': 1})
    assert run.called


@patch('calvin.utilities.nodecontrol.get_node_id')
@patch('calvin.runtime.north.calvin_node.start_node')
def test_dispatch_node(start_node, get_node_id):
    nodecontrol.dispatch_node(URI, CONTROL_URI, attributes={'a': 1}, barrier=False)
    assert start_node.called
    assert not get_node_id.called

    start_node.reset_mock()
    nodecontrol.dispatch_node(URI, CONTROL_URI, attributes={'a': 1}, barrier=True)
    assert start_node.called
    assert get_node_id.called


@patch('calvin.utilities.storage_node.StorageNode.run')
def test_start_storage_node(run):
    nodecontrol.start_storage_node(URI, CONTROL_URI)
    assert run.called


@patch('calvin.utilities.storage_node.start_node')
@patch('calvin.utilities.nodecontrol.get_node_id')
def test_dispatch_storage_node(get_node_id, start_node):
    nodecontrol.dispatch_storage_node(URI, CONTROL_URI, trace=True, attributes={})
    start_node.assert_called_with(URI, CONTROL_URI, True, {})
    assert get_node_id.called


@pytest.mark.slow
@patch('calvin.utilities.nodecontrol.get_node_id')
def test_node_control_barrier(get_node_id):
    get_node_id.side_effect = Exception("")  # return_value = None
    nodecontrol.node_control(CONTROL_URI, barrier=False)
    assert not get_node_id.called

    with pytest.raises(AssertionError):
        nodecontrol.node_control(CONTROL_URI, barrier=True)
    assert get_node_id.call_count == 20
    get_node_id.reset_mock()

    get_node_id.side_effect = None
    get_node_id.return_value = 1
    nodecontrol.node_control(CONTROL_URI, barrier=True)
    assert get_node_id.call_count == 1
