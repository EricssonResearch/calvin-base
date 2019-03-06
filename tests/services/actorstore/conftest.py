import pytest

from calvinservices.actorstore.store import Store

@pytest.fixture(scope='module')
def store():
    """Provide an instance of actor store"""
    store = Store()
    return store
    
@pytest.fixture(scope='module')
def actor_properties_schema():
    """Provide JSONSchema that actor properties must comply with """
    return Store.actor_properties_schema    

