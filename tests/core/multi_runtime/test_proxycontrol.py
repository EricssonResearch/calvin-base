import pytest

# FIXME: control_proxy: $rt1

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
  rt2rt_port: 5000
  port: 5001
  registry: $registry
- class: RUNTIME
  actorstore: $actorstore
  name: rt2
  registry: $registry
  config:
    global:
      control_proxy: calvinip://127.0.0.1:5000
"""

def test_id(system_setup, execute_cmd_check_output):
    uri = system_setup['rt1']['uri']
    res = execute_cmd_check_output(("cscontrol", uri, "id"))
    res = res.strip('"')
    assert res == system_setup['rt1']['node_id']

    