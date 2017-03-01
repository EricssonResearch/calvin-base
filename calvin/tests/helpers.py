from calvin.utilities.nodecontrol import dispatch_node
from calvin.utilities.attribute_resolver import format_index_string
from calvin.utilities import calvinconfig
from calvin.utilities import calvinlogger
from calvin.requests.request_handler import RT
import os
import time
import multiprocessing
import copy
import numbers

_log = calvinlogger.get_logger(__name__)
_conf = calvinconfig.get()

def retry(retries, function, criterion, error_msg):
    """
        Executes 'result = function()' until 'criterion(result)' evaluates to a true value.
        Raises 'Exception(error_msg)' if criterion is not fulfilled after 'retries' attempts
    
    """
    delay = 0.1
    retry = 0
    result = None
    while retry < retries:
        try:
            result = function()
            try:
                if criterion(result):
                    if retry > 0:
                        _log.info("Criterion %s(%s) satisfied after %d retries" %
                                    (str(criterion), str(function), retry,))
                    return result
            except Exception as e:
                _log.error("Erroneous criteria '%r" % (e, ))
                raise e
        except Exception as e:
            _log.exception("Encountered exception when retrying '%s'" % (e,))
            #_log.info("Encountered exception when retrying '%s'" % (e,))
        delay = min(2, delay * 1.5); retry += 1
        time.sleep(delay)
        try:
            r = result if isinstance(result, (numbers.Number, type(None))) else len(result)
        except:
            r = None
        _log.info("Criterion still not satisfied after %d retries, result (length) %s" % (retry, r))
    _log.info("Criterion %s(%s) never satisfied, last full result %s" % (str(criterion), str(function), str(result)))
    raise Exception(error_msg)

def wait_for_tokens(request_handler, rt, actor_id, size=5, retries=10):
    """An alias for 'actual_tokens'"""
    return actual_tokens(request_handler, rt, actor_id, size, retries)

def actual_tokens(request_handler, rt, actor_id, size=5, retries=10):
    """
    Uses 'request_handler' to fetch the report from actor 'actor_id' on runtime 'rt'.
    """
    from functools import partial
    func = partial(request_handler.report, rt, actor_id)
    criterion = lambda tokens: len(tokens) >= size
    return retry(retries, func, criterion, "Not enough tokens, expected %d" % (size,))


def multi_report(request_handler, rt, actor_ids):
    """
    Helper uses 'request_handler' to fetch the report from actors in 'actor_ids' list on runtime(s) 'rt'.
    """
    result = []
    if isinstance(rt, (list, tuple, set)):
        args = zip(rt, actor_ids)
    else:
        args = zip([rt]*len(actor_ids), actor_ids)
    for runtime, actor_id in args:
        result.append(request_handler.report(runtime, actor_id))
    return result

def actual_tokens_multiple(request_handler, rt, actor_ids, size=5, retries=10):
    """
    Uses 'request_handler' to fetch the report from actors in 'actor_ids' list on runtime(s) 'rt'.
    """
    from functools import partial
    func = partial(multi_report, request_handler, rt, actor_ids)
    criterion = lambda tokens: sum([len(t) for t in tokens]) >= size
    return retry(retries, func, criterion, "Not enough tokens, expected %d" % size)

def destroy_app(deployer, retries=10):
    """
    Tries to destroy the app connected with deployer. 
    """
    return delete_app(deployer.request_handler, deployer.runtime, deployer.app_id, retries=retries)


def deploy_app(request_handler, deployer, runtimes, retries=10):
    """
    Deploys app associated w/ deployer and then tries to verify its
    presence in registry (for all runtimes).
    """
    deployer.deploy()
    
    def check_application():
        for rt in runtimes:
            try:
                if request_handler.get_application(rt, deployer.app_id) is None:
                    return False
            except:
                return False
        _log.info("Application found on all peers, continuing")
        return True

    return retry(retries, check_application, lambda r: r, "Application not found on all peers")
    

def delete_app(request_handler, runtime, app_id, check_actor_ids=None, retries=10):
    """
    Deletes an app and then tries to verify it is actually gone.
    """
    from functools import partial

    def verify_app_gone(request_handler, runtime, app_id):
        try:
            request_handler.get_application(runtime, app_id)
            return False
        except:
            return True

    def verify_actors_gone(request_handler, runtime, actor_ids):
        responses = []
        for actor_id in actor_ids:
            responses.append(request_handler.async_get_actor(runtime, actor_id))
        gone = True
        for r in responses:
            try:
                response = request_handler.async_response(r)
                if response is not None:
                    gone = False
            except:
                pass
        return gone

    try:
        request_handler.delete_application(runtime, app_id)
    except Exception as e:
        msg = str(e.message)
        if msg.startswith("500"):
            _log.error("Delete App got 500")
        elif msg.startswith("404"):
            _log.error("Delete App got 404")
        else:
            _log.error("Delete App got unknown error %s" % str(msg))

    retry(retries, partial(verify_app_gone, request_handler, runtime, app_id), lambda r: r, "Application not deleted")
    if check_actor_ids:
        retry(retries, partial(verify_actors_gone, request_handler, runtime, check_actor_ids), 
              lambda r: r, "Application actors not deleted")


