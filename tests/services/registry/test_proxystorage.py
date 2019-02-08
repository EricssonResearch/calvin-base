import os
import json
import time

import pytest
import requests

@pytest.fixture(scope="module")
def _proxy_storage_system(start_registry, start_runtime, start_process):
    """
    Setup actorstore and runtimes for the duration of the test module and
    guarantee teardown afterwards (yield fixture).
    Runtime defaults to local (internal) registry.
    """
    # Setup
    # REST registry on http://localhost:4998
    registry_proc = start_registry()
    # This is the proxy server on port 5000/5001
    time.sleep(1)
    os.environ["CALVIN_GLOBAL_STORAGE_TYPE"] = '"rest"'
    server_rt_proc = start_runtime()
    time.sleep(1)
    # This is the proxy server on port 5000/5001
    os.environ["CALVIN_GLOBAL_STORAGE_TYPE"] = '"proxy"'
    os.environ["CALVIN_GLOBAL_STORAGE_PROXY"] = '"calvinip://localhost:5000"'
    client_rt_proc = start_process("csruntime -n localhost -p 5002 -c 5003")
    time.sleep(2)
        
    # Run tests
    yield
    
    # Teardown
    client_rt_proc.terminate()
    server_rt_proc.terminate()
    registry_proc.terminate()
    
def test_simple(_proxy_storage_system, control_api):
    print control_api.get_node_id("http://localhost:5001")
    print control_api.get_node_id("http://localhost:5003")
    res = requests.get("http://localhost:4998/dumpstorage")
    print json.dumps(res.json(), indent=4)
    print control_api.get_node_id("http://localhost:5001")
    print control_api.get_node_id("http://localhost:5003")
    res = requests.get("http://localhost:4998/dumpstorage")
    print json.dumps(res.json(), indent=4)
    
    