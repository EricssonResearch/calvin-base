import asyncio
import socket
import json

import pytest

##############################################################################
#                                                                            #
# WARNING! Don't use as template! Proof-of-concept ONLY!                     #
#                                                                            #
# A better approach would be to use an HTTP server instead of a socket, and  #
# reconfigure io.stdout to do HTTP POST of tokens in system_config below     #
#                                                                            #
##############################################################################


PORT=7789

system_config = f"""
- class: ACTORSTORE
  name: actorstore
  port: 4999
  type: REST
- class: RUNTIME
  name: runtime
  actorstore: $actorstore
  registry: 
    type: local
    uri: null
  config:
    calvinsys:
      io.stdout:
          attributes:
            address: "127.0.0.1"
            port: {PORT}
            connection_type: TCP
          module: network.SocketClient
"""

testlist = [
    (
        'test_feeding_tokens_into_test',
        r"""
            src : std.Counter()
            snk : io.Print()
            src.integer > snk.token
        """,
        ['snk'],
        "1234567891011121314151617181920",
    ),
    (
        'test_feeding_tokens_into_test_slowly',
        r"""
            src : std.Counter()
            delay : std.ClassicDelay(delay=0.1) 
            snk : io.Print()
            src.integer > delay.token
            delay.token > snk.token
        """,
        ['snk'],
        "1234567891011121314151617181920",
    )
]


#
# pytest-asyncio defaults to function scope for event_loop, need to redefine
# see https://github.com/pytest-dev/pytest-asyncio/issues/68
#
@pytest.yield_fixture(scope='module')
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

#
# This is a variant of the deploy_application fixture, just for testing
#
@pytest.fixture(scope='module', params=testlist)
def deploy_application(request, sink_server, system_setup, deploy_app, destroy_app):
    """Deploy applications from set of scrips and test output"""
    rt_uri = system_setup['runtime']['uri']
    actorstore_uri = system_setup['actorstore']['uri']
    name, script, _, expects = request.param

    # Socket server must start BEFORE app is deployed
    sink_server = sink_server(port=PORT)
    # Deploy app    
    app_info = deploy_app(rt_uri, script, name, actorstore_uri)

    yield (sink_server, expects)

    # Clean-up section
    sink_server.close()
    destroy_app(rt_uri, app_info)


@pytest.fixture(scope='module')
def sink_server():
    """
    Create a socket server listening on a specific port.
    N.B. The accept-part of the connection is handled by the 'recv_from_sink' fixture
    
    Usage: server_socket = sink_server(<port>)
    """
    def _socket_server(port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(0.0)
        s.bind(("localhost", port))
        s.listen(1)
        return s

    return _socket_server


@pytest.fixture(scope='module')
def recv_from_sink():
    """
    Wait for reconfigured sink, see 'system_config' above, to connect and receive its tokens.
    Return received data when enough bytes (min_length) read, or exception if timeout occurs before all bytes read.
    
    Usage: recv_from_sink(sink_server, min_length, timeout)
           where sink_server is the socket server created by 'sink_server' and passed from the
           'deploy_application' fixture.
    """
    
    # The actual recv loop
    async def _recv_sink(loop, sink_server, min_length):
        sink, _ = await loop.sock_accept(sink_server)
        _data = b"" 
        while len(_data) < min_length:
            data = await loop.sock_recv(sink, 256)
            if data:
                _data += data
        return _data

    # Wrap the recv in a timeout
    async def _recv_sink_timeout(sink_server, min_length, timeout):
        loop = asyncio.get_running_loop()
        try:
            data = await asyncio.wait_for(
                _recv_sink(loop, sink_server, min_length),
                timeout=timeout
            )
            return data
        except Exception as exc:
            return exc
     
    return _recv_sink_timeout
    

# Helper     
@pytest.fixture
def to_bytes():
    def _to_bytes(data):
        if not isinstance(data, str):
            data = json.dumps(data)
        return data.encode('utf-8')
    
    return _to_bytes     
          

@pytest.mark.asyncio
async def test_feedback(to_bytes, recv_from_sink, deploy_application):
    sink_server, expected = deploy_application
    bytes_expected = to_bytes(expected)
    data = await recv_from_sink(
        sink_server, 
        min_length=len(bytes_expected), 
        timeout=5.0
    )
    assert isinstance(data, bytes)
    assert data[:len(bytes_expected)] == bytes_expected
