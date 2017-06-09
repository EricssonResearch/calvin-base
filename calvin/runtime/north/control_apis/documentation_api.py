import json
from calvin.actorstore.store import DocumentationStore
from routes import handler, docs
from authentication import authentication_decorator

@handler(r"GET /\sHTTP/1")
@authentication_decorator
def handle_get_base_doc(self, handle, connection, match, data, hdr):
    """
    GET /
    Document the REST API
    """

    control_api_doc = docs()
    lines = control_api_doc.split("\n")

    want_json = 'accept' in hdr and hdr['accept'] == "application/json"

    if not want_json:
        data = """
        <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
        <html>
        <title>Calvin control API</title>
        <body>
        <xmp style="display:none;">"""

        block = []
        for line in lines:
            if not line and block:
                try:
                    data += '- __' + block.pop(1).strip().replace('_', '\_') + '__' + "\n"
                    data += "```\n" + "\n".join(s for s in block) + "\n```\n"
                except:
                    print "Error", line, block
                finally:
                    block =  []
            elif line:
                # same block
                block.append(line)
        data += """
        </xmp>
        <script src="//strapdownjs.com/v/0.2/strapdown.js"></script>
        </body>
        </html>
        """
        self.send_response(handle, connection, data, status=200, content_type="Content-Type: text/HTML")
    else:
        data = []
        block = []
        for line in lines:
            if not line and block:
                item = {'title': block.pop(1).strip().replace('_', '\_').strip()}
                item['doc_rows'] = [ a.strip() for a in block ]
                data.append(item)
                block =  []
            elif line:
                # same block
                block.append(line)

        self.send_response(handle, connection, json.dumps(data), status=200)

@handler(r"GET /actor_doc(\S*)\sHTTP/1")
@authentication_decorator
def handle_get_actor_doc(self, handle, connection, match, data, hdr):
    """
    GET /actor_doc {path}
    Get documentation in 'raw' format for actor or module at {path}
    Path is formatted as '/{module}/{submodule}/ ... /{actor}'.
    If {path} is empty return top-level documentation.
    See DocumentStore help_raw() for details on data format.
    Response status code: OK
    Response: dictionary with documentation
    """
    path = match.group(1)
    what = '.'.join(path.strip('/').split('/'))
    ds = DocumentationStore()
    what = None if not what else what
    data = ds.help_raw(what)
    self.send_response(handle, connection, data)
