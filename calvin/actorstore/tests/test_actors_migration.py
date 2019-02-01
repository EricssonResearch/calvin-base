# -*- coding: utf-8 -*-

import pytest
import unittest
import os
import time
from tempfile import mkstemp
from calvin.utilities.calvinlogger import get_logger
from calvin.tests import helpers
from calvin.requests.request_handler import RequestHandler

_log = get_logger(__name__)


class CalvinActorMigrationTestBase(unittest.TestCase):
    """ Base class for test actor migration. Based on CalvinTestBase but without the global variables """
    def setUp(self):
        self.request_handler = RequestHandler()
        self.test_type, [self.rt1, self.rt2, self.rt3] = helpers.setup_test_type(self.request_handler)

    def tearDown(self):
        helpers.teardown_test_type(self.request_handler, [self.rt1, self.rt2, self.rt3], self.test_type)

    def wait_for_migration(self, runtime, actors, retries=20):
        retry = 0
        if not isinstance(actors, list):
            actors = [actors]
        while retry < retries:
            try:
                current = self.request_handler.get_actors(runtime)
                if set(actors).issubset(set(current)):
                    break
                else:
                    _log.info("Migration not finished, retrying in %f" % (retry * 0.1,))
                    retry += 1
                    time.sleep(retry * 0.1)
            except Exception as e:
                _log.info("Migration not finished %s, retrying in %f" % (str(e), retry * 0.1,))
                retry += 1
                time.sleep(retry * 0.1)
        if retry == retries:
            _log.info("Migration failed, after %d retries" % (retry,))
            raise Exception("Migration failed")

    def migrate(self, source, dest, actor):
        self.request_handler.migrate(source, actor, dest.id)
        self.wait_for_migration(dest, [actor])


@pytest.mark.slow
class TestActorMigration(CalvinActorMigrationTestBase):
    def testRecTimer(self):
        """
        Simple test for RecTimer migration.
        Create a RecTimer actor and connect it to a source and a sink.
        Migrate it from runtime1 to runtime2
        """
        dut = self.request_handler.new_actor_wargs(self.rt1, 'std.RecTimer', 'dut', delay=0.1)
        src = self.request_handler.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = self.request_handler.new_actor_wargs(self.rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        self.request_handler.connect(self.rt1, snk, 'token', self.rt1.id, dut, 'token')
        self.request_handler.connect(self.rt1, dut, 'token', self.rt1.id, src, 'integer')

        self.migrate(self.rt1, self.rt2, dut)

    def testFileReader(self):
        """
        Simple test for FileReader migration.
        Create a FileReader actor and connect it to a source and a sink.
        Migrate it from runtime1 to runtime2 and verify that at least 1 token was received after migration
        """
        # create simple temp file with some data to be read
        fd, temp_path = mkstemp()
        os.write(fd, "Bla")
        os.close(fd)

        # create actors and connect them
        dut = self.request_handler.new_actor(self.rt1, 'io.FileReader', 'dut')
        src = self.request_handler.new_actor_wargs(self.rt1, 'std.Trigger', 'src', data=temp_path, tick=0.5)
        snk = self.request_handler.new_actor_wargs(self.rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        self.request_handler.connect(self.rt1, snk, 'token', self.rt1.id, dut, 'out')
        self.request_handler.connect(self.rt1, dut, 'filename', self.rt1.id, src, 'data')

        self.migrate(self.rt1, self.rt2, dut)

        # Wait at least 1 token after migration
        actual = helpers.wait_for_tokens(self.request_handler, self.rt1, snk, size=1)
        helpers.wait_for_tokens(self.request_handler, self.rt1, snk, len(actual)+1)

        # Cleanup
        os.remove(temp_path)

    def testFileWriter(self):
        """
        Simple test for FileWriter migration.
        Create a FileWriter actor and connect it to a source generating numbers (1, 2 ...).
        Use a Stringify actor to convert nubmer to string.
        Migrate it from runtime1 to runtime2 and wait something be written in file.
        """

        # create simple temp file with some data to be read
        fd, temp_path = mkstemp()
        os.close(fd)

        # create actors and connect them
        suffix_str = 'txt'
        dut = self.request_handler.new_actor_wargs(self.rt1, 'io.FileWriter', 'dut', basename=temp_path, suffix=suffix_str)
        src = self.request_handler.new_actor_wargs(self.rt1, 'std.CountTimer', 'src', sleep=0.5)
        strfy = self.request_handler.new_actor(self.rt1, 'std.Stringify', 'strfy')

        self.request_handler.connect(self.rt1, strfy, 'in', self.rt1.id, src, 'integer')
        self.request_handler.connect(self.rt1, dut, 'data', self.rt1.id, strfy, 'out')

        self.migrate(self.rt1, self.rt2, dut)

        def verify_filesize(filesize, retries=10):
            """
            Auxiliary method to verify that some token was written in file
            """
            from functools import partial
            # Use '1.' because after migration a new file is opened.
            # The '0.' was opened at first runtime
            func = partial(os.path.getsize, temp_path + '00001.' + suffix_str)
            criterion = lambda fsize: fsize >= filesize
            return helpers.retry(retries, func, criterion, "File size smaller than expected %d" % (filesize,))

        # wait one token after migration
        actual = verify_filesize(1)
        verify_filesize(actual + 1)

        # Cleanup, remove all files generated by the test
        import glob
        filelist = glob.glob(temp_path + "*")
        for f in filelist:
            os.remove(f)

if __name__ == '__main__':
    unittest.main()
