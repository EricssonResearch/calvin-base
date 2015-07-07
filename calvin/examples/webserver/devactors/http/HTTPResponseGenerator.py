# encoding: utf-8

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
from string import Template

class HTTPResponseGenerator(Actor):

    """
    Read status and optional body (if status = 200) and generate a HTML response
    Inputs:
      status : HTTP status 200/400/404/501
      body : HTML text
    Outputs:
      out : Properly formatted HTML response
    """

    STATUSMAP = {
        200: "OK",
        400: "Bad Request",
        404: "Not Found",
        501: "Not Implemented"
    }
    HEADER_TEMPLATE = Template("Content-Type: text/html\r\nContent-Length: $length")
    RESPONSE_TEMPLATE = Template("HTTP/1.0 $status $reason\r\n$header\r\n\r\n$body\r\n\r\n")
    ERROR_BODY = Template("<html><body>$reason ($status)</body></html>")

    @manage()
    def init(self):
        pass

    @condition(['status', 'body'], ['out'])
    @guard(lambda self, status, body : status == 200)
    def ok(self, status, body):
        header = self.HEADER_TEMPLATE.substitute(
            length=len(body)
        )
        response = self.RESPONSE_TEMPLATE.substitute(
            header=header,
            status=status,
            reason=self.STATUSMAP.get(status, "Unknown"),
            body=body
        )
        return ActionResult(production=(response, ))

    @condition(['status', 'body'], ['out'])
    @guard(lambda self, status, body : status != 200)
    def error(self, status, body):

        body = self.ERROR_BODY.substitute(
            status=status,
            reason=self.STATUSMAP.get(status, "Unknown")
        )
        header = self.HEADER_TEMPLATE.substitute(
            length=len(body)
        )
        response = self.RESPONSE_TEMPLATE.substitute(
            header=header,
            status=status,
            reason=self.STATUSMAP.get(status, "Unknown"),
            body=body
        )
        return ActionResult(production=(response, ))

    action_priority = (ok, error)

