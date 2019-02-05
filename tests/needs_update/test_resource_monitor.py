# -*- coding: utf-8 -*-

from calvin.runtime.north import storage
from calvin.requests import calvinresponse
import calvin.utilities.calvinconfig
from calvin.runtime.north.resource_monitor.cpu import CpuMonitor
from calvin.runtime.north.resource_monitor.memory import MemMonitor
from calvin.runtime.south.async import threads
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities.attribute_resolver import AttributeResolver
from calvin.tests.helpers_twisted import create_callback, wait_for
import calvin.tests
import pytest
import time

_conf = calvin.utilities.calvinconfig.get()

# So it skipps if we dont have twisted plugin
def _dummy_inline(*args):
    pass

if not hasattr(pytest, 'inlineCallbacks'):
    pytest.inlineCallbacks = _dummy_inline

@pytest.mark.essential
@pytest.mark.skipif(pytest.inlineCallbacks == _dummy_inline,
                    reason="No inline twisted plugin enabled, please use --twisted to py.test")


class TestCpuMonitor(object):
    CPUAVAIL_INDEX_BASE = ['node', 'resource', 'cpuAvail']
    CPUTOTAL_INDEX_BASE = ['node', 'attribute', 'cpuTotal']

    @pytest.inlineCallbacks
    def setup(self):
        _conf.set('global', 'storage_type', 'local')
        self.node = calvin.tests.TestNode(["127.0.0.1:5000"])
        self.node.attributes = AttributeResolver({"indexed_public": {"cpuTotal": "1" }})
        self.storage = storage.Storage(self.node)
        self.cpu = CpuMonitor(self.node.id, self.storage)
        self.done = False
        self.storage.add_node(self.node)
        yield threads.defer_to_thread(time.sleep, .01)

    @pytest.inlineCallbacks
    def teardown(self):
        yield threads.defer_to_thread(time.sleep, .001)

    def _test_done(self):
        return self.done

    def cb(self, key, value):
        self.get_ans = value
        self.done = True

    def cb2(self, value):
        self.get_ans = value
        self.done = True

    @pytest.inlineCallbacks
    def test_avail_invalid(self):
        """
        Verify invalid values for CPU avail
        """
        for i in [-1, 40, 101]:
            self.done = False
            self.cpu.set_avail(i, CalvinCB(self.cb))
            yield wait_for(self._test_done)
            assert self.get_ans == False

    @pytest.inlineCallbacks
    def test_avail_valid(self):
        """
        Test valid values for CPU avail.
        Verify if storage is as expected
        """
        values = [0, 25, 50, 75, 100]
        for i in values:
            # verify set return
            self.done = False
            self.cpu.set_avail(i, CalvinCB(self.cb))
            yield wait_for(self._test_done)
            assert self.get_ans == True

            # verify nodeCpuAvail in DB
            self.done = False
            self.storage.get(prefix="nodeCpuAvail-", key=self.node.id, cb=CalvinCB(self.cb))
            yield wait_for(self._test_done)
            assert self.get_ans == i

            # verify index ok and present for level i
            self.done = False
            self.storage.get_index(index=self.CPUAVAIL_INDEX_BASE + map(str, values[:values.index(i)+1]), root_prefix_level=2, cb=CalvinCB(self.cb2))
            yield wait_for(self._test_done)
            assert self.node.id in self.get_ans

    @pytest.inlineCallbacks
    def test_avail_change(self):
        """
        Verify if indexes are ok after a change in CPU avail.
        Old value must be erased from indexes
        """
        self.cpu.set_avail(50)
        self.cpu.set_avail(25, CalvinCB(self.cb))
        yield wait_for(self._test_done)
        assert self.get_ans == True

        # node id must not be present at level 50, only at 25
        self.done = False
        self.storage.get_index(index=self.CPUAVAIL_INDEX_BASE + ['0', '25', '50'], root_prefix_level=2, cb=CalvinCB(self.cb2))
        yield wait_for(self._test_done)
        assert self.get_ans == []

    @pytest.inlineCallbacks
    def test_stop_node(self):
        """
        Verify if indexes are cleared after node stop
        Old value must be erased from indexes
        """
        self.cpu.set_avail(25, CalvinCB(self.cb))
        yield wait_for(self._test_done)
        assert self.get_ans == True

        self.done = False
        self.storage.get_index(index=self.CPUAVAIL_INDEX_BASE + ['0', '25'], root_prefix_level=2, cb=CalvinCB(self.cb2))
        yield wait_for(self._test_done)
        assert self.node.id in self.get_ans

        self.cpu.stop()
        self.storage.delete_node(self.node)

        # nodeCpuAvail must not exist
        self.done = False
        self.storage.get(prefix="nodeCpuAvail-", key=self.node.id, cb=CalvinCB(self.cb))
        yield wait_for(self._test_done)
        assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.NOT_FOUND

        # node id must not be present at level 25
        self.done = False
        self.storage.get_index(index=self.CPUAVAIL_INDEX_BASE + ['0', '25'], root_prefix_level=2, cb=CalvinCB(self.cb2))
        yield wait_for(self._test_done)
        assert self.get_ans == []

        # no node in total indexes
        self.done = False
        self.storage.get_index(index=self.CPUTOTAL_INDEX_BASE + ['1'], root_prefix_level=2, cb=CalvinCB(self.cb2))
        yield wait_for(self._test_done)
        assert self.get_ans == []

    @pytest.inlineCallbacks
    def test_total_valid(self):
        """
        Test valid values for CPU power.
        Verify if storage is as expected
        """
        values = ["1", "1000", "100000", "1000000", "10000000"]
        for i in values:
            # verify set return
            self.done = False
            self.node.attributes = AttributeResolver({"indexed_public": {"cpuTotal": i }})
            self.storage.add_node(self.node, cb=self.cb)
            yield wait_for(self._test_done)
            assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK

            # verify index ok and present for level i
            self.done = False
            self.storage.get_index(index=self.CPUTOTAL_INDEX_BASE + map(str, values[:values.index(i)+1]), root_prefix_level=2, cb=CalvinCB(self.cb2))
            yield wait_for(self._test_done)
            assert self.node.id in self.get_ans


