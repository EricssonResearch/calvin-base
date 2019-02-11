import os
import json
import time

import pytest
import requests

@pytest.fixture(scope="function")
def _proxy_storage_system(monkeypatch, start_registry, start_runtime, stop_process):
    """
    Setup actorstore and runtimes for the duration of the test module and
    guarantee teardown afterwards (yield fixture).
    Runtime defaults to local (internal) registry.
    """
    # Setup
    # REST registry on http://localhost:4998
    registry_proc = start_registry()
    # This is the proxy server on port 5000/5001
    # time.sleep(1)
    # os.environ["CALVIN_GLOBAL_STORAGE_TYPE"] = '"rest"'
    monkeypatch.setenv("CALVIN_GLOBAL_STORAGE_TYPE", '"rest"')
    server_rt_proc = start_runtime(5000, 5001)
    # server_rt_proc = start_process("csruntime -n localhost -l ANALYZE -f server.log")
    # time.sleep(1)
    # This is the proxy client on port 5002/5003
    # os.environ["CALVIN_GLOBAL_STORAGE_TYPE"] = '"proxy"'
    # os.environ["CALVIN_GLOBAL_STORAGE_PROXY"] = '"calvinip://localhost:5000"'
    monkeypatch.setenv("CALVIN_GLOBAL_STORAGE_TYPE", '"proxy"')
    monkeypatch.setenv("CALVIN_GLOBAL_STORAGE_PROXY", '"calvinip://localhost:5000"')
    # client_rt_proc = start_process("csruntime -n localhost -p 5002 -c 5003")
    client_rt_proc = start_runtime(5002, 5003)
    # client_rt_proc = start_process("csruntime -n localhost -p 5002 -c 5003 -l ANALYZE -f client.log")
    time.sleep(4)
        
    # Run tests
    yield
    
    # Teardown
    # control_api.quit("http://localhost:{}".format(5003), method="now")
    # control_api.quit("http://localhost:{}".format(5001), method="now")
    stop_process(client_rt_proc)
    stop_process(server_rt_proc)
    stop_process(registry_proc)
    
    
def test_simple(_proxy_storage_system, control_api):
    # We have two runtimes with identical capabilities, 
    # but one is proxy server and one is proxy client.
    # Thus, the 'supernode' information in the registry will reflact that.
    # Use the above facts for a simple sanity test of proxy storage 
    status, response = control_api.get_node_id("http://localhost:5001")
    assert status == 200
    server_id = response['id']
    status, response = control_api.get_node_id("http://localhost:5003")
    assert status == 200
    client_id = response['id']
    res = requests.get("http://localhost:4998/dumpstorage")
    db = res.json()
    key_value_db, indexed_db = db
    # print json.dumps(key_value_db, indent=4)
    
    assert 'node-{}'.format(server_id) in key_value_db
    assert 'node-{}'.format(client_id) in key_value_db

    assert indexed_db["(u'supernode', u'0')"] == [client_id]
    assert indexed_db["(u'supernode', u'0', u'1')"] == [server_id]

    assert all([set(value) == set([server_id, client_id]) for key, value in indexed_db.items() if not key.startswith("(u'supernode',")])
