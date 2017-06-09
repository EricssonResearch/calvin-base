import json
from calvin.requests import calvinresponse
import calvin.runtime.south.plugins.ui.uicalvinsys as ui
from routes import handler, uuid_re

@handler(r"GET /uicalvinsys/" + uuid_re + "\sHTTP/1")
def handle_uicalvinsys(self, handle, connection, match, data, hdr):
    """
    GET /uicalvinsys/<uuid>
    Get UI definitions
    Response status code: UI definitions
    """
    self.send_response(handle, connection, json.dumps(ui.ui_definitions()), status=calvinresponse.OK)


@handler(r"POST /uicalvinsys\sHTTP/1")
def handle_uicalvinsys(self, handle, connection, match, data, hdr):
    """
    POST /uicalvinsys
    Update UICalvinSys state
    Body:
    {
        "actor_id" : <actor_id>
        "state": value
    }
    Response status code: OK or BAD_REQUEST
    """
    status = ui.update(data)
    self.send_response(handle, connection, None, status=calvinresponse.OK)

