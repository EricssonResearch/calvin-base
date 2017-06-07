import json
import time
from calvin.requests import calvinresponse
from calvin.utilities.calvinlogger import get_logger
from routes import handler, register, uuid_re
from authentication import authentication_decorator

_log = get_logger(__name__)

@authentication_decorator
@handler(r"POST /meter\sHTTP/1")
def handle_post_meter(self, handle, connection, match, data, hdr):
    """
    POST /meter
    Register for metering information
    Body:
    {
        "user_id": <user-id> optional user id
    }
    Response status code: OK or BAD_REQUEST
    Response:
    {
        "user_id": <user-id>,
        "timeout": <seconds data is kept>,
        "epoch_year": <the year the epoch starts at Jan 1 00:00, e.g. 1970>
    }
    """
    try:
        user_id = self.metering.register(data['user_id'] if data and 'user_id' in data else None)
        timeout = self.metering.timeout
        status = calvinresponse.OK
    except:
        _log.exception("handle_post_meter")
        status = calvinresponse.BAD_REQUEST
    self.send_response(handle, connection, json.dumps({ 'user_id': user_id,
                                                        'timeout': timeout,
                                                        'epoch_year': time.gmtime(0).tm_year})
                        if status == calvinresponse.OK else None, status=status)

@authentication_decorator
@handler(r"DELETE /meter/(METERING_" + uuid_re + "|" + uuid_re + ")\sHTTP/1")
def handle_delete_meter(self, handle, connection, match, data, hdr):
    """
    DELETE /meter/{user-id}
    Unregister for metering information
    Response status code: OK or NOT_FOUND
    """
    try:
        self.metering.unregister(match.group(1))
        status = calvinresponse.OK
    except:
        _log.exception("handle_delete_meter")
        status = calvinresponse.NOT_FOUND
    self.send_response(handle, connection, None, status=status)

@authentication_decorator
@handler(r"GET /meter/(METERING_" + uuid_re + "|" + uuid_re + ")/timed\sHTTP/1")
def handle_get_timed_meter(self, handle, connection, match, data, hdr):
    """
    GET /meter/{user-id}/timed
    Get timed metering information
    Response status code: OK or NOT_FOUND
    Response:
    {
        <actor-id>:
            [
                [<seconds since epoch>, <name of action>],
                ...
            ],
            ...
    }
    """
    try:
        data = self.metering.get_timed_meter(match.group(1))
        status = calvinresponse.OK
    except:
        _log.exception("handle_get_timed_meter")
        status = calvinresponse.NOT_FOUND
    self.send_response(handle, connection,
        json.dumps(data) if status == calvinresponse.OK else None, status=status)

@authentication_decorator
@handler(r"GET /meter/(METERING_" + uuid_re + "|" + uuid_re + ")/aggregated\sHTTP/1")
def handle_get_aggregated_meter(self, handle, connection, match, data, hdr):
    """
    GET /meter/{user-id}/aggregated
    Get aggregated metering information
    Response status code: OK or NOT_FOUND
    Response:
    {
        'activity':
        {
            <actor-id>:
            {
                <action-name>: <total fire count>,
                ...
            },
            ...
        },
        'time':
        {
            <actor-id>: [<start time of counter>, <last modification time>],
            ...
        }
    }
    """
    try:
        data = self.metering.get_aggregated_meter(match.group(1))
        status = calvinresponse.OK
    except:
        _log.exception("handle_get_aggregated_meter")
        status = calvinresponse.NOT_FOUND
    self.send_response(handle, connection,
        json.dumps(data) if status == calvinresponse.OK else None, status=status)

@authentication_decorator
@handler(r"GET /meter/(METERING_" + uuid_re + "|" + uuid_re + ")/metainfo\sHTTP/1")
def handle_get_metainfo_meter(self, handle, connection, match, data, hdr):
    """
    GET /meter/{user-id}/metainfo
    Get metering meta information on actors
    Response status code: OK or NOT_FOUND
    Response:
    {
        <actor-id>:
        {
            <action-name>:
            {
                'inports': {
                    <port-name> : <number of tokens per firing>,
                    ...
                           },
                'outports': {
                    <port-name> : <number of tokens per firing>,
                    ...
                           }
            },
            ...
        }
    }
    """
    try:
        data = self.metering.get_actors_info(match.group(1))
        status = calvinresponse.OK
    except:
        _log.exception("handle_get_metainfo_meter")
        status = calvinresponse.NOT_FOUND
    self.send_response(handle, connection,
        json.dumps(data) if status == calvinresponse.OK else None, status=status)
