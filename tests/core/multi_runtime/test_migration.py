import time

import pytest

# TODO: 
# [ ] Create common fixture for this file and single_runtime/test_calvin.py
# [ ] Use the possibility to configure io.Print to send its recieved tokens
#     to a test-entity (over HTTP) so we can get events and use them to
#     control, and speed up, the tests. 


testlist = [
    (
        'test_simple_migration',
        r"""
            trigger : std.Trigger(data=true, tick=0.1)
            name : context.RuntimeName()
            out : test.Sink(store_tokens=1, quiet=1, active=true)

            trigger.data > name.trigger
            name.value > out.token
    
            rule rt1 : runtime_name(name="rt1")
            
            apply trigger, name, out : rt1
        """,
        ['out'],
        ['name'],
    ),
]


system_config = r"""
- class: REGISTRY
  name: registry
  port: 4998
  type: REST
- class: ACTORSTORE
  name: actorstore
  port: 4999
  type: REST
- class: RUNTIME
  actorstore: $actorstore
  name: rt1
  registry: $registry
- class: RUNTIME
  actorstore: $actorstore
  name: rt2
  registry: $registry
- class: RUNTIME
  actorstore: $actorstore
  name: rt3
  registry: $registry
"""


@pytest.fixture(scope='module', params=testlist)
def deploy_application(request, system_setup, deploy_app, destroy_app):
    deploy_rt_uri = system_setup['rt1']['uri']
    name, script, sinks, migrates = request.param
    app_info = deploy_app(deploy_rt_uri, script, name)
    app_id = app_info['application_id']
    actor_map = app_info['actor_map']
    sink_ids = [actor_map[name + ':' + sink] for sink in sinks]
    migrate_ids = [actor_map[name + ':' + migrate] for migrate in migrates]
    
    yield (deploy_rt_uri, sink_ids, migrate_ids, app_id)

    destroy_app(deploy_rt_uri, app_info)


def _get_report(control_api, rt_uri, sink_id):
    # We need to take care, since the actor might be migrating
    for retry in range(10):
        _, actor_info = control_api.get_actor(rt_uri, sink_id)
        node_id = actor_info['node_id']
        _, node_info = control_api.get_node(rt_uri, node_id)
        target_uri = node_info['control_uris'][0]
        status, actual = control_api.get_actor_report(target_uri, sink_id)
        if status == 200:
            break
        time.sleep(0.1)
    return actual
    

def _get_actual(control_api, rt_uri, sink_id, min_len):
    for retry in range(50):
        actual = _get_report(control_api, rt_uri, sink_id)
        if len(actual) >= min_len:
            break
        time.sleep(0.1)
    assert len(actual) >= min_len
    return actual

  
def test_sanity(deploy_application, control_api):
    deploy_rt_uri, sink_ids, migrate_ids, app_id = deploy_application
    _get_actual(control_api, deploy_rt_uri, sink_ids[0], 10)


def _move_req(destination_rt_name, actor_name, force_move):
    req = {
        "deploy_info": {
            "valid": True, 
            "requirements": {
                actor_name: [
                    {
                        "kwargs": {
                            "name": destination_rt_name
                        }, 
                        "type": "+", 
                        "op": "runtime_name"
                    }
                ], 
            },
            "move": force_move,
        },
    } 
    return req
    
       
def test_migration(deploy_application, control_api):
    deploy_rt_uri, sink_ids, migrate_ids, app_id = deploy_application
    output = _get_actual(control_api, deploy_rt_uri, sink_ids[0], 5)
    assert set(output) == set(['rt1'])
    
    reqs = _move_req('rt3', 'name', force_move=True)
    status, _ = control_api.migrate_application(deploy_rt_uri, app_id, reqs)
    output = _get_actual(control_api, deploy_rt_uri, sink_ids[0], len(output) + 10)
    assert set(output) == set(['rt1', 'rt3'])
    
    reqs = _move_req('rt2', 'name', force_move=True)
    status, _ = control_api.migrate_application(deploy_rt_uri, app_id, reqs)
    output = _get_actual(control_api, deploy_rt_uri, sink_ids[0], len(output) + 10)
    assert set(output) == set(['rt1', 'rt2', 'rt3'])
    
    
    
    
    
    