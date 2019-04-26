import pytest

from calvinservices.actorstore.store import Store
from calvin.common import metadata_proxy as mdproxy

@pytest.fixture(scope='module')
def store():
    """Provide an instance of actor store"""
    store = mdproxy.ActorMetadataProxy('local')
    return store
    
@pytest.fixture(scope='module')
def actor_properties_schema():
    """Provide JSONSchema that actor properties must comply with """
    return Store.actor_properties_schema    

