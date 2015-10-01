# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import time
import multiprocessing
from calvin.runtime.north import calvin_node
from calvin.Tools import cscompiler as compiler
from calvin.Tools import deployer
import pytest
from calvin.utilities import utils
from calvin.utilities.nodecontrol import dispatch_node
from calvin.utilities import calvinuuid
from warnings import warn
from calvin.utilities.attribute_resolver import format_index_string
import socket
import os
import json
try:
    ip_addr = os.environ["CALVIN_TEST_LOCALHOST"]
except:
    import socket
    ip_addr = socket.gethostbyname(socket.gethostname())


def absolute_filename(filename):
    import os.path
    return os.path.join(os.path.dirname(__file__), filename)

class CalvinNodeTestBase(unittest.TestCase):

    def setUp(self):
        self.rt1, _ = dispatch_node("calvinip://%s:5000" % (ip_addr,), "http://%s:5003" % ip_addr,
             attributes={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode1'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}})

        self.rt2, _ = dispatch_node("calvinip://%s:5001" % (ip_addr,), "http://%s:5004" % ip_addr,
             attributes={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner1'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode2'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 1}}})
        self.rt3, _ = dispatch_node("calvinip://%s:5002" % (ip_addr,), "http://%s:5005" % ip_addr,
             attributes={'indexed_public':
                  {'owner':{'organization': 'org.testexample', 'personOrGroup': 'testOwner2'},
                   'node_name': {'organization': 'org.testexample', 'name': 'testNode3'},
                   'address': {'country': 'SE', 'locality': 'testCity', 'street': 'testStreet', 'streetNumber': 2}}})

    def tearDown(self):
        utils.quit(self.rt1)
        utils.quit(self.rt2)
        utils.quit(self.rt3)
        time.sleep(0.2)
        for p in multiprocessing.active_children():
            p.terminate()
        time.sleep(0.2)


@pytest.mark.slow
class TestDeployScript(CalvinNodeTestBase):

    def setUp(self):
        super(TestDeployScript, self).setUp()
        self.test_script_dir = absolute_filename('scripts/')

    @pytest.mark.slow
    def testDeploySimple(self):
        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs'])
        time.sleep(2)
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(self.test_script_dir+"test_deploy1.calvin"), attr=None,
                                reqs=self.test_script_dir+"test_deploy1.deployjson")
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        time.sleep(2)
        actors = [utils.get_actors(self.rt1), utils.get_actors(self.rt2), utils.get_actors(self.rt3)]
        # src -> rt2, sum -> rt2, snk -> rt3
        assert result['actor_map']['test_deploy1:src'] in actors[1]
        assert result['actor_map']['test_deploy1:sum'] in actors[1]
        assert result['actor_map']['test_deploy1:snk'] in actors[2]
        utils.delete_application(self.rt1, result['application_id'])
        time.sleep(0.5)

    @pytest.mark.slow
    def testDeployLongActorChain(self):
        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs'])
        time.sleep(2)
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(self.test_script_dir+"test_deploy2.calvin"), attr=None,
                                reqs=self.test_script_dir+"test_deploy2.deployjson")
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        time.sleep(2)
        actors = [utils.get_actors(self.rt1), utils.get_actors(self.rt2), utils.get_actors(self.rt3)]
        # src -> rt1, sum[1:8] -> [rt1, rt2, rt3], snk -> rt3
        assert result['actor_map']['test_deploy2:src'] in actors[0]
        assert result['actor_map']['test_deploy2:snk'] in actors[2]
        sum_list=[result['actor_map']['test_deploy2:sum%d'%i] for i in range(1,9)]
        sum_place = [0 if a in actors[0] else 1 if a in actors[1] else 2 if a in actors[2] else -1 for a in sum_list]
        assert not any([p==-1 for p in sum_place])
        assert all(x<=y for x, y in zip(sum_place, sum_place[1:]))
        utils.delete_application(self.rt1, result['application_id'])
        time.sleep(0.5)

    @pytest.mark.slow
    def testDeployComponent(self):
        from calvin.Tools.cscontrol import control_deploy as deploy_app
        from collections import namedtuple
        DeployArgs = namedtuple('DeployArgs', ['node', 'attr', 'script','reqs'])
        time.sleep(2)
        args = DeployArgs(node='http://%s:5003' % ip_addr,
                          script=open(self.test_script_dir+"test_deploy3.calvin"), attr=None,
                                reqs=self.test_script_dir+"test_deploy3.deployjson")
        result = {}
        try:
            result = deploy_app(args)
        except:
            raise Exception("Failed deployment of app %s, no use to verify if requirements fulfilled" % args.script.name)
        time.sleep(2)
        actors = [utils.get_actors(self.rt1), utils.get_actors(self.rt2), utils.get_actors(self.rt3)]
        # src:(first, second) -> rt1, sum -> rt2, snk -> rt3
        assert result['actor_map']['test_deploy3:src:first'] in actors[0]
        assert result['actor_map']['test_deploy3:src:second'] in actors[0]
        assert result['actor_map']['test_deploy3:sum'] in actors[1]
        assert result['actor_map']['test_deploy3:snk'] in actors[2]
        utils.delete_application(self.rt1, result['application_id'])
        time.sleep(0.5)
