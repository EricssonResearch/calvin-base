# -*- coding: utf-8 -*-

import pytest
import unittest
from calvin.tests import helpers
from calvin.requests.request_handler import RequestHandler

class CalvinTestBase(unittest.TestCase):

    def setUp(self):
        self.request_handler = RequestHandler()
        self.test_type, [self.rt1, self.rt2, self.rt3] = helpers.setup_test_type(self.request_handler)

    def tearDown(self):
        helpers.teardown_test_type(self.request_handler, [self.rt1, self.rt2, self.rt3], self.test_type)

    def wait_for_migration(self, runtime, actors, retries=20):
        retry = 0
        if not isinstance(actors, list):
            actors = [ actors ]
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
            _log.info("Migration failed, after %d retires" % (retry,))
            raise Exception("Migration failed")

    def migrate(self, source, dest, actor):
        self.request_handler.migrate(source, actor, dest.id)
        self.wait_for_migration(dest, [actor])

class TestActorMigration(CalvinTestBase):
    def testRecTimer(self):
        """
        Simple test for RecTimer migration.
        Create a RecTimer actor and connects it to a source and a sink.
        Migrate it from runtime1 to runtime2
        """
        rec = self.request_handler.new_actor(self.rt1, 'std.RecTimer', 'rec')
        src = self.request_handler.new_actor(self.rt1, 'std.CountTimer', 'src')
        snk = self.request_handler.new_actor_wargs(self.rt1, 'test.Sink', 'snk', store_tokens=1, quiet=1)

        self.request_handler.connect(self.rt1, snk, 'token', self.rt1.id, rec, 'token')
        self.request_handler.connect(self.rt1, rec, 'token', self.rt1.id, src, 'integer')

        self.migrate(self.rt1, self.rt2, rec)

