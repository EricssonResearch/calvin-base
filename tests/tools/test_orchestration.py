import pytest
import yaml

from tools.toolsupport import orchestration


def test_actorstore_setup():
    cfg = """
    - class: RUNTIME
      name: rt1
      actorstore: 
          uri: local
    """
    config = yaml.load(cfg, Loader=yaml.SafeLoader)
    sm = orchestration.SystemManager(config, start=False)
    assert sm.info['rt1']['actorstore'] == {'uri': 'local'}
    
    