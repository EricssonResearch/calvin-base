import pytest

system_config = r"""
- class: REGISTRY
  name: registry
  type: REST
- class: ACTORSTORE
  name: actorstore
  type: REST
- actorstore: $actorstore
  class: RUNTIME
  name: runtime1
  registry: $registry
- actorstore: $actorstore
  class: RUNTIME
  name: runtime2
  registry: $registry
- actorstore: $actorstore
  class: RUNTIME
  name: runtime3
  registry: $runtime1
"""

def test_setup(system_setup):
    assert len(system_setup) == 5
    
    