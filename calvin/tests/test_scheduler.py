import pytest
import unittest
from mock import Mock
from calvin.runtime.north import scheduler, calvinsys
from calvin.runtime.north.actormanager import ActorManager
from calvin.runtime.north.plugins.port import queue
from calvin.runtime.north.plugins.port.endpoint import LocalOutEndpoint, LocalInEndpoint


def create_actor(kind, args):
    node = Mock()
    actor_manager = ActorManager(node)
    actor_id = actor_manager.new(kind, args)
    actor = actor_manager.actors[actor_id]
    actor._calvinsys = Mock()
    return actor


class TestBase(unittest.TestCase):

    def setUp(self):
        node = Mock()
        cs = calvinsys.get_calvinsys()
        cs.init(node)
        actor_manager = Mock()
        actor_manager.enabled_actors = Mock(return_value=[1, 3, 7])
        self.scheduler = scheduler.Onebyone_Scheduler(node, actor_manager) 
        node.sched = self.scheduler

    def tearDown(self):
        pass

class SchedulerSanityCheck(TestBase):

    def test_sanity(self):
        assert self.scheduler.actor_mgr.enabled_actors() == [1, 3, 7]
        
class SchedulerCheckStrategy(TestBase):

    def test_simple(self):
        # Create actors
        src = create_actor('std.Constant', {"data":42, "name":"src"})
        filter = create_actor('std.Identity', {"name":"filter"})
        snk = create_actor('flow.Terminator', {"name":"snk"})
                    
        # Get get the ports
        src_outport = src.outports['token']
        filter_inport = filter.inports['token']  
        filter_outport = filter.outports['token']
        snk_inport = snk.inports['void']
        
        # Set the queue types and length for each port
        src_outport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
        filter_inport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))
        filter_outport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "out"}, {}))
        snk_inport.set_queue(queue.fanout_fifo.FanoutFIFO({'queue_length': 4, 'direction': "in"}, {}))
        
        # Create endpoints
        src_out_ep = LocalOutEndpoint(src_outport, filter_inport)
        filter_in_ep = LocalInEndpoint(filter_inport, src_outport)
        filter_out_ep = LocalOutEndpoint(filter_outport, snk_inport)
        snk_in_ep = LocalInEndpoint(snk_inport, filter_outport)
        
        # Attach the enpoints to the ports
        src_outport.attach_endpoint(src_out_ep)
        filter_inport.attach_endpoint(filter_in_ep)
        filter_outport.attach_endpoint(filter_out_ep)
        snk_inport.attach_endpoint(snk_in_ep)
                
        assert src.name == "src"    
        assert filter.name == "filter"          
        # Verify that src.token is connected to filter.token
        assert len(src.outports['token'].endpoints) == 1     
        assert src.outports['token'].endpoints[0].peer_port.owner.name == filter.name 
        assert src.outports['token'].endpoints[0].peer_port.owner == filter
        assert src.outports['token'].endpoints[0].peer_port.name == "token"
        assert src.outports['token'].endpoints[0].peer_port == filter.inports['token']
          
