# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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

import copy
import json
from twisted.enterprise import adbapi
from twisted.internet import defer
from calvin.runtime.south.async import async
from calvin.runtime.north.plugins.storage.storage_base import StorageBase
from calvin.utilities.calvin_callback import CalvinCB
from calvin.utilities import calvinlogger
from calvin.utilities import calvinconfig
from calvin.requests import calvinresponse

_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()

############################
# TODO Remake the storage API:
# * better names needed
######################

# The config kwarg depends on which database python module that is used
# Here is data for dbmodule="MySQLdb"
# host, port, db, user and passwd can be set, but if local only user and passwd is needed
# If other modules use another arg name for db need to fix that here
# Below defaults assume a password-less root user on local mysql
config_kwargs = _conf.get('global', 'storage_sql')
config_kwargs.setdefault('dbmodule', "MySQLdb")
config_kwargs.setdefault('user', "root")
config_kwargs.setdefault('db', _conf.get_in_order("dht_network_filter", "ALL").replace("-", "_"))

# Have single values and set-values in seperate tables to allow uniqueness on the right terms,
# i.e. key and key+value, respectively. Also support longer valuestr in single value.
# Set-values have one value on each row in the table.
QUERY_SETUP = """
CREATE DATABASE {db};
CREATE TABLE {db}.ckeys (
    id BIGINT AUTO_INCREMENT,
    keystr VARCHAR(1024),
    PRIMARY KEY(id),
    INDEX(keystr),
    UNIQUE(keystr)
);
CREATE TABLE {db}.cvalues (
    id BIGINT NOT NULL,
    valuestr VARCHAR(2048),
    PRIMARY KEY (id),
    FOREIGN KEY (id) REFERENCES {db}.ckeys (id) ON DELETE CASCADE
);
CREATE TABLE {db}.csetvalues (
    id BIGINT NOT NULL,
    valuestr VARCHAR(512),
    UNIQUE KEY keyvalue (id, valuestr),
    FOREIGN KEY (id) REFERENCES {db}.ckeys (id) ON DELETE CASCADE
);""".format(db=config_kwargs['db'])

# Needed to make set two roundtrips since mysql did not like (Err 2014) multi-statement that modified a depedent table
# Could potentially be made if multi-statement is supported in the dbmodule (now using MySQLdb module)
QUERY_SET = [q.format(db=config_kwargs['db']) for q in ["""
INSERT IGNORE INTO {db}.ckeys (keystr) VALUES('{{keystr}}');
""", """
INSERT INTO {db}.cvalues (id, valuestr)
    (SELECT id, '{{valuestr}}' FROM {db}.ckeys WHERE keystr='{{keystr}}')
    ON DUPLICATE KEY UPDATE valuestr='{{valuestr}}';
"""]]

QUERY_GET = """
SELECT valuestr FROM {db}.cvalues WHERE id IN (SELECT id FROM {db}.ckeys WHERE keystr='{{keystr}}');
""".format(db=config_kwargs['db'])

# Due to value tabels have foreign key for id the values will also be deleted
QUERY_DELETE = """
DELETE FROM {db}.ckeys WHERE keystr='{{keystr}}';
""".format(db=config_kwargs['db'])

# Due to value tabels have foreign key for id the values will also be deleted
QUERY_DELETE_MANY = """
DELETE FROM {db}.ckeys WHERE {{keystr}};
""".format(db=config_kwargs['db'])

QUERY_APPEND = [q.format(db=config_kwargs['db']) for q in ["""
INSERT IGNORE INTO {db}.ckeys (keystr) VALUES('{{keystr}}');
""", """
INSERT IGNORE INTO {db}.csetvalues (id, valuestr)
    (SELECT id, '{{valuestr}}' FROM {db}.ckeys WHERE keystr='{{keystr}}');
"""]]

QUERY_REMOVE = """
DELETE FROM {db}.csetvalues WHERE
    id IN (SELECT id FROM {db}.ckeys WHERE keystr='{{keystr}}') AND valuestr='{{valuestr}}';
""".format(db=config_kwargs['db'])

QUERY_GETCONCAT = """
SELECT valuestr FROM {db}.csetvalues WHERE
    id IN (SELECT id FROM {db}.ckeys WHERE keystr='{{keystr}}');
""".format(db=config_kwargs['db'])

QUERY_GET_INDEX = """
SELECT valuestr FROM {db}.csetvalues WHERE
    id IN (SELECT id FROM {db}.ckeys WHERE keystr LIKE '{{keystr}}%');
""".format(db=config_kwargs['db'])

