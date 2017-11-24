import pytest
import unittest
from mock import Mock
from calvin.runtime.north import scheduler

class TestBase(unittest.TestCase):

    def setUp(self):
        actor_manager = Mock()
        actor_manager.enabled_actors = Mock(return_value=[1, 3, 7])
        node = Mock()
        self.scheduler = scheduler.Onebyone_Scheduler(node, actor_manager) 

    def tearDown(self):
        pass

class SchedulerSanityCheck(TestBase):

    def test_sanity(self):
        assert self.scheduler.actor_mgr.enabled_actors() == [1, 3, 7]
        
class SchedulerCheckStrategy(TestBase):

    def test_simple(self):
        assert False
