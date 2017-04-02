from calvin.runtime.north.plugins.nest import Nest
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.plugins.async.twistedimpl import  threads

_log = get_logger(__name__)

class LogInException(Exception):

    """
    Just a simple custom exception for the class below
    """
    def __init__(self, message):
        self.message = message

class NotFoundException(Exception):



    """
    Just a simple custom exception for the class below
    """
    def __init__(self, message):
        self.message = message


class NestIntegration(object):

    def __init__(self, node, actor):
        self.nest = None
        self._node = node
        self._actore = actor
        self.isLogged = None
        try:
            credentials = self._node.attributes.get_private("/web/nest.com")
        except Exception as e:
            _log.error("Credentials not accessible. Error message %s" % e.message)
            credentials = None

        if credentials:
            self._in_progress = threads.defer_to_thread(self.login,credentials['username'], credentials['password'])
            self._in_progress.addCallback(self._post_login)
            self._in_progress.addErrback(self._err_login)

        else:
            _log.warning("Expected credentials /private/web/nest.com not found")
            self.nest = None

    def _post_login(self,*args, **kwargs):
        self._in_progress = None
        (res,) = args
        self.isLogged = res

        if self.isLogged:
            _log.info("Successfully logged in into Nest.com")
            #get update values each 2 seconds (it requires to renew the login, change this value carefully
            self.nest._cache_ttl = 20
        else:
            _log.info("Authentication failed. Check username and password")

    def _err_login(self, *args, **kwargs):
         _log.error("%r %r" % (args, kwargs))
         self._in_progress = None
         self.isLogged = False

    def login(self, username, password):
        """
        Authentication to the Nest service
        Args:
            username:
            password:

        Returns: False if authentication fails, True otherwise

        """
        login_success = False
        try:
            self.nest = Nest(username, password)
            self.check_login()
            login_success = True

        except Exception, ex:
            _log.error(ex.message)
        return login_success

    def check_login(self):

        """
        Checks if the user credentials are correct. Using this library is necessary to execute a query
        to get any authentication results
        Returns:

        """
        if self.nest is None:
            raise LogInException("Log in before attempting any operation!")
        try:
            self.nest.structures
        except Exception:
            raise LogInException("Wrong credentials! Check username and password")

    def list_structures(self):

        """
        Lists all structures owned by the current user
        Returns: a list of structures

        """
        self.check_login()
        return self.nest.structures

    def list_devices(self):

        """
        Lists all devices owned by the current user
        Returns: a list of structures

        """
        self.check_login()
        complete_list = [self.nest.devices, self.nest.protectdevices, self.nest.cameradevices]
        return reduce(lambda first,second: first + second, complete_list)

    def list_devices_by_structure(self, structure_name):

        """
        Lists the devices in the given structure
        Args:
            structure_name:

        Returns: the list of devices related to that structure

        """
        self.check_login()
        structure = self.get_structure_by_name(structure_name)

        if structure is None:
            raise NotFoundException("Structure with %s name does not exist" % structure_name)
        complete_list = [structure.devices, structure.protectdevices, structure.cameradevices]
        return reduce(lambda first,second: first + second, complete_list)

    def get_structure_by_name(self, structure_name):

        """
        Args:
            structure_name: the name of the selected structure

        Returns: a list with all the structures which matches that name

        """
        self.check_login()
        res = filter(lambda item: item.name == structure_name, self.nest.structures)
        return next(iter(res), None)

    def get_device_by_name(self,deviceID):

        """
        Lookup with a device given its name
        Args:
            deviceID: the device name

        Returns: the managed object linked to the name or None if it doesn't exist

        """
        self.check_login()
        res = filter(lambda device: device.name == deviceID, self.nest.devices)
        return next(iter(res), None)

    def get_property(self,deviceID, proprety_name):

        """
        read property device given property and device names
        Args:
            deviceID:
            proprety_name:

        Returns: the value of that property or raise an exception otherwise

        """
        self.check_login()
        device = self.get_device_by_name(deviceID)

        if device is None:
            raise NotFoundException("Device with %s name does not exist!" % deviceID)
        return device.__getattribute__(proprety_name)

    def set_property(self, deviceID, property_name, value):
        """
        Set the property of a device given its identifier

        Args:
            deviceID: device identifier
            property_name: the property name to set
            value: the value for the property to be set

        Returns:
            True if the operation succeeds
            NotFoundException if the device name is not found
            AttributeError if the property doesn't exists
        """
        self.check_login()
        device = self.get_device_by_name(deviceID)

        if device is None:
            raise NotFoundException("Device with %s name does not exist!" % deviceID)
        device.__setattr__(property_name, value)
        return True


def register(node, actor):
    return NestIntegration(node,actor)