class SqlClient(StorageBase):
    """
        Sql client plugin class for SQL based storage.
    """
    def __init__(self):
        super(SqlClient, self).__init__()
        self.dbpool = None

    def start(self, iface='', bootstrap=[], cb=None, name=None, nodeid=None):
        kwargs = copy.copy(config_kwargs)
        _log.debug("SQL start %s" % str(kwargs))
        kwargs.pop('db', None)
        dbmodule = kwargs.pop('dbmodule', "MySQLdb")
        # FIXME does this take too long?
        self.dbpool = adbapi.ConnectionPool(dbmodule, **kwargs)
        if not self.dbpool:
            _log.debug("Failed SQL connection pool")
            if cb is not None:
                async.DelayedCall(0, cb, False)
            return
        d = self.dbpool.runQuery(QUERY_SETUP)
        d.addCallbacks(CalvinCB(self._setup_cb, cb=cb), CalvinCB(self._setup_fail_cb, cb=cb))
        _log.debug("Sent SQL table setup query")

    def _setup_cb(self, result, *args, **kwargs):
        cb = kwargs.pop('cb', None)
        _log.debug("SQL setup OK %s" % str(result))
        if cb is not None:
            async.DelayedCall(0, cb, True)

    def _setup_fail_cb(self, failure, **kwargs):
        ok = False
        cb = kwargs.pop('cb', None)
        try:
            err = int(str(failure.value)[1:5])
        except:
            err = 9999
        if err == 1007:
            # Database exist, which is OK
            ok = True
        _log.debug("SQL setup %s %i %s" % ("OK" if ok else "FAIL", err, str(failure)))
        if cb is not None:
            async.DelayedCall(0, cb, ok)

    def set(self, key, value, cb=None):
        """
            Set a key, value pair in the storage
        """
        _log.debug("SQL set %s to %s" % (key, value))
        value = json.dumps(value)
        key_sql = key.replace("'", r"\'")
        def _set_value(*args, **kwargs):
            d2 = self.dbpool.runQuery(QUERY_SET[1].format(keystr=key_sql, valuestr=value))
            d2.addCallbacks(CalvinCB(self._set_cb, cb=cb, key=key, value=value),
                            CalvinCB(self._set_fail_cb, cb=cb, key=key, value=value))
        d1 = self.dbpool.runQuery(QUERY_SET[0].format(keystr=key_sql, valuestr=value))
        d1.addCallbacks(_set_value, CalvinCB(self._set_fail_cb, cb=cb, key=key, value=value))
        _log.debug("SQL set %s to %s requested" % (key, value))

    def _set_cb(self, result, **kwargs):
        _log.debug("SQL set OK")
        cb = kwargs.pop('cb', None)
        key = kwargs.pop('key', None)
        _log.debug("SQL set OK %s" % str(result))
        if cb is not None:
            async.DelayedCall(0, CalvinCB(cb, key, calvinresponse.CalvinResponse(status=calvinresponse.OK)))

    def _set_fail_cb(self, failure, **kwargs):
        _log.debug("SQL set FAIL")
        ok = False
        cb = kwargs.pop('cb', None)
        key = kwargs.pop('key', None)
        # TODO handle errors
        try:
            err = int(str(failure.value)[1:5])
        except:
            err = 9999
        _log.debug("SQL set %s %i %s" % ("OK" if ok else "FAIL", err, str(failure)))
        if cb is not None:
            async.DelayedCall(0, CalvinCB(cb, key, calvinresponse.CalvinResponse(status=ok)))

    def get(self, key, cb=None):
        """
            Gets a value from the storage
        """
        _log.debug("SQL get %s" % (key,))
        key_sql = key.replace("'", r"\'")
        d = self.dbpool.runQuery(QUERY_GET.format(keystr=key_sql))
        d.addCallbacks(CalvinCB(self._get_cb, cb=cb, key=key), CalvinCB(self._get_fail_cb, cb=cb, key=key))
        _log.debug("SQL get %s requested" % (key,))

    def _get_cb(self, result, **kwargs):
        _log.debug("SQL get OK")
        cb = kwargs.pop('cb', None)
        key = kwargs.pop('key', None)
        try:
            r = json.loads(result[0][0])
        except:
            # Empty hence deleted or don't exist
            r = calvinresponse.CalvinResponse(status=calvinresponse.NOT_FOUND)
        _log.debug("SQL get OK %s" % r)
        if cb is not None:
            async.DelayedCall(0, CalvinCB(cb, key, r))

    def _get_fail_cb(self, failure, **kwargs):
        _log.debug("SQL get FAIL")
        ok = False
        cb = kwargs.pop('cb', None)
        key = kwargs.pop('key', None)
        # TODO handle errors
        try:
            err = int(str(failure.value)[1:5])
        except:
            err = 9999
        _log.debug("SQL get %s %i %s" % ("OK" if ok else "FAIL", err, str(failure)))
        if cb is not None:
            async.DelayedCall(0, CalvinCB(cb, key, calvinresponse.CalvinResponse(status=calvinresponse.NOT_FOUND)))

    def delete(self, key, cb=None):
        _log.debug("SQL delete %s" % (key,))
        key_sql = key.replace("'", r"\'")
        d1 = self.dbpool.runQuery(QUERY_DELETE.format(keystr=key_sql))
        d1.addCallbacks(CalvinCB(self._delete_cb, cb=cb, key=key),
                        CalvinCB(self._delete_fail_cb, cb=cb, key=key))

    def _delete_cb(self, result, **kwargs):
        _log.debug("SQL delete OK")
        cb = kwargs.pop('cb', None)
        key = kwargs.pop('key', None)
        _log.debug("SQL delete OK %s" % str(result))
        if cb is not None:
            async.DelayedCall(0, CalvinCB(cb, key, calvinresponse.CalvinResponse(status=True)))

    def _delete_fail_cb(self, failure, **kwargs):
        _log.debug("SQL delete FAIL")
        ok = False
        cb = kwargs.pop('cb', None)
        key = kwargs.pop('key', None)
        # TODO handle errors
        try:
            err = int(str(failure.value)[1:5])
        except:
            err = 9999
        _log.debug("SQL delete %s %i %s" % ("OK" if ok else "FAIL", err, str(failure)))
        if cb is not None:
            async.DelayedCall(0, CalvinCB(cb, key, calvinresponse.CalvinResponse(status=ok)))

    def get_concat(self, key, cb=None):
        """
            Gets a value from the storage
        """
        _log.debug("SQL get_concat %s" % (key,))
        key_sql = key.replace("'", r"\'")
        d = self.dbpool.runQuery(QUERY_GETCONCAT.format(keystr=key_sql))
        d.addCallbacks(CalvinCB(self._getconcat_cb, cb=cb, key=key), CalvinCB(self._getconcat_fail_cb, cb=cb, key=key))
        _log.debug("SQL get_concat %s requested" % (key,))

    def _getconcat_cb(self, result, **kwargs):
        _log.debug("SQL get_concat OK %s" % str(result))
        cb = kwargs.pop('cb', None)
        key = kwargs.pop('key', None)
        try:
            extracted_result = [json.loads(r[0]) for r in result]
        except:
            extracted_result = []
        _log.debug("SQL get_concat OK %s %s" % (result, extracted_result))
        if cb is not None:
            if key is None:
                async.DelayedCall(0, CalvinCB(cb, extracted_result))
            else:
                async.DelayedCall(0, CalvinCB(cb, key, extracted_result))

    def _getconcat_fail_cb(self, failure, **kwargs):
        _log.debug("SQL get_concat FAIL")
        ok = False
        cb = kwargs.pop('cb', None)
        key = kwargs.pop('key', None)
        # TODO handle errors
        try:
            err = int(str(failure.value)[1:5])
        except:
            err = 9999
        _log.debug("SQL get_concat %s %i %s" % ("OK" if ok else "FAIL", err, str(failure)))
        if cb is not None:
            # FIXME: Should this be empty list?
            if key is None:
                async.DelayedCall(0, CalvinCB(cb, calvinresponse.CalvinResponse(status=calvinresponse.NOT_FOUND)))
            else:
                async.DelayedCall(0, CalvinCB(cb, key, calvinresponse.CalvinResponse(status=calvinresponse.NOT_FOUND)))

    def append(self, key, value, cb=None, include_key=True):
        _log.debug("SQL append %s to %s" % (value, key))
        values = [json.dumps(v) for v in value]
        key_sql = key.replace("'", r"\'")
        key_none = key if include_key else None
        def _append_value(*args, **kwargs):
            dlist = []
            for v in values:
                dlist.append(self.dbpool.runQuery(QUERY_APPEND[1].format(keystr=key_sql, valuestr=v)))
            d2 = defer.DeferredList(dlist) if len(dlist) > 1 else dlist[0]
            d2.addCallbacks(CalvinCB(self._append_cb, cb=cb, key=key_none), CalvinCB(self._append_fail_cb, cb=cb, key=key_none))
        d1 = self.dbpool.runQuery(QUERY_APPEND[0].format(keystr=key_sql))
        d1.addCallbacks(_append_value, CalvinCB(self._append_fail_cb, cb=cb, key=key_none))
        _log.debug("SQL append %s to %s requested" % (value, key))

    def _append_cb(self, result, **kwargs):
        _log.debug("SQL append OK")
        cb = kwargs.pop('cb', None)
        key = kwargs.pop('key', None)
        _log.debug("SQL append OK %s" % str(result))
        if cb is not None:
            if key is None:
                async.DelayedCall(0, CalvinCB(cb, calvinresponse.CalvinResponse(status=True)))
            else:
                async.DelayedCall(0, CalvinCB(cb, key, calvinresponse.CalvinResponse(status=True)))

    def _append_fail_cb(self, failure, **kwargs):
        _log.debug("SQL append FAIL")
        ok = False
        cb = kwargs.pop('cb', None)
        key = kwargs.pop('key', None)
        # TODO handle errors
        try:
            err = int(str(failure.value)[1:5])
        except:
            err = 9999
        _log.debug("SQL append %s %i %s" % ("OK" if ok else "FAIL", err, str(failure)))
        if cb is not None:
            if key is None:
                async.DelayedCall(0, CalvinCB(cb, calvinresponse.CalvinResponse(status=ok)))
            else:
                async.DelayedCall(0, CalvinCB(cb, key, calvinresponse.CalvinResponse(status=ok)))

    def remove(self, key, value, cb=None, include_key=True):
        _log.debug("SQL remove %s to %s" % (value, key))
        key_sql = key.replace("'", r"\'")
        key_none = key if include_key else None
        values = [json.dumps(v) for v in value]
        dlist = []
        for v in values:
            dlist.append(self.dbpool.runQuery(QUERY_REMOVE.format(keystr=key_sql, valuestr=v)))
        d = defer.DeferredList(dlist) if len(dlist) > 1 else dlist[0]
        d.addCallbacks(CalvinCB(self._remove_cb, cb=cb, key=key_none), CalvinCB(self._remove_fail_cb, cb=cb, key=key_none))
        _log.debug("SQL remove %s to %s requested" % (value, key))

    def _remove_cb(self, result, **kwargs):
        _log.debug("SQL remove OK")
        cb = kwargs.pop('cb', None)
        key = kwargs.pop('key', None)
        _log.debug("SQL remove OK %s" % str(result))
        if cb is not None:
            if key is None:
                async.DelayedCall(0, CalvinCB(cb, calvinresponse.CalvinResponse(status=True)))
            else:
                async.DelayedCall(0, CalvinCB(cb, key, calvinresponse.CalvinResponse(status=True)))

    def _remove_fail_cb(self, failure, **kwargs):
        _log.debug("SQL remove FAIL")
        ok = False
        cb = kwargs.pop('cb', None)
        key = kwargs.pop('key', None)
        # TODO handle errors
        try:
            err = int(str(failure.value)[1:5])
        except:
            err = 9999
        _log.debug("SQL remove %s %i %s" % ("OK" if ok else "FAIL", err, str(failure)))
        if cb is not None:
            if key is None:
                async.DelayedCall(0, CalvinCB(cb, calvinresponse.CalvinResponse(status=ok)))
            else:
                async.DelayedCall(0, CalvinCB(cb, key, calvinresponse.CalvinResponse(status=ok)))

    def add_index(self, prefix, indexes, value, cb=None):
        _log.debug("SQL add_index %s %s" % (indexes, value))
        # Make sure that internal index level / is different from level seperator
        key = prefix + '/'+'/'.join([i.replace('/',r'+/') for i in indexes]) + '/'
        self.append(key, value, cb=cb, include_key=False)

    def remove_index(self, prefix, indexes, value, cb=None):
        _log.debug("SQL remove_index %s %s" % (indexes, value))
        # Make sure that internal index level / is different from level seperator
        key = prefix + '/'+'/'.join([i.replace('/',r'+/') for i in indexes]) + '/'
        self.remove(key, value, cb=cb, include_key=False)

    def get_index(self, prefix, index, cb=None):
        _log.debug("SQL get_index %s" % (index,))
        # Make sure that internal index level / is different from level seperator and we only match full level
        key = prefix + '/'+'/'.join([i.replace('/',r'+/') for i in index]) + '/'
        d = self.dbpool.runQuery(QUERY_GET_INDEX.format(keystr=key.replace("'", r"\'")))
        d.addCallbacks(CalvinCB(self._getconcat_cb, cb=cb), CalvinCB(self._getconcat_fail_cb, cb=cb))
        _log.debug("SQL get_index %s requested" % (key,))

    def bootstrap(self, addrs, cb=None):
        _log.debug("SQL bootstrap")

    def stop(self, cb=None):
        _log.debug("SQL stop")
