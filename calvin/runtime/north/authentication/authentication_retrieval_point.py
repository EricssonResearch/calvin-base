# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

from abc import ABCMeta, abstractmethod
import os
import glob
import json
from calvin.utilities import calvinuuid
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities import calvinconfig
from passlib.hash import pbkdf2_sha256

_log = get_logger(__name__)
_conf = calvinconfig.get()
_sec_conf = _conf

# This is an abstract class for the PRP (Policy Retrieval Point)
class AuthenticationRetrievalPoint(object):
    __metaclass__ = ABCMeta  # Metaclass for defining Abstract Base Classes

    @abstractmethod
    def get_users_db(self):
        """Return a JSON representation of the policy identified by id"""
        return

    @abstractmethod
    def create_users_db(self, data):
        """Create policy based on the JSON representation in data"""
        return

    @abstractmethod
    def update_users_db(self, data):
        """Change the content of the policy identified by id to data (JSON representation of policy)"""
        return

    @abstractmethod
    def delete_users_db(self):
        """Delete the policy identified by id"""
        return


class FileAuthenticationRetrievalPoint(object):

    def __init__(self, path):
        # Replace ~ by the user's home directory.
        _log.debug("FileAuthenticationRetrievalPoint::__init__")
        self.path = os.path.expanduser(path) 
        self.users_db=self.get_users_db()
        self.groups_db=self.get_groups_db()
        if not os.path.exists(self.path):
            try:
                os.makedirs(self.path)
            except OSError as exc:  # Guard against race condition
                _log.error("Failed to create path, path={}".format(path))
                if exc.errno != errno.EEXIST:
                    raise

    def get_users_db(self):
        """Return the database of users"""
        _log.debug("get_users_db")
        try:
            self.check_stored_users_db_for_unhashed_passwords()
        except Exception as err:
            _log.error("Failed to check for unhashed passwords in users file, err={}".format(err))
            return None
        try:
            users_db_path = os.path.join(self.path,'users.json')
            with open(users_db_path,'rt') as data:
                users_db = json.load(data)
        except Exception as err:
            _log.error("No users.json file can be found at path={}, err={}".format(users_db_path, err))
            return None
        return users_db

    def create_users_db(self, data):
        """Create a database of users"""
        _log.debug("create_users_db")
        hashed_data = self.hash_passwords(data)
        with open(os.path.join(self.path, "users.json"), "w") as file:
            json.dump(hashed_data, file)

    def hash_passwords(self, data):
        """Change the content of the users database"""
        import time
        #TODO: remove printing passwords into log 
        _log.debug("hash_passwords\n\tdata={}".format(data))
        updates_made = False
        start = time.time()
        for username in data:
            user_data = data[username]
            try:
                is_pbkdf2 = pbkdf2_sha256.identify(user_data['password'])
            except Exception as err:
                _log.error("Failed to identify if password is PBKDF2 or not:"
                           "\n\tusername={}"
                           "\n\tuser_data={}"
                           "\n\terr={}".format(username, user_data, err))
                raise

            #If the password is in clear, let's hash it with a salt and store that instead
            if ('password' in user_data) and not (is_pbkdf2):
                try:
                    hash = pbkdf2_sha256.encrypt(user_data['password'], rounds=200000, salt_size=16)
                except Exception as err:
                    _log.error("Failed to calculate PBKDF2 of password, err={}".format(err))
                    raise
                user_data['password']=hash
                updates_made = True
        _log.debug("hashed_passwords"
                   "\n\tdata={}"
                   "\n\ttime it took to hash passwords={}".format(data, time.time()-start))
        return updates_made

    def update_users_db(self, data):
        """Change the content of the users database"""
        _log.debug("update_users_db"
                   "\n\tdata={}".format(data))
        try:
            self.hash_passwords(data)
        except Exception as err:
            _log.error("Failed to hash passwords, err={}".format(err))
            raise
        file_path = os.path.join(self.path, "users.json")
        if os.path.isfile(file_path):
            with open(file_path, "w") as file:
                json.dump(data, file)
        else:
            _log.error("update_users_db: file does not exist, file_path={}".format(file_path))
            raise IOError  # Raise exception if policy named filename doesn't exist
        self.users_db = data

    def check_stored_users_db_for_unhashed_passwords(self):
        """
        Load the database from storage, check if there
        are any passwords stored in clear, and if so, hash
        the passwords and store the hashes instead
        """
        _log.debug("check_stored_users_db_for_unhashed_passwords")
        file_path = os.path.join(self.path, "users.json")
        if os.path.isfile(file_path):
            try:
                with open(file_path, "r+") as file:
                    data = json.load(file)
                    if self.hash_passwords(data):
                        file.seek(0)
                        json.dump(data, file)
                        file.truncate()
            except Exception as exc:
                _log.exception("Failed to open users.json, exc={}".format(exc))

        else:
            _log.error("No users.json file, looking at {}".format(file_path))
            raise IOError  # Raise exception if policy named filename doesn't exist


    def delete_users_db(self):
        """Delete the policy named policy_id"""
        _log.debug("delete_users_db")
        os.remove(os.path.join(self.path, "users.json"))
        self.users_db=None

    def get_groups_db(self):
        """Return the database of groups"""
        path = os.path.join(self.path,"groups.json")
        _log.debug("get_groups_db, path={}".format(path))
        try:
            with open(path, 'rt') as data:
                groups_db = json.load(data)
        except Exception as err:
            _log.error("Failed to open groups.json:"
                       "\n\tpath={}"
                       "\n\terr={}".format(path, err))
            return None
        return groups_db

    def create_groups_db(self, data):
        """Create a database of groups"""
        _log.debug("create_grousp_db")
        with open(os.path.join(self.path, "groups.json"), "w") as file:
            json.dump(data, file)

    def update_groups_db(self, data):
        """Change the content of the groups database """
        _log.debug("update_groups_db")
        file_path = os.path.join(self.path, "groups.json")
        if os.path.isfile(file_path):
            with open(file_path, "w") as file:
                json.dump(data, file)
        else:
            raise IOError  # Raise exception if policy named filename doesn't exist
        self.groups_db = data

    def delete_groups_db(self):
        """Delete the policy named policy_id"""
        _log.debug("delete_groups_db")
        os.remove(os.path.join(self.path, "groups.json"))
        self.groups_db = None