def deploy_script(request_handler, name, script, runtime, retries=10):
    """
    Deploys script and then tries to verify its
    presence in registry on the runtime.
    """

    response = request_handler.deploy_application(runtime, name, script)
    app_id = response['application_id']

    def check_application():
        try:
            if request_handler.get_application(runtime, app_id) is None:
                return False
        except:
            return False
        _log.info("Application found, continuing")
        return True

    retry(retries, check_application, lambda r: r, "Application not found")
    return response

def flatten_zip(lz):
    return [] if not lz else [ lz[0][0], lz[0][1] ] + flatten_zip(lz[1:])
    

# Helper for 'std.CountTimer' actor
def expected_counter(n):
    return [i for i in range(1, n + 1)]

# Helper for 'std.Sum' 
def expected_sum(n):
    def cumsum(l):
        s = 0
        for n in l:
            s = s + n
            yield s
        
    return list(cumsum(range(1, n + 1)))

def expected_tokens(request_handler, rt, actor_id, t_type):
    
    tokens = request_handler.report(rt, actor_id)

    if t_type == 'seq':
        return expected_counter(tokens)

    if t_type == 'sum':
        return expected_sum(tokens)

    return None


def setup_distributed(control_uri, purpose, request_handler):
    from functools import partial
    
    remote_node_count = 3
    test_peers = None
    runtimes = []
    
    runtime = RT(control_uri)
    index = {"node_name": {"organization": "com.ericsson", "purpose": purpose}}
    index_string = format_index_string(index)
    
    get_index = partial(request_handler.get_index, runtime, index_string)
    
    def criteria(peers):
        return peers and peers.get("result", None) and len(peers["result"]) >= remote_node_count
    
    test_peers = retry(10, get_index, criteria, "Not all nodes found")
    test_peers = test_peers["result"]
    
    for peer_id in test_peers:
        peer = request_handler.get_node(runtime, peer_id)
        if not peer:
            _log.warning("Runtime '%r' peer '%r' does not exist" % (runtime, peer_id, ))
            continue
        rt = RT(peer["control_uri"])
        rt.id = peer_id
        rt.uris = peer["uri"]
        runtimes.append(rt)

    return runtimes
    
def setup_local(ip_addr, request_handler, nbr, proxy_storage):  
    def check_storage(rt, n, index):
        index_string = format_index_string(index)
        retries = 0
        while retries < 120:
            try:
                retries += 1
                peers = request_handler.get_index(rt, index_string, timeout=60)
            except Exception as e:
                try:
                    notfound = e.message.startswith("404")
                except:
                    notfound = False
                if notfound:
                    peers={'result':[]}
                else:
                    _log.info("Timed out when finding peers retrying")
                    retries += 39  # A timeout counts more we don't want to wait 60*100 seconds
                    continue
            if len(peers['result']) >= n:
                _log.info("Found %d peers (%r)", len(peers['result']), peers['result'])
                return
            _log.info("Only %d peers found (%r)", len(peers['result']), peers['result'])
            time.sleep(1)
        # No more retrying
        raise Exception("Storage check failed, could not find peers.")

    hosts = [
        ("calvinip://%s:%d" % (ip_addr, d), "http://%s:%d" % (ip_addr, d+1)) for d in range(5200, 5200 + 2 * nbr, 2)
    ]

    runtimes = []

    host = hosts[0]
    attr = {u'indexed_public': {u'node_name': {u'organization': u'com.ericsson', u'purpose': u'distributed-test'}}}
    attr_first = copy.deepcopy(attr)
    attr_first['indexed_public']['node_name']['group'] = u'first'
    attr_first['indexed_public']['node_name']['name'] = u'runtime1'
    attr_rest = copy.deepcopy(attr)
    attr_rest['indexed_public']['node_name']['group'] = u'rest'

    _log.info("starting runtime %s %s" % host)
    
    if proxy_storage:
        import calvin.runtime.north.storage
        calvin.runtime.north.storage._conf.set('global', 'storage_type', 'local')
    rt, _ = dispatch_node([host[0]], host[1], attributes=attr_first)
    check_storage(rt, len(runtimes)+1, attr['indexed_public'])
    runtimes += [rt]
    if proxy_storage:
        import calvin.runtime.north.storage
        calvin.runtime.north.storage._conf.set('global', 'storage_type', 'proxy')
        calvin.runtime.north.storage._conf.set('global', 'storage_proxy', host[0])
    _log.info("started runtime %s %s" % host)

    count = 2
    for host in hosts[1:]:
        if nbr > 3:
            # Improve likelihood of success if runtimes started with a time interval
            time.sleep(10.0)
        _log.info("starting runtime %s %s" % host)
        attr_rt = copy.deepcopy(attr_rest)
        attr_rt['indexed_public']['node_name']['name'] = u'runtime' + str(count)
        count += 1
        rt, _ = dispatch_node([host[0]], host[1], attributes=attr_rt)
        check_storage(rt, len(runtimes)+1, attr['indexed_public'])
        _log.info("started runtime %s %s" % host)
        runtimes += [rt]

    for host in hosts:
        check_storage(RT(host[1]), nbr, attr['indexed_public'])
        
    for host in hosts:
        request_handler.peer_setup(RT(host[1]), [h[0] for h in hosts if h != host])
    
    return runtimes

