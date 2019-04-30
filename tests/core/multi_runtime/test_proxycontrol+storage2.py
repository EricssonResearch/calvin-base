import json

import pytest


#
# N.B. The system config requires that $refs definition appear before use
#      Here we work around that to allow rt1 to use rt2 as registry proxy by
#      specifying rt2rt_port in rt2 and explicitly use that in the registry
#      definition in rt1
#
# FIXME: Add two pass parsing of configs in orchestration to remove limitation.
#
system_config = r"""
- class: REGISTRY
  name: registry
  port: 4998
  type: REST
- class: RUNTIME
  name: rt1
  registry:
    uri: calvinip://127.0.0.1:5000
    type: proxy
- class: RUNTIME
  rt2rt_port: 5000
  name: rt2
  registry: $registry
  control_proxy: $rt1
"""

@pytest.mark.skip(reason="Enable when problem with proxy runtimes is fixed")
def test_id(system_setup, execute_cmd_check_output):
    # Check sanity
    rt1_uri = system_setup['rt1']['uri']
    rt1_id = execute_cmd_check_output(("cscontrol", rt1_uri, "id"))
    rt1_id = rt1_id.strip('"')
    assert rt1_id == system_setup['rt1']['node_id']

    # Find ids of nodes connected to rt1, i.e. rt2_id
    res = execute_cmd_check_output(("cscontrol", rt1_uri, "nodes", "list"))
    node_ids = json.loads(res)
    assert len(node_ids) == 1
    rt2_id = node_ids[0]
    assert rt2_id != rt1_id

    # Get info on rt2 from registry
    res = execute_cmd_check_output(("cscontrol", rt1_uri, "nodes", "info", rt2_id))
    info = json.loads(res)
    rt2_uris = info["control_uris"]
    assert len(rt2_uris) == 1
    rt2_uri = rt2_uris[0]

    # verify that rt2 can be queried **using rt1 as proxy**
    res = execute_cmd_check_output(("cscontrol", rt2_uri, "nodes", "list"))
    node_ids = json.loads(res)
    assert len(node_ids) == 1
    assert node_ids[0] == rt1_id
