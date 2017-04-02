from calvin.calvinsys.integration.nest import NestIntegration, NotFoundException, \
    LogInException

import json as js
import pytest
from calvin.utilities.calvinlogger import get_logger

"""
Configuration file for automated testing. Change with your credentials file
NEST_CONFIG_DIR = $PATHTO/yourcredentials.json

The file has to be structured like the following

{
    "user": "<NEST EMAIL/USERNAME>",
    "pass": "<YOUR PASSWORD>"
}
"""
NEST_CONFIG_DIR = '/home/emirkomo/projects/internship/calvin-base/calvin/calvinsys/integration/tests/credentials.json'

"""
run py.test test_nest.py --runslow
if it fails multiple times, specifically because of LogInException where not due it's Nest
Cloud messing with multiple and sequential logins.
[TODO] paramterize tests
"""
_log = get_logger(__name__)


def login():
        json_content =open(NEST_CONFIG_DIR).read()
        json = js.loads(json_content)
        nest_int = NestIntegration()
        nest_int.login(json['user'], json['pass'])
        return nest_int

@pytest.mark.slow
def test_correct_login():
    json_content =open(NEST_CONFIG_DIR).read()
    json = js.loads(json_content)
    nest_int = NestIntegration(1,2)
    assert nest_int.login(json['user'], json['pass']) is True

@pytest.mark.slow
def test_wrong_login():
    nest_int = NestIntegration(1,2)
    assert nest_int.login('lol','lol') is False

@pytest.mark.slow
def test_list_structures(app):
    nest = app.nest_object
    _log.info(app.nest_object.nest.user)
    assert nest.list_structures() != []

@pytest.mark.slow
def test_list_devices(app):
    nest = app.nest_object
    assert nest.list_devices() != []

@pytest.mark.slow
def test_correct_list_devices_by_structure(app):
    nest = app.nest_object
    print nest.nest.user
    assert nest.list_devices_by_structure('HomeTest') is not None

@pytest.mark.slow
def test_wrong_list_devices_by_structure(app):
    nest = app.nest_object
    with pytest.raises(NotFoundException):
        nest.list_devices_by_structure('HomeTessss')

@pytest.mark.slow
def test_correct_device_by_name(app):
    nest = app.nest_object
    assert nest.get_device_by_name('DFF9') is not None

@pytest.mark.slow
def test_wrong_device_by_name(app):
    nest = app.nest_object
    assert nest.get_device_by_name('1234') is  None

@pytest.mark.slow
def test_correct_device_property(app):
    nest = app.nest_object
    assert nest.get_property('DFF9', 'temperature') is not None

@pytest.mark.slow
def test_wrong_device_property(app):
    nest = app.nest_object
    with pytest.raises(AttributeError):
        nest.get_property('DFF9', 'idonotexist')

@pytest.mark.slow
def test_nonexisting_device_property(app):
    nest = app.nest_object
    with pytest.raises(NotFoundException):
        nest.get_property('1234', 'idonotexist')

@pytest.mark.slow
def test_correct_set_device_property(app):
    nest = app.nest_object
    test_val = 'imatestvalue'
    device = '4A32'
    prop = 'name'
    nest.set_property(device, prop, test_val)

    #this works only for the name property, the fastest to check
    assert nest.get_property(test_val, prop) == test_val
    #assert nest.get_property(device, prop) == test_val


@pytest.mark.slow
def test_wrong_set_device_property(app):
    nest = app.nest_object
    with pytest.raises(NotFoundException):
        nest.set_property('XXXX', 'idonotexist','falsevalue')







