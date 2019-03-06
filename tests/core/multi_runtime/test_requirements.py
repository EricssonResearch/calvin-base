import time

import pytest


# TODO:
# [ ] Add remaining tests from needs_update/test_requirements.py
# [ ] Use fixture below as the generic deploy application fixture

system_config = """
- class: REGISTRY
  name: registry
  port: 4998
  type: REST
- class: ACTORSTORE
  name: actorstore
  port: 4999
  type: REST
- class: RUNTIME
  name: testNode1
  actorstore: $actorstore
  registry: $registry
  attributes:
    indexed_public:
      address:
        country: SE
        locality: testCity
        street: testStreet
        streetNumber: 1
      node_name:
        organization: org.testexample
      owner:
        organization: org.testexample
        personOrGroup: testOwner1   
- class: RUNTIME
  name: testNode2
  actorstore: $actorstore
  registry: $registry
  attributes:
    indexed_public:
      address:
        country: SE
        locality: testCity
        street: testStreet
        streetNumber: 1
      node_name:
        organization: org.testexample
      owner:
        organization: org.testexample
        personOrGroup: testOwner1
- class: RUNTIME
  name: testNode3
  actorstore: $actorstore
  registry: $registry
  attributes:
    indexed_public:
      address:
        country: SE
        locality: testCity
        street: testStreet
        streetNumber: 2
      node_name:
        organization: org.testexample
      owner:
        organization: org.testexample
        personOrGroup: testOwner2     
"""


def _get_actors(setup, control_api, actor_names):
    rt_uris = [setup[name]['uri'] for name in actor_names]
    actors = []
    for rt in rt_uris:
        status, alist = control_api.get_actors(rt)
        actors.append(alist) if status == 200 else []
    return actors

def _check_deploy1(setup, app_info, control_api):
    actors = _get_actors(setup, control_api, ['testNode1','testNode2','testNode3'])
    # src -> rt2, sum -> rt2, snk -> rt3
    assert app_info['actor_map']['deploy1:src'] in actors[1]
    assert app_info['actor_map']['deploy1:sum'] in actors[1]
    assert app_info['actor_map']['deploy1:snk'] in actors[2]
    
def _check_deploy2(setup, app_info, control_api):
    actors = _get_actors(setup, control_api, ['testNode1','testNode2','testNode3'])
    # src -> rt1, sum[1:8] -> [rt1, rt2, rt3], snk -> rt3
    assert app_info['actor_map']['deploy2:src'] in actors[0]
    assert app_info['actor_map']['deploy2:snk'] in actors[2]
    sum_list=[app_info['actor_map']['deploy2:sum{}'.format(i)] for i in range(1,9)]
    sum_place = [0 if a in actors[0] else 1 if a in actors[1] else 2 if a in actors[2] else -1 for a in sum_list]
    assert -1 not in sum_place # assert not any([p==-1 for p in sum_place])
    assert all(x<=y for x, y in list(zip(sum_place, sum_place[1:])))


def _check_deploy3(setup, app_info, control_api):
    actors = _get_actors(setup, control_api, ['testNode1','testNode2','testNode3'])
    # src:(first, second) -> rt1, sum -> rt2, snk -> rt3
    assert app_info['actor_map']['deploy3:src:first'] in actors[0]
    assert app_info['actor_map']['deploy3:src:second'] in actors[0]
    assert app_info['actor_map']['deploy3:sum'] in actors[1]
    assert app_info['actor_map']['deploy3:snk'] in actors[2]
        

testlist = [
    (
        'deploy1', 
        _check_deploy1,
        """
        src : std.CountTimer(start=1, sleep=0.1, steps=1000000000)
        sum : std.Sum()
        snk : test.Sink(store_tokens=false, active=true, quiet=false)

        src.integer > sum.integer
        sum.integer > snk.token

        rule src_rule : node_attr_match(index=["node_name", {"organization": "org.testexample", "name": "testNode1"}]) | node_attr_match(index=["node_name", {"organization": "org.testexample", "name": "testNode2"}])
        rule snk_rule : node_attr_match(index=["node_name", {"organization": "org.testexample", "name": "testNode3"}]) &~ current_node()
        rule sum_rule : node_attr_match(index=["node_name", {"organization": "org.testexample", "name": "testNode2"}])

        group firstgroup : src, sum

        apply src : src_rule & ~current_node()
        apply sum : sum_rule
        apply snk : snk_rule
        """
    ),
    (
        'deploy2', 
        _check_deploy2,
        """
        src : std.CountTimer(start=1, sleep=0.1, steps=1000000000)
        sum1 : std.Sum()
        sum2 : std.Sum()
        sum3 : std.Sum()
        sum4 : std.Sum()
        sum5 : std.Sum()
        sum6 : std.Sum()
        sum7 : std.Sum()
        sum8 : std.Sum()
        snk : test.Sink(store_tokens=false, active=true, quiet=false)

        src.integer > sum1.integer
        sum1.integer > sum2.integer
        sum2.integer > sum3.integer
        sum3.integer > sum4.integer
        sum4.integer > sum5.integer
        sum5.integer > sum6.integer
        sum6.integer > sum7.integer
        sum7.integer > sum8.integer
        sum8.integer > snk.token

        rule node1 : node_attr_match(index=["node_name", {"organization": "org.testexample", "name": "testNode1"}])
        rule node3 : node_attr_match(index=["node_name", {"organization": "org.testexample", "name": "testNode3"}])

        apply src : node1
        apply snk : node3
        apply sum1, sum2, sum3, sum4, sum5, sum6, sum7, sum8 : all_nodes()
        """
    ),
    (
        'deploy3', 
        _check_deploy3,
        """
        component TheSource() -> out {
          first: std.CountTimer(start=1, sleep=0.1, steps=1000000000)
          second: std.Identity(dump=false)

          first.integer > second.token
          second.token > .out
        }

        src : TheSource()
        sum : std.Sum()
        snk : test.Sink(store_tokens=false, active=true, quiet=false)

        src.out > sum.integer
        sum.integer > snk.token


        apply src : node_attr_match(index=["node_name", {"organization": "org.testexample", "name": "testNode1"}])
        apply sum : node_attr_match(index=["node_name", {"organization": "org.testexample", "name": "testNode2"}])
        apply snk : node_attr_match(index=["node_name", {"organization": "org.testexample", "name": "testNode3"}]) & ~current_node()
        """
    )
]
    

@pytest.fixture(scope='module', params=testlist, ids=lambda t: t[0])
def deploy_application(request, system_setup, deploy_app, destroy_app):
    deploy_rt_uri = system_setup['testNode1']['uri']
    name, checker, script = request.param
    app_info = deploy_app(deploy_rt_uri, script, name)

    yield (system_setup, app_info, checker)

    # Clean-up section
    destroy_app(deploy_rt_uri, app_info)


def test_deployment(deploy_application, control_api):
    setup, app_info, checker = deploy_application
    # FIXME: Adding some time for the registry to settle, add check instead.
    time.sleep(2)
    checker(setup, app_info, control_api)
    
    
    
    
    
    
    
    
    
    
    
    