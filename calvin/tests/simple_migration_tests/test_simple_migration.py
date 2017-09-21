# -*- coding: utf-8 -*-
import pytest
import time
import glob
import os.path
import functools
from calvin.requests import request_handler

handler = request_handler.RequestHandler()
path, fname = os.path.split(os.path.realpath(__file__))
applications = glob.glob(path + "/*.calvin")

def deploy(rt, script_name):
    with open(script_name, "r") as fp:
        script = fp.read()
    return handler.deploy_application(rt, script_name, script)

def migrate_actor(rt, actor_id, dst_rt):
    return handler.migrate(rt, actor_id, dst_rt)

def start_runtime(address, port, controlport, attributes, environment, logfile):
    import subprocess
    import json
    import os
    env = os.environ.copy()
    env.update(environment)
    return subprocess.Popen(["csruntime", "--host", "%s" % address, "--port", "%s" % port, "--controlport", "%s" % controlport, "--logfile", logfile, "--attr", json.dumps(attributes)], env=env)

def cleanup(logpath):
    import os
    os.remove(os.path.join(logpath, "runtime-1.log"))
    os.remove(os.path.join(logpath, "runtime-2.log"))
    os.rmdir(logpath)
    
@pytest.fixture(scope="module")
def runtimes(request):
    import json
    import tempfile
    
    path = tempfile.mkdtemp()
    
    runtime_1 = {
        "address": "localhost",
        "port": 5000,
        "controlport": 5001,
        "attributes": {"public":{"runtime":{"attribute":"runtime-1 attribute"}},"indexed_public":{"node_name":{"name":"calvin-1"},"address":{"locality":"Malmö"}}},
        "environment": {"CALVIN_GLOBAL_STORAGE_TYPE": json.dumps("local")},
        "logfile": "{}/runtime-1.log".format(path)
    }

    runtime_2 = {
        "address": "localhost",
        "port": 5002,
        "controlport": 5003,
        "attributes": {"public":{"runtime":{"attribute":"runtime-2 attribute"}},"indexed_public":{"node_name":{"name":"calvin-2"},"address":{"locality":"Lund"}}},
        "environment": {"CALVIN_GLOBAL_STORAGE_TYPE": json.dumps("proxy"), "CALVIN_GLOBAL_STORAGE_PROXY": json.dumps("calvinip://{}:{}".format(runtime_1["address"], runtime_1["port"]))},
        "logfile": "{}/runtime-2.log".format(path)

    }
    runtime_1["process"] = start_runtime(**runtime_1)
    runtime_2["process"] = start_runtime(**runtime_2)
    runtime_1["handle"] = request_handler.get_runtime("http://{}:{}".format(runtime_1["address"], runtime_1["controlport"]))
    runtime_2["handle"] = request_handler.get_runtime("http://{}:{}".format(runtime_2["address"], runtime_2["controlport"]))

    retries = 0
    while retries < 10:
        try:
            runtime_1["id"] = handler.get_node_id(runtime_1["handle"])
            runtime_2["id"] = handler.get_node_id(runtime_2["handle"])
            break
        except Exception as e:
            # retry
            print("Retrying because {}".format(e))
            retries += 1
            time.sleep(1.0)
    assert retries < 10   
    # teardown
    request.addfinalizer(functools.partial(handler.quit, runtime_1["handle"]))
    request.addfinalizer(functools.partial(handler.quit, runtime_2["handle"]))
    request.addfinalizer(functools.partial(cleanup, path))
    return runtime_1, runtime_2
    
def migrate_actors(runtime_1, runtime_2, actors):
    for actor_name, actor_id in actors.items():
        migrate_actor(runtime_1["handle"], actor_id, runtime_2["id"])
        time.sleep(1.0)
        migrate_actor(runtime_2["handle"], actor_id, runtime_1["id"])
        time.sleep(1.0)

@pytest.mark.first
@pytest.mark.parametrize("application", applications)
def test_application(runtimes, application):
    runtime_1, runtime_2 = runtimes
    try:
        app_info = deploy(runtime_1["handle"], application)
        actors = app_info.get("actor_map", {})
        migrate_actors(runtime_1, runtime_2, actors)
        handler.delete_application(runtime_1["handle"], app_info["application_id"])
    except Exception as e:
        print("Deployment/migration of application {} failed: {}".format(application, e))
        raise e
    

@pytest.mark.second
def test_runtime_log(runtimes):
    rt1, rt2 = runtimes
    for logfile in [rt1["logfile"], rt2["logfile"]]:
        with open(logfile, "r") as fp:
            lines = fp.read().splitlines()
            for line in lines:
                if line.find("xception") !=-1:
                    raise Exception("Error encountered: {}".format(line))
