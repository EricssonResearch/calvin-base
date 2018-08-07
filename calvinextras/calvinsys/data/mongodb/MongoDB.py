
# -*- coding: utf-8 -*-

# Copyright (c) 2018 Ericsson AB
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

from calvin.runtime.south.plugins.async import threads, async
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.calvinsys import base_calvinsys_object
import pymongo

_log = get_logger(__name__)

class MongoDB(base_calvinsys_object.BaseCalvinsysObject):
    """
    Attempt to write data to MongoDB.

    """

    init_schema = {
        "type": "object",
        "properties": {
            "db_host": {
                "description": "Address to mongo db instance",
                "type": "string"
            },
            "db_port": {
                "description": "Port to connect to, defaults to 27017",
                "type": "integer"
            },
            "collection": {
                "description": "Name of collection to write to",
                "type": "string"
            },
            "logging_interval": {
                "description": "How frequently to log data on database updates",
                "type": "number"
            }
        },
        "required": ["db_host", "collection"]
    }

    can_write_schema = {
        "description": "Returns True if ready for write, otherwise False",
        "type": "boolean"
    }

    write_schema = {
        "description": "Write list of documents to database",
        "type": "array"
    }

    def init(self, db_host, collection, db_port=27017, logging_interval=None, *kwargs):
        _log.info("Setup mongodb client")
        self.db_host = db_host
        self.collection_name = collection
        self.db_port = db_port
        self.client = None
        self.collection = None
        self.logging_interval = logging_interval

        if logging_interval is not None:
            # not more frequently than twice a minute
            self.logging_interval = max(30.0, self.logging_interval)

        self.busy = False

        self.items = 0

        def report():
            _log.info("Current rate: {} items in {} seconds ({:5.2f}/sec)".format(self.items, self.logging_interval, self.items/self.logging_interval))
            self.items = 0
            if self.stats:
                self.stats.reset()

        if self.logging_interval:
            self.stats = async.DelayedCall(self.logging_interval, report)
        else:
            self.stats = None

    def can_write(self):
        def get_collection():
            try:
                client = pymongo.MongoClient(self.db_host, self.db_port)
                coll = client.FaceGrind[self.collection_name]
                _log.info("Database connection opened successfully")
                return client, coll
            except Exception as e:
                _log.error("Failed to open database connection: {}".format(e))
                return None, None

        def done((client, collection)):
            if client and collection:
                self.client = client
                self.collection = collection
                self.busy = False
                self.scheduler_wakeup()

        def error(err):
            _log.error("There was an issue connecting to the database: {}".format(err))

        if not self.busy and self.client is None and self.collection is None:
            self.busy = True
            deferred = threads.defer_to_thread(get_collection)
            deferred.addCallback(done)
            deferred.addErrback(error)

        return not self.busy and self.collection is not None

    def write(self, documents):
        def insert(documents):
            try:
                result = self.collection.insert_many(documents)
                # assert result.inserted_count == 1
                return len(result.inserted_ids)
            except Exception as e:
                _log.error("Failed to insert document: {}".format(e))
                return False

        def done(ok):
            self.busy = False
            if ok:
                if self.items == 0:
                    _log.info("S: Stored {} documents in last operation".format(ok))
                self.items += ok
            else :
                _log.error("Failed to insert document - reconnecting")
                try:
                    self.client.close()
                finally:
                    self.client = None
                    self.collection = None
            self.scheduler_wakeup()

        print("Inserting documents {}".format(json.dumps(documents, indent=2)))
        self.busy = True
        deferred = threads.defer_to_thread(insert, documents)
        deferred.addCallback(done)

    def close(self):
        self.stats = None
        self.busy = True
        if self.client:
            self.client.close()
        self.collection = -1
        self.client = -1