def setup_bluetooth(bt_master_controluri, request_handler):
    runtime = RT(bt_master_controluri)
    runtimes = []
    bt_master_id = request_handler.get_node_id(bt_master_controluri)
    data = request_handler.get_node(runtime, bt_master_id)
    if data:
        runtime.id = bt_master_id
        runtime.uris = data["uri"]
        test_peers = request_handler.get_nodes(runtime)
        test_peer2_id = test_peers[0]
        test_peer2 = request_handler.get_node(runtime, test_peer2_id)
        if test_peer2:
            rt2 = RT(test_peer2["control_uri"])
            rt2.id = test_peer2_id
            rt2.uris = test_peer2["uri"]
            runtimes.append(rt2)
        test_peer3_id = test_peers[1]
        if test_peer3_id:
            test_peer3 = request_handler.get_node(runtime, test_peer3_id)
            if test_peer3:
                rt3 = request_handler.RT(test_peer3["control_uri"])
                rt3.id = test_peer3_id
                rt3.uris = test_peer3["uri"]
                runtimes.append(rt3)
    return [runtime] + runtimes

def setup_test_type(request_handler, nbr=3, proxy_storage=False):
    control_uri = None
    ip_addr = None
    purpose = None
    bt_master_controluri = None
    test_type = None

    try:
        control_uri = os.environ["CALVIN_TEST_CTRL_URI"]
        purpose = os.environ["CALVIN_TEST_UUID"]
        test_type = "distributed"
    except KeyError:
        pass

    if not test_type:
        # Bluetooth tests assumes one master runtime with two connected peers
        # CALVIN_TEST_BT_MASTERCONTROLURI is the control uri of the master runtime
        try:
            bt_master_controluri = os.environ["CALVIN_TEST_BT_MASTERCONTROLURI"]
            _log.debug("Running Bluetooth tests")
            test_type = "bluetooth"
        except KeyError:
            pass

    if not test_type:
        try:
            ip_addr = os.environ["CALVIN_TEST_LOCALHOST"]
        except KeyError:
            import socket
            # If this fails add hostname to the /etc/hosts file for 127.0.0.1
            ip_addr = socket.gethostbyname(socket.gethostname())
        test_type = "local"

    if test_type == "distributed":
        runtimes = setup_distributed(control_uri, purpose, request_handler)
    elif test_type == "bluetooth":
        runtimes = setup_bluetooth(bt_master_controluri, request_handler)
    else:
        proxy_storage = bool(int(os.environ.get("CALVIN_TESTING_PROXY_STORAGE", proxy_storage)))
        runtimes = setup_local(ip_addr, request_handler, nbr, proxy_storage)

    return test_type, runtimes
    

def teardown_test_type(test_type, runtimes, request_handler):
    from functools import partial
    def wait_for_it(peer):
        while True:
            try:
                request_handler.get_node_id(peer)
            except Exception:
                return True
        return False
        
    if test_type == "local":
        for peer in runtimes:
            request_handler.quit(peer)
            retry(10, partial(request_handler.get_node_id, peer), lambda _: True, "Failed to stop peer %r" % (peer,))
            # wait_for_it(peer)
        for p in multiprocessing.active_children():
            p.terminate()
            time.sleep(1)

