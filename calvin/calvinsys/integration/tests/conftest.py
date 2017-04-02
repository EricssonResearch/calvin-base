import pytest
from calvin.calvinsys.integration.nest import NestIntegration
from calvin.calvinsys.integration.tests.test_nest import NEST_CONFIG_DIR
from calvin.utilities.calvinlogger import get_logger

import json as js

_log = get_logger(__name__)


def login():
        json_content =open(NEST_CONFIG_DIR).read()
        json = js.loads(json_content)
        nest_int = NestIntegration(1,2)
        nest_int.login(json['user'], json['pass'])
        return nest_int

def pytest_configure(config):
    config.app = NestContainer()

def pytest_runtest_teardown(item):
    if item.name == 'test_correct_set_device_property':
        item.config.app.nest_object.set_property("imatestvalue", "name", "4A32")
        _log.info("Changes reverted")


@pytest.fixture(scope="session")
def app(request):
    return request.config.app

class NestContainer(object):

    def __init__(self):
        self.nest_object = login()
        _log.info("initialized")