class TestMemMonitor(object):
    MEMAVAIL_INDEX_BASE = ['node', 'resource', 'memAvail']
    MEMTOTAL_INDEX_BASE = ['node', 'attribute', 'memTotal']

    @pytest.inlineCallbacks
    def setup(self):
        _conf.set('global', 'storage_type', 'local')
        self.node = calvin.tests.TestNode(["127.0.0.1:5000"])
        self.node.attributes = AttributeResolver({"indexed_public": {"memTotal": "10G" }})
        self.storage = storage.Storage(self.node)
        self.mem = MemMonitor(self.node.id, self.storage)
        self.done = False
        self.storage.add_node(self.node)
        yield threads.defer_to_thread(time.sleep, .01)

    @pytest.inlineCallbacks
    def teardown(self):
        yield threads.defer_to_thread(time.sleep, .001)

    def _test_done(self):
        return self.done

    def cb(self, key, value):
        self.get_ans = value
        self.done = True

    def cb2(self, value):
        self.get_ans = value
        self.done = True

    @pytest.inlineCallbacks
    def test_avail_invalid(self):
        """
        Verify invalid values for RAM avail
        """
        for i in [-1, 40, 101]:
            self.done = False
            self.mem.set_avail(i, CalvinCB(self.cb))
            yield wait_for(self._test_done)
            assert self.get_ans == False

    @pytest.inlineCallbacks
    def test_avail_valid(self):
        """
        Test valid values for RAM avail.
        Verify if storage is as expected
        """
        values = [0, 25, 50, 75, 100]
        for i in values:
            # verify set return
            self.done = False
            self.mem.set_avail(i, CalvinCB(self.cb))
            yield wait_for(self._test_done)
            assert self.get_ans == True

            # verify nodeMemAvail in DB
            self.done = False
            self.storage.get(prefix="nodeMemAvail-", key=self.node.id, cb=CalvinCB(self.cb))
            yield wait_for(self._test_done)
            assert self.get_ans == i

            # verify index ok and present for level i
            self.done = False
            self.storage.get_index(index=self.MEMAVAIL_INDEX_BASE + map(str, values[:values.index(i)+1]), root_prefix_level=2, cb=CalvinCB(self.cb2))
            yield wait_for(self._test_done)
            assert self.node.id in self.get_ans

    @pytest.inlineCallbacks
    def test_avail_change(self):
        """
        Verify if indexes are ok after a change in RAM avail.
        Old value must be erased from indexes
        """
        self.mem.set_avail(50)
        self.mem.set_avail(25, CalvinCB(self.cb))
        yield wait_for(self._test_done)
        assert self.get_ans == True

        # node id must not be present at level 50, only at 25
        self.done = False
        self.storage.get_index(index=self.MEMAVAIL_INDEX_BASE + ['0', '25', '50'], root_prefix_level=2, cb=CalvinCB(self.cb2))
        yield wait_for(self._test_done)
        assert self.get_ans == []

    @pytest.inlineCallbacks
    def test_stop_node(self):
        """
        Verify if indexes are cleared after node stop
        Old value must be erased from indexes
        """
        self.mem.set_avail(25, CalvinCB(self.cb))
        yield wait_for(self._test_done)
        assert self.get_ans == True

        self.done = False
        self.storage.get_index(index=self.MEMAVAIL_INDEX_BASE + ['0', '25'], root_prefix_level=2, cb=CalvinCB(self.cb2))
        yield wait_for(self._test_done)
        assert self.node.id in self.get_ans

        self.mem.stop()
        self.storage.delete_node(self.node)

        # nodeMemAvail must not exist
        self.done = False
        self.storage.get(prefix="nodeMemAvail-", key=self.node.id, cb=CalvinCB(self.cb))
        yield wait_for(self._test_done)
        assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.NOT_FOUND

        # node id must not be present at level 25
        self.done = False
        self.storage.get_index(index=self.MEMAVAIL_INDEX_BASE + ['0', '25'], root_prefix_level=2, cb=CalvinCB(self.cb2))
        yield wait_for(self._test_done)
        assert self.get_ans == []

        # no node in total indexes
        self.done = False
        self.storage.get_index(index=self.MEMTOTAL_INDEX_BASE + ['1K'], root_prefix_level=2, cb=CalvinCB(self.cb2))
        yield wait_for(self._test_done)
        assert self.get_ans == []

    @pytest.inlineCallbacks
    def test_total_valid(self):
        """
        Test valid values for total RAM.
        Verify if storage is as expected
        """
        values = ["1K", "100K", "1M", "100M", "1G", "10G"]
        for i in values:
            # verify set return
            self.done = False
            self.node.attributes = AttributeResolver({"indexed_public": {"memTotal": i }})
            self.storage.add_node(self.node, cb=self.cb)
            yield wait_for(self._test_done)
            assert isinstance(self.get_ans, calvinresponse.CalvinResponse) and self.get_ans == calvinresponse.OK

            # verify index ok and present for level i
            self.done = False
            self.storage.get_index(index=self.MEMTOTAL_INDEX_BASE + map(str, values[:values.index(i)+1]), root_prefix_level=2, cb=CalvinCB(self.cb2))
            yield wait_for(self._test_done)
            assert self.node.id in self.get_ans
